# 🤖 LLMS AI Agent RAG Project

<div align="center">

**AI Pipeline with RAG, LLM and Autonomous Agent for BIM/Revit data automation**

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-LLM_Framework-1C3C3C?style=for-the-badge)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--3.5-412991?style=for-the-badge&logo=openai&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-orange?style=for-the-badge)
![n8n](https://img.shields.io/badge/n8n-Automation-EA4B71?style=for-the-badge)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)

</div>

---

## 🧠 Overview

This project is an **Artificial Intelligence agent** specialized in **BIM (Building Information Modeling)** data exported from **Revit**. It combines three core modern AI technologies:

| Technology | Role in this project |
|---|---|
| 🔍 **RAG** (Retrieval-Augmented Generation) | Indexes Revit data into a vector store and retrieves relevant information before generating responses |
| 🧠 **LLM** (Large Language Model) | GPT-3.5-turbo processes natural language, interprets engineering data and generates contextual responses |
| 🤖 **AI Agent** | Autonomous agent with session memory that decides which tools to use for each question |

The automation pipeline was **originally built in n8n** and later expanded with an AI layer in Python/LangChain, creating a hybrid low-code + code system exposed as a REST API.

---

## 🏗️ Full Architecture

```
╔══════════════════════════════════════════════════════════════════╗
║                        DATA INPUT                               ║
║                                                                  ║
║   Revit Export ──► Google Sheets ──► n8n Workflow               ║
║   (Keynotes, Areas,    (Revit JV      (JS Grouping +            ║
║    Lengths, Counts)     Sheet)         Catalog Lookup)          ║
╚══════════════════════════════════════════════════════════════════╝
                              │
                              ▼
╔══════════════════════════════════════════════════════════════════╗
║                        RAG LAYER                                 ║
║                                                                  ║
║   Processed                                                      ║
║   Revit Data   ──► Text Splitter ──► OpenAI Embeddings           ║
║                                           │                      ║
║                                           ▼                      ║
║                                      ChromaDB                    ║
║                                    (Vector Store)                ║
║                                           │                      ║
║                          Similarity Search (k=4)                 ║
╚══════════════════════════════════════════════════════════════════╝
                              │
                              ▼
╔══════════════════════════════════════════════════════════════════╗
║                    AI AGENT (LangChain)                          ║
║                                                                  ║
║   User Input ──► Agent Executor ──► Tool Selection              ║
║                       │                                          ║
║               ┌───────┼───────┐                                  ║
║               ▼       ▼       ▼                                  ║
║           Tool 1   Tool 2   Tool 3                               ║
║          Keynote   Ask RAG  Process                              ║
║          Query    (natural  Sheets                               ║
║                   language)                                      ║
║               │                                                  ║
║               ▼                                                  ║
║     ConversationBufferWindowMemory (k=10)                        ║
║               │                                                  ║
║               ▼                                                  ║
║          GPT-3.5-turbo ──► Final Response                        ║
╚══════════════════════════════════════════════════════════════════╝
                              │
                              ▼
╔══════════════════════════════════════════════════════════════════╗
║                     FASTAPI REST API                             ║
║                                                                  ║
║   POST /chat          POST /process       POST /upload           ║
║   POST /query/keynote GET  /health                               ║
║                                                                  ║
║   ← Callable from n8n HTTP node, Make, AWS Lambda, anything     ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## 🔍 RAG — Retrieval-Augmented Generation

RAG is the intelligence core of this project. Instead of passing raw data directly to the LLM (expensive and imprecise), the system works in two stages:

**1. Indexing (once):**
```
Revit Data → Chunking → Embeddings (OpenAI) → ChromaDB
```

**2. Query (real-time):**
```
User question → Question embedding
                      │
                      ▼
               Similarity Search
               in ChromaDB (k=4)
                      │
                      ▼
          Relevant chunks retrieved
                      │
                      ▼
       LLM receives: [context + question]
                      │
                      ▼
              Accurate response
```

**Why RAG here?**
Revit projects can have hundreds of Keynotes. Without RAG, sending everything to the LLM would be unfeasible and inaccurate. With RAG, the model only receives the 4 most relevant chunks for each question.

---

## 🤖 AI Agent — Autonomous Agent

The agent uses **LangChain AgentExecutor** with **OpenAI Tools** and autonomously decides which action to take:

```python
# The agent has 3 available tools:

@tool
def query_keynote(keynote: str) -> str:
    """Fetches data for a specific Keynote from the vector store"""

@tool
def ask_about_revit(question: str) -> str:
    """RAG — answers natural language questions about the project data"""

@tool
def process_sheets(revit_url, catalog_url, output_url) -> str:
    """Reads, processes and updates Google Sheets"""
```

**Agent reasoning examples:**

> *"What is the total area of ARQ.01.001?"*
> → Agent calls `query_keynote("ARQ.01.001")` → RAG returns data → LLM formats response

> *"Which elements have DEMOLITION status?"*
> → Agent calls `ask_about_revit("elements with demolition status")` → RAG searches → LLM lists

> *"Process the sheets for project X"*
> → Agent calls `process_sheets(url1, url2, url3)` → updates Google Sheets → confirms

---

## 🧠 LLM — Large Language Model

- **Model:** `gpt-3.5-turbo` (OpenAI)
- **Framework:** LangChain
- **Temperature:** 0 (deterministic responses for engineering data)
- **Memory:** `ConversationBufferWindowMemory` with a window of **10 messages** — the agent remembers conversation context
- **System Prompt:** specialized in BIM/Revit

---

## ⚡ Tech Stack

```
┌─────────────────────────────────────────────────────┐
│  AI & LLM                                           │
│  ├── LangChain 0.2        (agent framework)         │
│  ├── OpenAI GPT-3.5-turbo (LLM)                     │
│  ├── OpenAI Embeddings    (vectorization)           │
│  └── ChromaDB             (local vector store)      │
├─────────────────────────────────────────────────────┤
│  API & Backend                                      │
│  ├── FastAPI              (REST API)                │
│  └── Uvicorn              (ASGI server)             │
├─────────────────────────────────────────────────────┤
│  Automation & Data                                  │
│  ├── n8n                  (original workflow)       │
│  ├── gspread              (Google Sheets API)       │
│  └── Python 3.11                                    │
├─────────────────────────────────────────────────────┤
│  Infrastructure                                     │
│  ├── Docker + Docker Compose                        │
│  └── Railway / Render (free deploy)                 │
└─────────────────────────────────────────────────────┘
```

---

## 🗂️ Project Structure

```
bim-ai-agent/
│
├── app/
│   ├── main.py          # 🌐 FastAPI — routes and endpoints
│   ├── rag.py           # 🔍 RAG — indexing, embeddings, ChromaDB
│   └── agent.py         # 🤖 Agent — LangChain, Tools, Memory
│
├── n8n/
│   └── workflow.json    # ⚙️  Original n8n workflow (importable)
│
├── docs/
│   └── exemplo_revit_export.csv   # 📄 Sample CSV for testing
│
├── .env.example         # 🔐 Environment variables
├── docker-compose.yml   # 🐳 API + local n8n
├── Dockerfile
└── requirements.txt
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Docker (optional)
- OpenAI API Key
- Google Service Account (for Google Sheets)

### 1. Clone

```bash
git clone https://github.com/YOUR_USERNAME/bim-ai-agent.git
cd bim-ai-agent
```

### 2. Set up `.env`

```bash
cp .env.example .env
# Add your OPENAI_API_KEY and Google credentials
```

### 3. Run with Docker

```bash
docker-compose up --build
```

### 4. Or run directly

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

📖 Interactive docs: **http://localhost:8000/docs**

---

## 💬 Usage Examples

### Chat with the Agent

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Which keynotes have NEW status and what is the total area?",
    "session_id": "project-123"
  }'
```

```json
{
  "response": "Keynotes with NEW status are ARQ.01.001 (20.80 m²), ARQ.01.003 (15.75 m²) and INS.04.001 (12 units). Total NEW area: 36.55 m².",
  "session_id": "project-123"
}
```

### Upload Revit export

```bash
curl -X POST http://localhost:8000/upload/revit-csv \
  -F "file=@docs/exemplo_revit_export.csv"
```

### Trigger via n8n (HTTP Request node)

```
URL: http://localhost:8000/chat
Method: POST
Body: { "message": "{{ $json.chatInput }}", "session_id": "{{ $json.sessionId }}" }
```

---

## 🔗 n8n Integration

The original workflow is at `n8n/workflow.json`. To import it:

1. Open your n8n → **Workflows → Import from File**
2. Select `n8n/workflow.json`
3. Configure your Google Sheets and OpenAI credentials
4. Add an **HTTP Request node** pointing to this project's API

---

## 📄 License

MIT — free to use, adapt and evolve.

---

<div align="center">

Built with **LangChain** · **OpenAI** · **FastAPI** · **n8n** · **ChromaDB**

</div>
