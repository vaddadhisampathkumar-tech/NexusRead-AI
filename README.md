<div align="center">

# ⚡ NexusRead AI

### Intelligent Document Intelligence — Powered by Google Gemini & RAG

[

![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)

](https://nexusread-ai-lpof5vdxljavaouncsxofe.streamlit.app/)


![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat&logo=python)




![LangChain](https://img.shields.io/badge/LangChain-Latest-green?style=flat)




![Google Gemini](https://img.shields.io/badge/Google%20Gemini-2.5%20Flash-orange?style=flat&logo=google)




![License](https://img.shields.io/badge/License-MIT-purple?style=flat)



**Ask questions. Get answers. From any document or webpage — instantly.**

[🚀 Live Demo](https://nexusread-ai-lpof5vdxljavaouncsxofe.streamlit.app/) • [⭐ Star this repo](https://github.com/vaddadhisampathkumar-tech/NexusRead-AI) • [🔗 Connect on LinkedIn](https://www.linkedin.com/in/vaddadhi-sampath-kumar-2b103b325)

</div>

---

## 🧠 What is NexusRead AI?

NexusRead AI is a production-ready, fully deployed intelligent document assistant built on **Retrieval Augmented Generation (RAG)** architecture.

It started as a simple RAG experiment in **Google Colab** — no local environment, no team, no guidance. Just curiosity, Python, and a drive to build something real. Today it is a fully deployed AI product that anyone in the world can open and use without installing a single thing.

Upload a PDF. Paste a webpage URL. Ask anything. Get answers with exact page citations — powered by Google Gemini 2.5 Flash.

---

## ✨ Features

| Feature | Description |
|---|---|
| 📄 **PDF Chat** | Upload multiple PDFs and ask anything across all of them simultaneously |
| 🌐 **Web URL Chat** | Paste any webpage URL and instantly query its entire content |
| 🎤 **Voice Input** | Ask questions completely hands-free using your microphone |
| 🔍 **Web Search Fallback** | When your document has no answer, the internet steps in automatically |
| 📍 **Page Citations** | Every answer shows the exact page number it came from |
| 💾 **Chat Export** | Download your entire conversation as a PDF or plain text file |
| 💡 **Smart Suggestions** | AI auto-generates 4 relevant questions the moment your document loads |
| 🔑 **Bring Your Own Key** | Use your own free Gemini API key or the built-in system key |

---

## 🛠️ Tech Stack
Language         → Python
LLM              → Google Gemini 2.5 Flash
Embeddings       → Google Gemini Embedding-001
Architecture     → RAG (Retrieval Augmented Generation)
Framework        → LangChain & LangChain-Community
Vector Store     → InMemory Vector Store
Web Scraping     → BeautifulSoup4
Web Search       → DuckDuckGo API (Two-tier: JSON + HTML fallback)
UI & Frontend    → Streamlit
PDF Export       → FPDF2
Voice Input      → Streamlit Mic Recorder
Deployment       → Streamlit Community Cloud

---

## 🚀 Try It Live

No installation. No setup. No account needed.
Just open and start asking.

👉 https://nexusread-ai-lpof5vdxljavaouncsxofe.streamlit.app/

---

## 🖥️ Run It Locally

### What You Need
- Python 3.10 or above
- A free Google Gemini API key — get one at [aistudio.google.com](https://aistudio.google.com/apikey)

### Steps
'''
# Step 1 — Clone the repository
git clone https://github.com/vaddadhisampathkumar-tech/NexusRead-AI.git
cd NexusRead-AI

# Step 2 — Install all dependencies
pip install -r requirements.txt

# Step 3 — Add your API key
echo "GOOGLE_API_KEY=your_key_here" > .env

# Step 4 — Launch the app
streamlit run main.py
App opens automatically at http://localhost:8501 '''

##📁 Project Structure
NexusRead-AI/
├── main.py              → Streamlit UI and all frontend logic
├── engine.py            → RAG engine, embeddings, chains, web search
├── requirements.txt     → All project dependencies
├── .gitignore           → Keeps your API key safe and off GitHub
└── README.md            → You are here

🧩 How It Works
User asks a question
        ↓
Document or URL loaded → Text split into chunks → Embeddings created
        ↓
Question embedded → Vector similarity search → Most relevant chunks retrieved
        ↓
Google Gemini 2.5 Flash → Answer generated with page citations
        ↓
If no answer found + Web Search ON → DuckDuckGo → Gemini synthesises result
        ↓
Streamed response displayed to user in real time

🔑 Getting Your Free Gemini API Key
Visit aistudio.google.com/apikey
Sign in with your Google account
Click Create API Key
Copy it and paste into the NexusRead AI sidebar
Completely free. No credit card. No billing setup.

🤝 Contributing
Found a bug? Have an idea to make it better? Contributions are genuinely welcome.
# Fork the repo
# Create your branch
git checkout -b feature/your-idea

# Commit your changes
git commit -m "Add your idea here"

# Push and open a Pull Request
git push origin feature/your-idea

Every contribution — big or small — is appreciated.

👨‍💻 About the Developer
Hi, I'm Sampath Kumar — a fresh graduate passionate about Python and AI/ML development.
I started NexusRead AI as a simple RAG experiment in Google Colab with no local setup and no prior experience in LangChain or vector databases. Over time it evolved into a fully deployed, production-ready AI application with a professional UI, voice input, multi-document support, web search fallback, and chat export.
Building this taught me more than any course ever could.
I am actively looking for opportunities in Python Development and AI/ML Engineering where I can contribute, keep learning, and build things that actually matter.
📬 vaddadhisampathkumar@gmail.com
🔗 https://www.linkedin.com/in/vaddadhi-sampath-kumar-2b103b

📄 License
This project is open source and available under the MIT License.
Use it. Learn from it. Build on top of it.

Built from scratch with ❤️ by Sampath Kumar
"Don't wait until you're ready. You'll never be ready. Start, build, ship."
If this project helped you or impressed you — an honest ⭐ means everything.
�
```
