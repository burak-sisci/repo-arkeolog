"""Qdrant üzerinde semantik kod arama."""
from __future__ import annotations
import logging
from app.llm.gemini import gemini_client
from app.config import settings

logger = logging.getLogger(__name__)


async def retrieve_chunks(analysis_id: str, query: str, top_k: int = 8) -> list[dict]:
    from qdrant_client import QdrantClient

    try:
        query_vec = await gemini_client.embed_query(query)
    except Exception as e:
        logger.error(f"Query embedding failed: {e}")
        return []

    try:
        qdrant = QdrantClient(url=settings.qdrant_url)
        results = qdrant.search(
            collection_name=f"repo_{analysis_id}",
            query_vector=query_vec,
            limit=top_k,
            with_payload=True,
        )
    except Exception as e:
        logger.error(f"Qdrant search failed: {e}")
        return []

    chunks = []
    for r in results:
        payload = r.payload or {}
        chunks.append(
            {
                "file_path": payload.get("file_path", ""),
                "start_line": payload.get("start_line", 0),
                "end_line": payload.get("end_line", 0),
                "name": payload.get("name", ""),
                "language": payload.get("language", ""),
                "code": payload.get("code", ""),
                "score": r.score,
            }
        )

    # Re-rank: slightly boost chunks whose file_path contains query keywords
    query_lower = query.lower()
    for chunk in chunks:
        if any(kw in chunk["file_path"].lower() for kw in query_lower.split()):
            chunk["score"] = min(chunk["score"] + 0.05, 1.0)

    chunks.sort(key=lambda c: -c["score"])
    return chunks[:5]
