import json
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Analysis, ChatMessage
from app.schemas import ChatRequest
from app.rag.chat_chain import stream_chat

router = APIRouter()


@router.post("/chat/{analysis_id}")
async def chat_with_repo(
    analysis_id: str,
    req: ChatRequest,
    db: Session = Depends(get_db),
):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analiz bulunamadı.")
    if analysis.status != "done":
        raise HTTPException(status_code=400, detail="Analiz henüz tamamlanmadı.")

    # Save user message
    user_msg = ChatMessage(
        id=str(uuid.uuid4()),
        analysis_id=analysis_id,
        role="user",
        content=req.message,
        created_at=datetime.utcnow(),
    )
    db.add(user_msg)
    db.commit()

    async def event_stream():
        collected = []
        sources = []
        try:
            async for chunk in stream_chat(
                analysis_id=analysis_id,
                question=req.message,
                mimar_output=analysis.mimar_output,
                dedektif_output=analysis.dedektif_output,
            ):
                if chunk["type"] == "sources":
                    sources = chunk["sources"]
                    yield f"data: {json.dumps(chunk)}\n\n"
                elif chunk["type"] == "chunk":
                    collected.append(chunk["content"])
                    yield f"data: {json.dumps(chunk)}\n\n"
                elif chunk["type"] == "done":
                    yield f"data: {json.dumps(chunk)}\n\n"
        finally:
            # Persist assistant message
            full_content = "".join(collected)
            assistant_msg = ChatMessage(
                id=str(uuid.uuid4()),
                analysis_id=analysis_id,
                role="assistant",
                content=full_content,
                sources=sources,
                created_at=datetime.utcnow(),
            )
            db.add(assistant_msg)
            db.commit()

    return StreamingResponse(event_stream(), media_type="text/event-stream")
