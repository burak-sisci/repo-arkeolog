"""RAG chat zinciri — sorgu → retrieval → Gemini streaming."""
from __future__ import annotations
import logging
from app.rag.retriever import retrieve_chunks
from app.llm.gemini import gemini_client

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Sen bu repo hakkında soruları yanıtlayan bir asistansın. Aşağıda repodan
ilgili kod parçaları ve önceki analizlerden ilgili özetler var. Bu bağlamı
kullanarak kullanıcının sorusunu yanıtla.

KURAL: Sadece verilen bağlamdan yararlan. Bağlamda olmayan şey için
"Bu repoda bu konuda bilgi bulamadım" de.

Cevap dilini kullanıcının diline uydur."""


async def stream_chat(
    analysis_id: str,
    question: str,
    mimar_output: dict | None,
    dedektif_output: dict | None,
):
    # 1. Retrieve relevant chunks
    chunks = await retrieve_chunks(analysis_id, question, top_k=8)
    sources = [
        {"file": c["file_path"], "lines": f"{c['start_line']}-{c['end_line']}", "name": c["name"]}
        for c in chunks
    ]
    yield {"type": "sources", "sources": sources}

    # 2. Build context
    chunks_text = "\n\n".join(
        f"--- {c['file_path']}:{c['start_line']}-{c['end_line']} ---\n{c['code']}"
        for c in chunks
    )

    mimar_ctx = ""
    if mimar_output and "modules" in mimar_output:
        q_lower = question.lower()
        relevant = [
            m for m in mimar_output["modules"]
            if any(kw in m.get("path", "").lower() or kw in m.get("purpose", "").lower()
                   for kw in q_lower.split())
        ]
        if relevant:
            import json
            mimar_ctx = json.dumps(relevant, ensure_ascii=False)

    dedektif_ctx = ""
    if dedektif_output and "issues" in dedektif_output:
        q_lower = question.lower()
        relevant = [
            i for i in dedektif_output["issues"]
            if any(kw in (i.get("file_path") or "").lower() or kw in (i.get("description") or "").lower()
                   for kw in q_lower.split())
        ]
        if relevant:
            import json
            dedektif_ctx = json.dumps(relevant[:5], ensure_ascii=False)

    context = f"""İLGİLİ KOD PARÇALARI:
{chunks_text}

İLGİLİ MİMARİ BİLGİSİ:
{mimar_ctx or "(bulunamadı)"}

İLGİLİ TEKNİK BORÇLAR:
{dedektif_ctx or "(bulunamadı)"}"""

    # 3. Stream response
    user_prompt = f"Bağlam:\n{context}\n\nSoru: {question}"
    try:
        async for text_chunk in gemini_client.stream_generate(SYSTEM_PROMPT, user_prompt):
            yield {"type": "chunk", "content": text_chunk}
    except Exception as e:
        logger.error(f"Chat generation failed: {e}")
        yield {"type": "chunk", "content": f"Cevap üretilirken hata oluştu: {e}"}

    yield {"type": "done"}
