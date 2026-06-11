import streamlit as st
import tempfile
import os
import time
import base64
from fpdf import FPDF
from engine import (
    build_rag_chain,
    get_sources,
    get_suggested_questions,
    web_search,
    get_api_key,
    load_from_url
)

try:
    from streamlit_mic_recorder import speech_to_text
    MIC_AVAILABLE = True
except ImportError:
    MIC_AVAILABLE = False

st.set_page_config(
    page_title="NexusRead AI",
    page_icon="⚡",
    layout="wide"
)

st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #0a0a0a 0%,
    #0d1f0d 50%, #0a0a0a 100%);
    color: #e0e0e0;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d2b0d 0%,
    #0a1a0a 100%);
    border-right: 1px solid #1a4a1a;
}
.main-title {
    text-align: center;
    font-size: 3rem;
    font-weight: 800;
    background: linear-gradient(90deg, #00c853,
    #69f0ae, #00e676);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.2rem;
}
.sub-title {
    text-align: center;
    color: #69f0ae;
    font-size: 1rem;
    margin-bottom: 2rem;
    opacity: 0.8;
}
.welcome-card {
    background: linear-gradient(135deg, #0d2b0d,
    #1a4a1a);
    border: 1px solid #00c853;
    border-radius: 15px;
    padding: 2rem;
    margin: 1rem 0;
    text-align: center;
}
.user-bubble {
    background: linear-gradient(135deg, #1b5e20,
    #2e7d32);
    border-radius: 18px 18px 4px 18px;
    padding: 12px 18px;
    margin: 8px 0;
    border: 1px solid #388e3c;
    color: #ffffff;
}
.ai-bubble {
    background: linear-gradient(135deg, #0d2b0d,
    #1a3a1a);
    border-radius: 18px 18px 18px 4px;
    padding: 12px 18px;
    margin: 8px 0;
    border: 1px solid #00c853;
    color: #e8f5e9;
}
.web-bubble {
    background: linear-gradient(135deg, #0a1a2e,
    #0d2040);
    border-radius: 18px 18px 18px 4px;
    padding: 12px 18px;
    margin: 8px 0;
    border: 1px solid #1565c0;
    color: #e3f2fd;
}
.source-badge {
    background: #1b5e20;
    color: #69f0ae;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.75rem;
    margin: 2px;
    display: inline-block;
    border: 1px solid #00c853;
}
.web-badge {
    background: #0d47a1;
    color: #90caf9;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.75rem;
    margin: 2px;
    display: inline-block;
    border: 1px solid #1565c0;
}
.web-search-active {
    background: linear-gradient(135deg, #0a1a2e,
    #0d2040);
    border: 1px solid #1565c0;
    border-radius: 8px;
    padding: 6px 12px;
    color: #90caf9;
    font-size: 0.85rem;
    margin: 4px 0;
    display: inline-block;
}
.stats-card {
    background: linear-gradient(135deg, #0d2b0d,
    #1a3a1a);
    border: 1px solid #00c853;
    border-radius: 10px;
    padding: 1rem;
    text-align: center;
    color: #69f0ae;
}
.api-card {
    background: linear-gradient(135deg, #1a0a0a,
    #2a1a0a);
    border: 1px solid #ff6d00;
    border-radius: 10px;
    padding: 0.8rem;
    margin: 0.5rem 0;
    font-size: 0.85rem;
    color: #ffab40;
}
.tool-btn > div > button {
    background: #111111 !important;
    color: #888888 !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 50% !important;
    width: 36px !important;
    height: 36px !important;
    padding: 0 !important;
    font-size: 1rem !important;
    min-width: 36px !important;
    transition: all 0.2s ease !important;
}
.tool-btn > div > button:hover {
    background: #0d2b0d !important;
    color: #00c853 !important;
    border-color: #00c853 !important;
    box-shadow: 0 0 8px rgba(0,200,83,0.3) !important;
}
[data-testid="stFileUploader"] {
    border: 2px dashed #00c853 !important;
    border-radius: 10px !important;
}
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


def generate_pdf(chat_history):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "NexusRead AI - Chat Export",
             ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.ln(4)
    for msg in chat_history:
        role = "You" if msg["role"] == "user" \
            else "NexusRead"
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 8, f"{role}:", ln=True)
        pdf.set_font("Helvetica", "", 9)
        clean = msg["content"] \
            .replace("**", "").replace("*", "") \
            .encode("latin-1", "replace") \
            .decode("latin-1")
        pdf.multi_cell(0, 6, clean)
        pdf.ln(2)
    return bytes(pdf.output())


def get_chat_text(chat_history):
    lines = []
    for msg in chat_history:
        role = "You" if msg["role"] == "user" \
            else "NexusRead"
        lines.append(f"{role}: {msg['content']}\n")
    return "\n".join(lines)


# ── KEY FUNCTION: reliable "no answer" detection ──────────────────────────
def rag_had_no_answer(response: str) -> bool:
    """
    Returns True if the RAG chain couldn't find the answer.
    Uses the sentinel token we embedded in the prompt,
    plus a broader set of fallback phrases.
    """
    r = response.strip().lower()

    # Primary: sentinel token we tell the model to use
    if "nexus_not_found" in r:
        return True

    # Secondary: common LLM "no answer" phrases
    no_answer_phrases = [
        "couldn't find this",
        "i couldn't find",
        "cannot find",
        "not found in",
        "no information",
        "not mentioned",
        "not available in",
        "does not contain",
        "not in the document",
        "not in the context",
        "outside the scope",
        "not covered in",
        "no relevant",
    ]
    return any(p in r for p in no_answer_phrases)


defaults = {
    "rag_chain": None,
    "vector_ind": None,
    "chat_history": [],
    "pdf_names": [],
    "total_chunks": 0,
    "total_pages": 0,
    "processing_time": 0,
    "suggested_questions": [],
    "show_sources": True,
    "web_search_enabled": False,
    "pending_question": None,
    "user_api_key": "",
    "share_menu_open": False,
    "input_mode": "pdf"
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

st.markdown(
    '<div class="main-title">⚡ NexusRead AI</div>',
    unsafe_allow_html=True
)
st.markdown(
    '<div class="sub-title">'
    'Intelligent document intelligence — '
    'PDFs, URLs, voice & web search in one place'
    '</div>',
    unsafe_allow_html=True
)

# ── SIDEBAR ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    st.markdown("---")

    st.toggle("📄 Show Source Pages", key="show_sources")
    st.toggle("🌐 Web Search Fallback", key="web_search_enabled")

    # Visual confirmation that web search is active
    if st.session_state.web_search_enabled:
        st.markdown(
            '<div class="web-search-active">'
            '🌐 Web search is ON — will search the web '
            'if your document has no answer'
            '</div>',
            unsafe_allow_html=True
        )

    st.markdown("---")

    st.markdown("### 🔑 API Key")
    env_key = os.getenv("GOOGLE_API_KEY", "")
    if env_key and env_key.startswith("AIza"):
        st.success("✅ System API key active")
    else:
        st.markdown(
            '<div class="api-card">⚠️ No system key.'
            ' Enter your own below.</div>',
            unsafe_allow_html=True
        )

    user_key_input = st.text_input(
        "Your Gemini API Key (optional)",
        type="password",
        placeholder="AIza...",
        help="Get free key at aistudio.google.com"
    )
    if user_key_input:
        st.session_state.user_api_key = user_key_input
        st.success("✅ Your key will be used")

    st.link_button(
        "🔗 Get Free API Key",
        "https://aistudio.google.com/apikey"
    )

    st.markdown("---")

    st.markdown("### 📥 Input Mode")
    mode = st.radio(
        "Choose source type:",
        ["📄 PDF Upload", "🌐 Web URL"],
        key="input_mode_radio"
    )
    st.session_state.input_mode = mode

    st.markdown("---")

    if mode == "📄 PDF Upload":
        st.markdown("### 📂 Upload PDF")
        uploaded_files = st.file_uploader(
            "Choose PDF files",
            type=["pdf"],
            accept_multiple_files=True
        )

        if uploaded_files:
            new_names = [f.name for f in uploaded_files]
            if new_names != st.session_state.pdf_names:
                active_key = get_api_key(
                    st.session_state.user_api_key
                )
                if not active_key:
                    st.error("❌ No API key! Enter above.")
                else:
                    progress = st.progress(0)
                    status = st.empty()
                    tmp_paths = []

                    status.markdown("📖 Reading PDFs...")
                    progress.progress(20)

                    for f in uploaded_files:
                        with tempfile.NamedTemporaryFile(
                            delete=False,
                            suffix=".pdf"
                        ) as tmp:
                            tmp.write(f.read())
                            tmp_paths.append(tmp.name)

                    try:
                        start = time.time()
                        status.markdown(
                            "🧠 Creating embeddings..."
                        )
                        progress.progress(60)

                        rag_chain, v_ind, chunks, meta \
                            = build_rag_chain(
                                tmp_paths, active_key
                            )

                        progress.progress(80)
                        end = time.time()

                        st.session_state.rag_chain = \
                            rag_chain
                        st.session_state.vector_ind = \
                            v_ind
                        st.session_state.pdf_names = \
                            new_names
                        st.session_state.total_chunks \
                            = chunks
                        st.session_state.total_pages \
                            = sum(
                                m["pages"] for m in meta
                            )
                        st.session_state.processing_time\
                            = round(end - start, 1)
                        st.session_state.chat_history \
                            = []

                        status.markdown(
                            "💡 Generating suggestions..."
                        )
                        progress.progress(90)

                        from langchain_community \
                            .document_loaders \
                            import PyPDFLoader
                        fl = PyPDFLoader(tmp_paths[0])
                        fd = fl.load()
                        pt = " ".join(
                            [d.page_content for d in fd]
                        )
                        st.session_state \
                            .suggested_questions = \
                            get_suggested_questions(
                                pt, active_key
                            )

                        progress.progress(100)
                        status.markdown("✅ Ready!")
                        time.sleep(1)
                        status.empty()
                        progress.empty()

                    except Exception as e:
                        err = str(e)
                        if "429" in err or \
                                "QUOTA" in err.upper():
                            st.error(
                                "⚠️ Quota exceeded!\n"
                                "Enter your API key above."
                            )
                        else:
                            st.error(f"❌ {e}")
                    finally:
                        for p in tmp_paths:
                            os.unlink(p)

    else:
        st.markdown("### 🌐 Load from URL")
        web_url = st.text_input(
            "Paste any webpage URL:",
            placeholder="https://example.com/article"
        )
        if st.button("🔗 Load URL", key="load_url_btn"):
            active_key = get_api_key(
                st.session_state.user_api_key
            )
            if not active_key:
                st.error("❌ No API key! Enter above.")
            elif not web_url.strip().startswith("http"):
                st.error("❌ Enter a valid URL")
            else:
                with st.spinner("🌐 Loading webpage..."):
                    try:
                        start = time.time()
                        rag_chain, v_ind, chunks, \
                            page_title = \
                            load_from_url(
                                web_url, active_key
                            )
                        end = time.time()

                        st.session_state.rag_chain = \
                            rag_chain
                        st.session_state.vector_ind = \
                            v_ind
                        st.session_state.pdf_names = \
                            [page_title]
                        st.session_state.total_chunks \
                            = chunks
                        st.session_state.total_pages = 1
                        st.session_state.processing_time\
                            = round(end - start, 1)
                        st.session_state.chat_history \
                            = []
                        st.session_state \
                            .suggested_questions = \
                            get_suggested_questions(
                                web_url[:2000],
                                active_key
                            )
                        st.success(
                            f"✅ Loaded: {page_title}"
                        )
                    except Exception as e:
                        st.error(f"❌ {e}")

    if st.session_state.pdf_names:
        st.markdown("---")
        st.markdown("### 📊 Stats")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"""
            <div class="stats-card">
            <b>{st.session_state.total_pages}</b>
            <br><small>Pages</small>
            </div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class="stats-card">
            <b>{st.session_state.total_chunks}</b>
            <br><small>Chunks</small>
            </div>""", unsafe_allow_html=True)
        st.markdown(f"""
        <div class="stats-card" style="margin-top:8px">
        <b>{st.session_state.processing_time}s</b>
        Processing Time
        </div>""", unsafe_allow_html=True)

# ── MAIN AREA ─────────────────────────────────────────────────────────────
if not st.session_state.rag_chain:
    st.markdown("""
    <div class="welcome-card">
        <h2>👋 Welcome to NexusRead AI!</h2>
        <p style="color:#69f0ae;font-size:1.1rem;">
        Intelligent document assistant powered by
        Google Gemini AI</p><br>
        <p>📄 Upload a PDF <b>or</b>
        🌐 paste a webpage URL</p>
        <p>🎤 Ask by voice or typing</p>
        <p>📍 Get answers with page citations</p>
        <p>🌐 Web search fallback included</p>
        <p>🔑 Use your own API key</p>
        <p>📑 Download chat as PDF or text</p>
        <br>
        <p style="color:#00c853;font-size:0.9rem;">
        Powered by LangChain + Google Gemini AI
        </p>
    </div>
    """, unsafe_allow_html=True)

else:
    if st.session_state.suggested_questions \
            and not st.session_state.chat_history:
        st.markdown("### 💡 Suggested Questions")
        cols = st.columns(2)
        for i, q in enumerate(
            st.session_state.suggested_questions
        ):
            with cols[i % 2]:
                if st.button(q, key=f"sq_{i}"):
                    st.session_state.pending_question \
                        = q
                    st.rerun()
        st.markdown("---")

    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            icon = "🎤" if msg.get("voice") else "👤"
            st.markdown(f"""
            <div class="user-bubble">
            {icon} <b>You:</b> {msg["content"]}
            </div>""", unsafe_allow_html=True)
        else:
            bubble_class = "web-bubble" \
                if msg.get("web_search") else "ai-bubble"
            icon = "🌐" if msg.get("web_search") else "⚡"
            label = "Web" if msg.get("web_search") \
                else "NexusRead"
            st.markdown(f"""
            <div class="{bubble_class}">
            {icon} <b>{label}:</b>
            <br>{msg["content"]}
            </div>""", unsafe_allow_html=True)
            if msg.get("web_search"):
                st.markdown(
                    '<span class="web-badge">'
                    '🌐 Answer sourced from web search'
                    '</span>',
                    unsafe_allow_html=True
                )
            if "sources" in msg \
                    and st.session_state.show_sources \
                    and not msg.get("web_search"):
                for src in msg["sources"]:
                    st.markdown(
                        f'<span class="source-badge">'
                        f'{src}</span>',
                        unsafe_allow_html=True
                    )

    if st.session_state.pending_question:
        user_input = st.session_state.pending_question
        st.session_state.pending_question = None
        is_voice = False
    else:
        user_input = None
        is_voice = False

    if MIC_AVAILABLE:
        mic_col, input_col = st.columns([1, 20])
        with mic_col:
            voice_result = speech_to_text(
                language="en",
                start_prompt="🎤",
                stop_prompt="⏹️",
                just_once=True,
                key="mic_input"
            )
            if voice_result:
                user_input = voice_result
                is_voice = True
        with input_col:
            typed = st.chat_input(
                "Ask something about your document..."
            )
            if typed:
                user_input = typed
                is_voice = False
    else:
        typed = st.chat_input(
            "Ask something about your document..."
        )
        if typed:
            user_input = typed
            is_voice = False

    # ── TOOLBAR ───────────────────────────────────────────────────────────
    st.markdown(
        "<div style='height:4px'></div>",
        unsafe_allow_html=True
    )
    t1, t2, t3, t_space = st.columns([1, 1, 1, 17])

    with t1:
        st.markdown(
            '<div class="tool-btn">',
            unsafe_allow_html=True
        )
        if st.button("🗑️", help="Clear Chat",
                     key="clr_t"):
            st.session_state.chat_history = []
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with t2:
        st.markdown(
            '<div class="tool-btn">',
            unsafe_allow_html=True
        )
        if st.button("📤", help="Share / Export Chat",
                     key="shr_t"):
            st.session_state.share_menu_open = \
                not st.session_state.share_menu_open
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with t3:
        st.markdown(
            '<div class="tool-btn">',
            unsafe_allow_html=True
        )
        st.button("💾", help="Download Chat", key="dl_t")
        st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.share_menu_open \
            and st.session_state.chat_history:
        st.markdown("#### 📤 Export Options")
        s1, s2 = st.columns(2)
        with s1:
            st.download_button(
                "📋 Download as Text",
                data=get_chat_text(
                    st.session_state.chat_history
                ),
                file_name="nexusread_chat.txt",
                mime="text/plain",
                key="dl_txt"
            )
        with s2:
            try:
                pdf_bytes = generate_pdf(
                    st.session_state.chat_history
                )
                st.download_button(
                    "📑 Download as PDF",
                    data=pdf_bytes,
                    file_name="nexusread_chat.pdf",
                    mime="application/pdf",
                    key="dl_pdf"
                )
            except Exception:
                st.warning("PDF export unavailable")

    if user_input:
        active_key = get_api_key(
            st.session_state.user_api_key
        )
        st.session_state.chat_history.append({
            "role": "user",
            "content": user_input,
            "voice": is_voice
        })

        with st.spinner("⚡ NexusRead is thinking..."):
            try:
                response = st.session_state \
                    .rag_chain.invoke(user_input)
                is_web = False
                sources = []

                # ── FIXED trigger: sentinel + broad phrases ──
                if st.session_state.web_search_enabled \
                        and rag_had_no_answer(response):
                    with st.spinner(
                        "🌐 Searching the web..."
                    ):
                        web_result = web_search(
                            user_input, active_key
                        )
                        # Only use web result if it
                        # actually returned something
                        if web_result and \
                                "couldn't retrieve" \
                                not in web_result.lower():
                            response = web_result
                            is_web = True

                if not is_web and \
                        st.session_state.show_sources:
                    sources = get_sources(
                        st.session_state.vector_ind,
                        user_input
                    )

                ph = st.empty()
                displayed = ""
                bubble = "web-bubble" if is_web \
                    else "ai-bubble"
                icon = "🌐" if is_web else "⚡"
                label = "Web" if is_web else "NexusRead"
                for char in response:
                    displayed += char
                    ph.markdown(
                        f'<div class="{bubble}">'
                        f'{icon} <b>{label}:</b><br>'
                        f'{displayed}▌</div>',
                        unsafe_allow_html=True
                    )
                    time.sleep(0.008)
                ph.empty()

                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": response,
                    "sources": sources,
                    "web_search": is_web
                })

            except Exception as e:
                err = str(e)
                if "429" in err or \
                        "QUOTA" in err.upper():
                    msg = (
                        "⚠️ **API quota exceeded!**\n\n"
                        "1. Enter your API key in sidebar\n"
                        "2. Get free key: "
                        "aistudio.google.com/apikey\n"
                        "3. Or wait 24 hours"
                    )
                else:
                    msg = f"❌ Error: {err}"

                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": msg,
                    "sources": [],
                    "web_search": False
                })
        st.rerun()
        