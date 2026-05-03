# 🤖 BIM AI Agent

<div align="center">

**Pipeline de IA com RAG, LLM e Agente Autônomo para automação de dados BIM/Revit**

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-LLM_Framework-1C3C3C?style=for-the-badge)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--3.5-412991?style=for-the-badge&logo=openai&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-orange?style=for-the-badge)
![n8n](https://img.shields.io/badge/n8n-Automation-EA4B71?style=for-the-badge)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)

</div>

---

## 🧠 Visão Geral

Este projeto é um **agente de Inteligência Artificial** especializado em dados **BIM (Building Information Modeling)** exportados do **Revit**. Combina três tecnologias centrais de IA moderna:

| Tecnologia | O que faz neste projeto |
|---|---|
| 🔍 **RAG** (Retrieval-Augmented Generation) | Indexa os dados do Revit em um vector store e recupera informações relevantes antes de gerar respostas |
| 🧠 **LLM** (Large Language Model) | GPT-3.5-turbo processa linguagem natural, interpreta dados de engenharia e gera respostas contextuais |
| 🤖 **AI Agent** | Agente autônomo com memória de sessão que decide quais ferramentas usar para responder cada pergunta |

O fluxo de automação foi **originalmente desenvolvido em n8n** e depois expandido com uma camada de IA em Python/LangChain, criando um sistema híbrido low-code + código que roda via API REST.

---

## 🏗️ Arquitetura Completa

```
╔══════════════════════════════════════════════════════════════════╗
║                      ENTRADA DE DADOS                           ║
║                                                                  ║
║   Revit Export ──► Google Sheets ──► n8n Workflow               ║
║   (Keynotes, Áreas,    (Planilha     (Agrupamento JS +           ║
║    Comprimentos,        Revit JV)     Cruzamento Cadastro)       ║
║    Contagens)                                                    ║
╚══════════════════════════════════════════════════════════════════╝
                              │
                              ▼
╔══════════════════════════════════════════════════════════════════╗
║                      CAMADA RAG                                  ║
║                                                                  ║
║   Dados Revit                                                    ║
║   Processados  ──► Text Splitter ──► OpenAI Embeddings           ║
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
║          GPT-3.5-turbo ──► Resposta Final                        ║
╚══════════════════════════════════════════════════════════════════╝
                              │
                              ▼
╔══════════════════════════════════════════════════════════════════╗
║                     FASTAPI REST API                             ║
║                                                                  ║
║   POST /chat          POST /process       POST /upload           ║
║   POST /query/keynote GET  /health                               ║
║                                                                  ║
║   ← Chamável via n8n HTTP node, Make, AWS Lambda, qualquer coisa ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## 🔍 RAG — Retrieval-Augmented Generation

O RAG é o núcleo de inteligência deste projeto. Em vez de apenas passar os dados brutos ao LLM (o que seria caro e impreciso), o sistema:

**1. Indexação (uma vez):**
```
Dados Revit → Chunking → Embeddings (OpenAI) → ChromaDB
```

**2. Consulta (em tempo real):**
```
Pergunta do usuário → Embedding da pergunta
                           │
                           ▼
                    Similarity Search
                    no ChromaDB (k=4)
                           │
                           ▼
              Chunks relevantes recuperados
                           │
                           ▼
               LLM recebe: [contexto + pergunta]
                           │
                           ▼
                    Resposta precisa
```

**Por que RAG aqui?**
Os dados do Revit podem ter centenas de Keynotes. Sem RAG, enviar tudo ao LLM seria inviável e impreciso. Com RAG, o modelo recebe apenas os 4 chunks mais relevantes para cada pergunta.

---

## 🤖 AI Agent — Agente Autônomo

O agente usa **LangChain AgentExecutor** com **OpenAI Tools** e decide autonomamente qual ação tomar:

```python
# O agente tem 3 ferramentas disponíveis:

@tool
def consultar_keynote(keynote: str) -> str:
    """Busca dados de um Keynote específico no vector store"""

@tool
def perguntar_sobre_revit(pergunta: str) -> str:
    """RAG — responde perguntas em linguagem natural sobre o projeto"""

@tool
def processar_planilhas(revit_url, catalog_url, output_url) -> str:
    """Lê, processa e atualiza as planilhas Google Sheets"""
```

**Exemplos de raciocínio do agente:**

> *"Qual a área total do ARQ.01.001?"*
> → Agente chama `consultar_keynote("ARQ.01.001")` → retorna dados do RAG → LLM formata resposta

> *"Quais elementos têm status DEMOLIÇÃO?"*
> → Agente chama `perguntar_sobre_revit("elementos com status demolição")` → RAG busca → LLM lista

> *"Processe as planilhas do projeto X"*
> → Agente chama `processar_planilhas(url1, url2, url3)` → atualiza Google Sheets → confirma

---

## 🧠 LLM — Large Language Model

- **Modelo:** `gpt-3.5-turbo` (OpenAI)
- **Framework:** LangChain
- **Temperatura:** 0 (respostas determinísticas para dados de engenharia)
- **Memória:** `ConversationBufferWindowMemory` com janela de **10 mensagens** — o agente lembra do contexto da conversa
- **System Prompt:** especializado em BIM/Revit, responde em português

---

## ⚡ Stack Tecnológica

```
┌─────────────────────────────────────────────────────┐
│  IA & LLM                                           │
│  ├── LangChain 0.2        (framework de agentes)    │
│  ├── OpenAI GPT-3.5-turbo (LLM)                     │
│  ├── OpenAI Embeddings    (vetorização)             │
│  └── ChromaDB             (vector store local)      │
├─────────────────────────────────────────────────────┤
│  API & Backend                                      │
│  ├── FastAPI              (REST API)                │
│  └── Uvicorn              (ASGI server)             │
├─────────────────────────────────────────────────────┤
│  Automação & Dados                                  │
│  ├── n8n                  (workflow original)       │
│  ├── gspread              (Google Sheets API)       │
│  └── Python 3.11                                    │
├─────────────────────────────────────────────────────┤
│  Infraestrutura                                     │
│  ├── Docker + Docker Compose                        │
│  └── Railway / Render (deploy gratuito)             │
└─────────────────────────────────────────────────────┘
```

---

## 🗂️ Estrutura do Projeto

```
bim-ai-agent/
│
├── app/
│   ├── main.py          # 🌐 API FastAPI — rotas e endpoints
│   ├── rag.py           # 🔍 RAG — indexação, embeddings, ChromaDB
│   └── agent.py         # 🤖 Agent — LangChain, Tools, Memória
│
├── n8n/
│   └── workflow.json    # ⚙️  Workflow n8n original (importável)
│
├── docs/
│   └── exemplo_revit_export.csv   # 📄 CSV exemplo para testes
│
├── .env.example         # 🔐 Variáveis de ambiente
├── docker-compose.yml   # 🐳 API + n8n local
├── Dockerfile
└── requirements.txt
```

---

## 🚀 Como Rodar

### Pré-requisitos
- Python 3.11+
- Docker (opcional)
- Chave da API OpenAI
- Service Account Google (para Google Sheets)

### 1. Clone

```bash
git clone https://github.com/SEU_USUARIO/bim-ai-agent.git
cd bim-ai-agent
```

### 2. Configure o `.env`

```bash
cp .env.example .env
# Adicione sua OPENAI_API_KEY e credenciais Google
```

### 3. Suba com Docker

```bash
docker-compose up --build
```

### 4. Ou rode direto

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

📖 Documentação interativa: **http://localhost:8000/docs**

---

## 💬 Exemplos de Uso

### Chat com o Agente

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Quais keynotes têm status NOVO e qual a área total?",
    "session_id": "projeto-vila-madalena"
  }'
```

```json
{
  "response": "Os keynotes com status NOVO são ARQ.01.001 (20.80 m²), ARQ.01.003 (15.75 m²) e INS.04.001 (12 unidades). Área total NOVO: 36.55 m².",
  "session_id": "projeto-vila-madalena"
}
```

### Upload de exportação Revit

```bash
curl -X POST http://localhost:8000/upload/revit-csv \
  -F "file=@docs/exemplo_revit_export.csv"
```

### Acionar via n8n (HTTP Request node)

```
URL: http://localhost:8000/chat
Method: POST
Body: { "message": "{{ $json.chatInput }}", "session_id": "{{ $json.sessionId }}" }
```

---

## 🔗 Integração n8n

O workflow original está em `n8n/workflow.json`. Para importar:

1. Abra seu n8n → **Workflows → Import from File**
2. Selecione `n8n/workflow.json`
3. Configure credenciais Google Sheets e OpenAI
4. Adicione um **HTTP Request node** apontando para a API deste projeto

---

## 📄 Licença

MIT — livre para usar, adaptar e evoluir.

---

<div align="center">

Construído com **LangChain** · **OpenAI** · **FastAPI** · **n8n** · **ChromaDB**

</div>
