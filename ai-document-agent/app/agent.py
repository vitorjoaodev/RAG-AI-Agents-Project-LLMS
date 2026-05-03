"""
BIM Agent - Agente de IA para dados Revit
Replica e expande o workflow n8n com agente LangChain
"""

import os
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferWindowMemory

import gspread
from google.oauth2.service_account import Credentials

from app.rag import RevitRAG


# --- Google Sheets Helper ---

def get_sheets_client():
    """Retorna cliente Google Sheets autenticado."""
    scopes = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(
        os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "credentials.json"),
        scopes=scopes,
    )
    return gspread.authorize(creds)


# --- Tools do Agente ---

rag_instance = RevitRAG()

@tool
def consultar_keynote(keynote: str) -> str:
    """
    Consulta dados de um Keynote específico do Revit.
    Use quando o usuário perguntar sobre um código ou elemento específico.
    """
    result = rag_instance.query_keynote(keynote)
    if "error" in result:
        return result["error"]
    return "\n".join(result["data"])


@tool
def perguntar_sobre_revit(pergunta: str) -> str:
    """
    Responde perguntas em linguagem natural sobre os dados do Revit indexados.
    Use para perguntas como: 'qual elemento tem maior área?', 'liste todos os status', etc.
    """
    return rag_instance.ask(pergunta)


@tool
def processar_planilhas(revit_url: str, catalog_url: str, output_url: str) -> str:
    """
    Processa as planilhas do Revit: lê, agrupa por Keynote, cruza com cadastro e atualiza saída.
    Replica o workflow n8n completo.
    """
    try:
        client = get_sheets_client()

        # 1. Ler planilha Revit
        revit_sh = client.open_by_url(revit_url).sheet1
        revit_data = revit_sh.get_all_records()

        # 2. Agrupar por Keynote (lógica do Code node n8n)
        grouped = rag_instance.group_by_keynote(revit_data)
        formatted = rag_instance.format_grouped_data(grouped)

        # 3. Ler cadastro
        catalog_sh = client.open_by_url(catalog_url).sheet1
        catalog_data = catalog_sh.get_all_records()
        catalog_map = {str(r.get("Código", "")).strip(): r for r in catalog_data}

        # 4. Cruzar dados
        merged = []
        for item in formatted:
            cat = catalog_map.get(item["Código"], {})
            merged.append({**cat, **item})

        # 5. Limpar e atualizar planilha de saída
        output_sh = client.open_by_url(output_url).sheet1
        if merged:
            headers = list(merged[0].keys())
            rows = [list(r.values()) for r in merged]
            output_sh.clear()
            output_sh.append_row(headers)
            output_sh.append_rows(rows)

        return f"✅ Processado com sucesso! {len(merged)} Keynotes atualizados na planilha de saída."

    except Exception as e:
        return f"❌ Erro ao processar planilhas: {str(e)}"


# --- BIM Agent ---

class BIMAgent:
    """
    Agente de IA com memória para conversas sobre dados Revit.
    Replica e expande o agente n8n (chatTrigger + memoryBufferWindow + OpenAI).
    """

    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            temperature=0,
        )
        self.tools = [consultar_keynote, perguntar_sobre_revit, processar_planilhas]
        self.sessions: dict[str, AgentExecutor] = {}

    def _create_session(self, session_id: str) -> AgentExecutor:
        """Cria nova sessão de agente com memória (replica memoryBufferWindow do n8n)."""
        memory = ConversationBufferWindowMemory(
            k=10,  # últimas 10 mensagens (mesmo padrão do n8n)
            memory_key="chat_history",
            return_messages=True,
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """Você é um assistente especialista em dados BIM/Revit.
Você ajuda engenheiros e arquitetos a entender dados exportados do Revit,
como Keynotes, áreas, comprimentos e contagens de elementos construtivos.

Quando o usuário perguntar sobre dados, use as ferramentas disponíveis.
Responda sempre em português do Brasil de forma clara e objetiva.""",
                ),
                MessagesPlaceholder(variable_name="chat_history"),
                ("user", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        agent = create_openai_tools_agent(self.llm, self.tools, prompt)
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=memory,
            verbose=True,
            max_iterations=5,
        )

    async def chat(self, message: str, session_id: str = "default") -> str:
        """Processa mensagem com memória de sessão."""
        if session_id not in self.sessions:
            self.sessions[session_id] = self._create_session(session_id)

        executor = self.sessions[session_id]
        result = executor.invoke({"input": message})
        return result["output"]

    async def process_sheets(
        self, revit_url: str, catalog_url: str, output_url: str
    ) -> dict:
        """Processa planilhas diretamente via API."""
        msg = processar_planilhas.invoke(
            {"revit_url": revit_url, "catalog_url": catalog_url, "output_url": output_url}
        )
        return {"message": msg}
