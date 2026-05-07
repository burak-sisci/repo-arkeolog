from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy import String, DateTime, JSON, Text, ForeignKey
from datetime import datetime
import uuid

Base = declarative_base()


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repo_url: Mapped[str] = mapped_column(String(500), index=True)
    repo_hash: Mapped[str] = mapped_column(String(64), index=True)
    commit_sha: Mapped[str] = mapped_column(String(40), default="")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    progress: Mapped[dict] = mapped_column(JSON, default=dict)

    plan_output: Mapped[dict | None] = mapped_column(JSON)
    mimar_output: Mapped[dict | None] = mapped_column(JSON)
    tarihci_output: Mapped[dict | None] = mapped_column(JSON)
    dedektif_output: Mapped[dict | None] = mapped_column(JSON)
    onboarding_output: Mapped[dict | None] = mapped_column(JSON)

    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    sources: Mapped[list | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
