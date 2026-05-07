"""
VEDA — Vertex AI Embeddings + Cosine Similarity
Generates startup embeddings and finds similar past audits.
No external vector DB — cosine similarity in-memory.
"""
import json
import logging
import math
import os
from typing import Optional
from utils.config import PROJECT_ID, LOCATION

logger = logging.getLogger(__name__)

_EMBEDDING_MODEL = "text-embedding-004"
_STORE_FILE      = "/tmp/veda_embeddings.json"


def _get_embedding(text: str) -> list[float]:
    """Generate embedding using Vertex AI text-embedding model."""
    import vertexai
    from vertexai.language_models import TextEmbeddingModel
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    model  = TextEmbeddingModel.from_pretrained(_EMBEDDING_MODEL)
    result = model.get_embeddings([text[:3000]])
    return result[0].values


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot   = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _load_store() -> list[dict]:
    try:
        if os.path.exists(_STORE_FILE):
            with open(_STORE_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return []


def _save_store(store: list[dict]) -> None:
    try:
        with open(_STORE_FILE, "w") as f:
            json.dump(store, f)
    except Exception as exc:
        logger.warning("[Embeddings] Save failed: %s", exc)


def store_startup_embedding(
    job_id: str,
    company_name: str,
    industry: str,
    summary: str,
    scores: dict,
) -> bool:
    """Generate and store embedding for a completed audit."""
    try:
        text      = f"{company_name} {industry} {summary}"
        embedding = _get_embedding(text)
        store     = _load_store()

        # Remove old entry for same company if exists
        store = [s for s in store if s.get("company_name") != company_name]
        store.append({
            "job_id":       job_id,
            "company_name": company_name,
            "industry":     industry,
            "summary":      summary[:500],
            "scores":       scores,
            "embedding":    embedding,
        })
        _save_store(store)
        logger.info("[Embeddings] Stored embedding for: %s", company_name)
        return True
    except Exception as exc:
        logger.warning("[Embeddings] Store failed: %s", exc)
        return False


def find_similar_startups(query_summary: str, top_k: int = 3) -> list[dict]:
    """Find top-k similar startups using cosine similarity."""
    try:
        store = _load_store()
        if not store:
            return []

        query_embedding = _get_embedding(query_summary)
        scored = []
        for item in store:
            emb = item.get("embedding")
            if not emb:
                continue
            sim = _cosine_similarity(query_embedding, emb)
            scored.append({
                "company_name": item["company_name"],
                "industry":     item["industry"],
                "summary":      item["summary"],
                "scores":       item.get("scores", {}),
                "similarity":   round(sim, 4),
                "job_id":       item["job_id"],
            })

        scored.sort(key=lambda x: x["similarity"], reverse=True)
        return scored[:top_k]

    except Exception as exc:
        logger.warning("[Embeddings] Similarity search failed: %s", exc)
        return []
