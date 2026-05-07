from pydantic import BaseModel, HttpUrl
from typing import Literal, Any


class AnalyzeRequest(BaseModel):
    repo_url: str
    branch: str = "main"


class AnalyzeResponse(BaseModel):
    analysis_id: str
    status: str
    cached: bool = False


class ProgressUpdate(BaseModel):
    analysis_id: str
    stage: Literal["mining", "planning", "mimar", "tarihci", "dedektif", "onboarding", "done", "error"]
    message: str
    progress_pct: int


class AnalysisResult(BaseModel):
    analysis_id: str
    status: str
    repo_url: str
    progress: dict
    results: dict | None = None
    error: str | None = None
    created_at: str
    completed_at: str | None = None


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    content: str
    sources: list[dict]


class UsageStatus(BaseModel):
    gemini_status: Literal["green", "yellow", "red"]
    groq_status: Literal["green", "yellow", "red"]
    gemini_rpm_current: int
    groq_rpm_current: int
