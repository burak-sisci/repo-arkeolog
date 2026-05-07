from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import analyze, chat, ws, health

app = FastAPI(
    title="RepoArkeolog API",
    description="GitHub repository multi-agent analysis tool",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(health.router, prefix="/api")
app.include_router(ws.router)
