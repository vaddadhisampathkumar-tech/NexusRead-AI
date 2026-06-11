import os
import time
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document

load_dotenv()


def get_api_key(user_key=None):
    if user_key and user_key.strip().startswith("AIza"):
        return user_key.strip()
    return os.getenv("GOOGLE_API_KEY")


def build_rag_chain(pdf_paths: list, api_key: str):
    all_documents = []
    pdf_metadata = []

    for pdf_path in pdf_paths:
        loader = PyPDFLoader(pdf_path)
        docs = loader.load()
        all_documents.extend(docs)
        pdf_metadata.append({"pages": len(docs)})

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,
        chunk_overlap=200,
        separators=["\n\n", "\n", " "]
    )
    splitting = splitter.split_documents(all_documents)

    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        google_api_key=api_key,
        task_type="retrieval_document"
    )

    vector_st = InMemoryVectorStore.from_documents(
        documents=splitting,
        embedding=embeddings
    )
    vector_ind = vector_st.as_retriever(
        search_kwargs={"k": 8}
    )

    model = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=api_key
    )

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    template = """You are a helpful AI assistant named NexusRead.
Answer the question based only on the following context:

{context}

Question: {question}

Format your response with:
- Clear **bold headings** for each section
- A blank line between each section
- Bullet points for lists
- If answering from multiple documents, clearly separate
  each document answer with headings like
  **From History Document:** and **From Resume:**

If the answer cannot be found in the context, respond with
exactly this phrase: "NEXUS_NOT_FOUND"

Answer:"""

    prompt = ChatPromptTemplate.from_template(template)

    rag_chain = (
        {"context": vector_ind | format_docs,
         "question": RunnablePassthrough()}
        | prompt
        | model
        | StrOutputParser()
    )

    return rag_chain, vector_ind, len(splitting), pdf_metadata


def get_sources(vector_ind, query):
    docs = vector_ind.invoke(query)
    sources = []
    for doc in docs:
        page = doc.metadata.get("page", 0) + 1
        sources.append(f"📄 Page {page}")
    return list(set(sources))


def get_suggested_questions(pdf_text: str, api_key: str):
    model = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=api_key
    )
    prompt = f"""Based on this content, suggest exactly 4
short useful questions a user might ask. Return only the
questions, one per line, no numbering, no extra text.

Content:
{pdf_text[:2000]}"""

    response = model.invoke(prompt)
    questions = response.content.strip().split("\n")
    return [q.strip() for q in questions if q.strip()][:4]


def _ddg_json_search(query: str) -> list[str]:
    """
    DuckDuckGo Instant Answer JSON API — no scraping,
    no bot detection, no API key needed.
    Returns a list of text snippets.
    """
    try:
        params = {
            "q": query,
            "format": "json",
            "no_redirect": "1",
            "no_html": "1",
            "skip_disambig": "1",
        }
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            )
        }
        resp = requests.get(
            "https://api.duckduckgo.com/",
            params=params,
            headers=headers,
            timeout=8
        )
        data = resp.json()

        snippets = []

        # AbstractText: best single-paragraph answer
        if data.get("AbstractText"):
            snippets.append(data["AbstractText"])

        # RelatedTopics: list of result snippets
        for topic in data.get("RelatedTopics", []):
            if isinstance(topic, dict):
                text = topic.get("Text", "")
                if text and len(text) > 40:
                    snippets.append(text)
            # Some topics have nested Topics
            elif isinstance(topic, dict) and "Topics" in topic:
                for sub in topic.get("Topics", []):
                    text = sub.get("Text", "")
                    if text and len(text) > 40:
                        snippets.append(text)
            if len(snippets) >= 5:
                break

        # Answer field (e.g. calculations, definitions)
        if data.get("Answer"):
            snippets.insert(0, str(data["Answer"]))

        return snippets[:5]

    except Exception:
        return []


def _ddg_html_search(query: str) -> list[str]:
    """
    Fallback: DuckDuckGo HTML scrape with rotated UA.
    Only used if JSON API returns nothing.
    """
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml",
        }
        url = (
            "https://html.duckduckgo.com/html/"
            f"?q={requests.utils.quote(query)}&kl=us-en"
        )
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for tag in soup.select(".result__snippet"):
            text = tag.get_text(strip=True)
            if len(text) > 40:
                results.append(text)
            if len(results) >= 5:
                break
        return results
    except Exception:
        return []


def web_search(query: str, api_key: str) -> str:
    """
    Two-tier web search:
    1. DuckDuckGo JSON API (fast, no bot blocks)
    2. DuckDuckGo HTML scrape as fallback
    Then synthesises answer with Gemini.
    """
    # Tier 1: JSON API
    snippets = _ddg_json_search(query)

    # Tier 2: HTML fallback if JSON returned nothing
    if not snippets:
        snippets = _ddg_html_search(query)

    if not snippets:
        return (
            "⚠️ Web search couldn't retrieve results for "
            f'"{query}". Try rephrasing or check your '
            "internet connection."
        )

    context = "\n\n".join(snippets)

    model = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=api_key
    )
    web_prompt = f"""Based on these web search results,
answer the question clearly and concisely. Cite specific
facts where possible.

Search Results:
{context}

Question: {query}

Answer:"""
    web_response = model.invoke(web_prompt)
    return web_response.content


def load_from_url(url: str, api_key: str):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36"
        )
    }
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    title_tag = soup.find("title")
    page_title = (
        title_tag.get_text(strip=True) if title_tag else url
    )

    for tag in soup(["script", "style", "nav",
                     "footer", "header", "aside"]):
        tag.decompose()

    raw_text = soup.get_text(separator="\n")
    lines = [
        l.strip() for l in raw_text.splitlines()
        if len(l.strip()) > 30
    ]
    clean_text = "\n".join(lines)

    if not clean_text:
        raise ValueError(
            "No readable content found at this URL."
        )

    documents = [Document(
        page_content=clean_text,
        metadata={"source": url, "title": page_title}
    )]

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,
        chunk_overlap=200,
        separators=["\n\n", "\n", " "]
    )
    splitting = splitter.split_documents(documents)

    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        google_api_key=api_key,
        task_type="retrieval_document"
    )
    vector_st = InMemoryVectorStore.from_documents(
        documents=splitting,
        embedding=embeddings
    )
    vector_ind = vector_st.as_retriever(
        search_kwargs={"k": 8}
    )

    model = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=api_key
    )

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    template = """You are a helpful AI assistant named NexusRead.
Answer the question based only on the following context from webpage:

{context}

Question: {question}

Format your response with:
- Clear **bold headings** for each section
- Bullet points for lists

If the answer cannot be found, respond with exactly:
"NEXUS_NOT_FOUND"

Answer:"""

    prompt = ChatPromptTemplate.from_template(template)

    rag_chain = (
        {"context": vector_ind | format_docs,
         "question": RunnablePassthrough()}
        | prompt
        | model
        | StrOutputParser()
    )

    return rag_chain, vector_ind, len(splitting), page_title