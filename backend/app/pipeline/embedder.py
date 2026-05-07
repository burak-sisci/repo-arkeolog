"""Gemini text-embedding-004 ile chunk vektörleştirme ve Qdrant'a yazım."""
from __future__ import annotations
import asyncio
import logging
from app.pipeline.chunker import CodeChunk
from app.llm.gemini import gemini_client
from app.config import settings

logger = logging.getLogger(__name__)

BATCH_SIZE = 20  # Gemini embedding batch limit


async def embed_chunks(analysis_id: str, chunks: list[CodeChunk]) -> None:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct

    if not chunks:
        return

    qdrant = QdrantClient(url=settings.qdrant_url)
    collection_name = f"repo_{analysis_id}"

    # Create collection
    qdrant.recreate_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=768, distance=Distance.COSINE),
    )

    # Embed in batches
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]
        texts = [f"{c.file_path}\n{c.name}\n{c.code}" for c in batch]
        try:
            vectors = await gemini_client.embed_batch(texts)
        except Exception as e:
            logger.error(f"Embedding batch {i//BATCH_SIZE} failed: {e}")
            # Use zero vectors as fallback so pipeline continues
            vectors = [[0.0] * 768 for _ in batch]

        points = [
            PointStruct(
                id=i + j,
                vector=vec,
                payload={
                    "file_path": c.file_path,
                    "start_line": c.start_line,
                    "end_line": c.end_line,
                    "chunk_type": c.chunk_type,
                    "name": c.name,
                    "language": c.language,
                    "code": c.code,
                },
            )
            for j, (c, vec) in enumerate(zip(batch, vectors))
        ]
        qdrant.upsert(collection_name=collection_name, points=points)
        await asyncio.sleep(0.1)  # Be gentle with rate limits

    logger.info(f"Embedded {len(chunks)} chunks into {collection_name}")
