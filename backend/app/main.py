from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analyze, chat, ws, health
from app.config import settings

app = FastAPI(
    title="RepoArkeolog API",
    description="GitHub repository multi-agent analysis tool",
    version="0.1.0",
)

# CORS — production'da CORS_ORIGINS env değişkeniyle kısıtlanır.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(health.router, prefix="/api")
app.include_router(ws.router)
