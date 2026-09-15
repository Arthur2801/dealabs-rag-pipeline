"""Recherche vectorielle et synthèse des bons plans indexés."""

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from pymongo import MongoClient
from sentence_transformers import SentenceTransformer

MODEL_ID = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DATABASE = "deals_db"
COLLECTION = "deals"
VECTOR_INDEX = "vector_index"

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


@lru_cache(maxsize=1)
def _collection():
    uri = os.getenv("MONGO_URI")
    if not uri:
        raise RuntimeError("MONGO_URI est requis")
    client = MongoClient(uri, serverSelectionTimeoutMS=10000)
    return client[DATABASE][COLLECTION]


@lru_cache(maxsize=1)
def _embedding_model():
    return SentenceTransformer(MODEL_ID)


def get_deals_rag(query: str, max_price: float = 1200, limit: int = 5) -> list[dict]:
    """Trouver les deals les plus proches sémantiquement sous un prix plafond."""
    query = query.strip()
    if not query:
        return []

    vector = _embedding_model().encode(query, convert_to_numpy=True).tolist()
    pipeline = [
        {
            "$vectorSearch": {
                "index": VECTOR_INDEX,
                "path": "embedding",
                "queryVector": vector,
                "numCandidates": max(100, limit * 20),
                "limit": limit,
                "filter": {"price": {"$lte": max_price}},
            }
        },
        {
            "$project": {
                "title": 1,
                "price": 1,
                "group_display_summary": 1,
                "url": 1,
                "text": 1,
                "score": {"$meta": "vectorSearchScore"},
            }
        },
    ]
    return list(_collection().aggregate(pipeline))


def get_llm_answer(query: str, deals: list[dict], language: str = "fr") -> str | None:
    """Résumer les résultats récupérés ; retourner None si Groq n'est pas configuré."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or not deals:
        return None

    context = "\n".join(
        (
            f"{number}. {deal.get('title', 'Sans titre')} | "
            f"prix: {deal.get('price', 'inconnu')} EUR | "
            f"catégorie: {deal.get('group_display_summary', 'inconnue')} | "
            f"lien: {deal.get('url', 'indisponible')} | "
            f"description: {str(deal.get('text') or '')[:500]}"
        )
        for number, deal in enumerate(deals, 1)
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Tu aides à comparer des bons plans. Réponds dans la langue indiquée. "
                "Utilise uniquement les résultats fournis. Ne crée ni prix, ni produit, "
                "ni caractéristique absents du contexte. Si l'information manque, dis-le.",
            ),
            (
                "human",
                "Langue : {language}\nRecherche : {query}\nRésultats :\n{context}",
            ),
        ]
    )
    llm = ChatGroq(
        groq_api_key=api_key,
        model_name="openai/gpt-oss-20b",
        temperature=0,
    )
    return (prompt | llm).invoke(
        {"language": language, "query": query, "context": context}
    ).content
