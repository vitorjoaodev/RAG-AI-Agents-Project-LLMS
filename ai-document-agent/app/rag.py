"""
RAG (Retrieval-Augmented Generation) para dados do Revit
Indexa e consulta Keynotes, áreas, comprimentos e contagens
"""

import os
import io
import csv
from typing import Optional
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from langchain.chains import RetrievalQA


class RevitRAG:
    """
    RAG especializado em dados exportados do Revit.
    Replica a lógica de agrupamento por Keynote do workflow n8n.
    """

    def __init__(self):
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        self.llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            openai_api_key=os.getenv("OPENAI_API_KEY"),
        )
        self.vectorstore: Optional[Chroma] = None
        self._load_existing_index()

    def _load_existing_index(self):
        """Carrega índice existente se houver."""
        persist_path = "./chroma_db"
        if os.path.exists(persist_path):
            self.vectorstore = Chroma(
                persist_directory=persist_path,
                embedding_function=self.embeddings,
            )

    def group_by_keynote(self, rows: list[dict]) -> dict:
        """
        Agrupa linhas do Revit por Keynote.
        Replica exatamente a lógica do Code node no n8n.
        """
        grouped = {}

        for row in rows:
            # Limpar tabs e espaços (mesmo tratamento do n8n)
            area = row.get("Area", "")
            length = row.get("Lenght", row.get("\tLenght", ""))
            count = row.get("Count", row.get("\tCount", ""))
            keynote = row.get("Keynote", row.get("        Keynote", ""))
            status = row.get("Status", row.get("        Status", ""))

            keynote_clean = str(keynote).replace("\t", "").replace(" ", "").strip()

            if not keynote_clean or len(keynote_clean) < 3:
                continue

            if keynote_clean not in grouped:
                grouped[keynote_clean] = {
                    "keynote": keynote_clean,
                    "status": "",
                    "areas": [],
                    "lengths": [],
                    "counts": [],
                }

            try:
                area_num = float(str(area).replace("\t", "").replace(" ", ""))
                if area_num > 0:
                    grouped[keynote_clean]["areas"].append(area_num)
            except (ValueError, TypeError):
                pass

            try:
                length_num = float(str(length).replace("\t", "").replace(" ", ""))
                if length_num > 0:
                    grouped[keynote_clean]["lengths"].append(length_num)
            except (ValueError, TypeError):
                pass

            try:
                count_num = float(str(count).replace("\t", "").replace(" ", ""))
                if count_num > 0:
                    grouped[keynote_clean]["counts"].append(count_num)
            except (ValueError, TypeError):
                pass

            status_clean = str(status).replace("\t", " ").strip()
            if status_clean and not grouped[keynote_clean]["status"]:
                grouped[keynote_clean]["status"] = status_clean

        return grouped

    def format_grouped_data(self, grouped: dict) -> list[dict]:
        """Formata os dados agrupados para output."""
        result = []
        for group in grouped.values():
            areas = group["areas"]
            lengths = group["lengths"]
            counts = group["counts"]

            area_text = ""
            if areas:
                area_text = f"({len(areas)} resultados): {' + '.join(map(str, areas))} / Soma = {sum(areas):.2f}"

            length_text = ""
            if lengths:
                length_text = f"({len(lengths)} resultados): {' + '.join(map(str, lengths))} / Soma = {sum(lengths):.2f}"

            count_text = ""
            if counts:
                counts_int = [round(c) for c in counts]
                count_text = f"({len(counts_int)} resultados): {' + '.join(map(str, counts_int))} / Soma = {round(sum(counts))}"

            result.append(
                {
                    "Código": group["keynote"],
                    "Status": group["status"],
                    "AREA m2": area_text,
                    "COMPRIMENTO m": length_text,
                    "CONTAGEM UNID": count_text,
                }
            )

        return result

    def index_revit_export(self, csv_content: str) -> dict:
        """
        Indexa exportação CSV do Revit no vectorstore.
        Permite consultas em linguagem natural depois.
        """
        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)

        grouped = self.group_by_keynote(rows)
        formatted = self.format_grouped_data(grouped)

        # Criar documentos para o vectorstore
        documents = []
        for item in formatted:
            content = (
                f"Keynote: {item['Código']}\n"
                f"Status: {item['Status']}\n"
                f"Área (m²): {item['AREA m2']}\n"
                f"Comprimento (m): {item['COMPRIMENTO m']}\n"
                f"Contagem (unid): {item['CONTAGEM UNID']}"
            )
            documents.append(
                Document(page_content=content, metadata={"keynote": item["Código"]})
            )

        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        splits = splitter.split_documents(documents)

        self.vectorstore = Chroma.from_documents(
            documents=splits,
            embedding=self.embeddings,
            persist_directory="./chroma_db",
        )
        self.vectorstore.persist()

        return {"total_keynotes": len(formatted), "indexed_chunks": len(splits)}

    def query_keynote(self, keynote: str) -> dict:
        """Consulta informações de um Keynote específico."""
        if not self.vectorstore:
            return {"error": "Nenhum dado indexado. Faça upload de uma exportação do Revit."}

        docs = self.vectorstore.similarity_search(f"Keynote {keynote}", k=3)
        if not docs:
            return {"error": f"Keynote '{keynote}' não encontrado."}

        return {"keynote": keynote, "data": [d.page_content for d in docs]}

    def ask(self, question: str) -> str:
        """Responde perguntas em linguagem natural sobre os dados do Revit."""
        if not self.vectorstore:
            return "Nenhum dado indexado ainda. Faça upload de uma exportação do Revit."

        qa = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.vectorstore.as_retriever(search_kwargs={"k": 4}),
        )
        return qa.run(question)
