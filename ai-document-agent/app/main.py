"""
BIM AI Agent - FastAPI Application
Automação inteligente de dados Revit com IA
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn

from app.rag import RevitRAG
from app.agent import BIMAgent

app = FastAPI(
    title="BIM AI Agent",
    description="API para automação inteligente de dados Revit com IA",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

rag = RevitRAG()
agent = BIMAgent()


# --- Models ---

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"

class ProcessRequest(BaseModel):
    revit_sheet_url: str
    catalog_sheet_url: str
    output_sheet_url: str

class QueryRequest(BaseModel):
    keynote: str


# --- Endpoints ---

@app.get("/")
def root():
    return {
        "project": "BIM AI Agent",
        "description": "Automação de dados Revit com IA",
        "docs": "/docs",
    }


@app.post("/chat")
async def chat(req: ChatRequest):
    """
    Chat com IA sobre os dados do Revit.
    Compatível com n8n webhook trigger.
    """
    try:
        response = await agent.chat(req.message, session_id=req.session_id)
        return {"response": response, "session_id": req.session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process")
async def process_revit_data(req: ProcessRequest):
    """
    Processa dados do Revit:
    1. Lê planilha Revit (Keynotes, Areas, Comprimentos)
    2. Agrupa por Keynote
    3. Cruza com cadastro
    4. Atualiza planilha de saída
    """
    try:
        result = await agent.process_sheets(
            revit_url=req.revit_sheet_url,
            catalog_url=req.catalog_sheet_url,
            output_url=req.output_sheet_url,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query/keynote")
async def query_keynote(req: QueryRequest):
    """
    Consulta informações de um Keynote específico usando RAG.
    """
    try:
        result = rag.query_keynote(req.keynote)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload/revit-csv")
async def upload_revit_csv(file: UploadFile = File(...)):
    """
    Faz upload de exportação CSV do Revit e indexa no RAG.
    """
    try:
        content = await file.read()
        result = rag.index_revit_export(content.decode("utf-8"))
        return {"message": "Dados indexados com sucesso", "keynotes": result["total_keynotes"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
