"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-05
"""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analyses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("repo_url", sa.String(500), nullable=False, index=True),
        sa.Column("repo_hash", sa.String(64), nullable=False, index=True),
        sa.Column("commit_sha", sa.String(40), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("progress", sa.JSON),
        sa.Column("plan_output", sa.JSON),
        sa.Column("mimar_output", sa.JSON),
        sa.Column("tarihci_output", sa.JSON),
        sa.Column("dedektif_output", sa.JSON),
        sa.Column("onboarding_output", sa.JSON),
        sa.Column("error", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime),
    )
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("analysis_id", sa.String(36), sa.ForeignKey("analyses.id"), nullable=False, index=True),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("sources", sa.JSON),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("chat_messages")
    op.drop_table("analyses")
