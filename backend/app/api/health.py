from fastapi import APIRouter
from app.schemas import UsageStatus
from app.llm.usage_tracker import usage_tracker

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/usage", response_model=UsageStatus)
async def usage_status():
    return usage_tracker.get_status()
