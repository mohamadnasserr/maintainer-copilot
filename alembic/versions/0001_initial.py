"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-20
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "widget_configs",
        sa.Column("widget_id", sa.Text(), primary_key=True),
        sa.Column("allowed_origins", sa.JSON(), nullable=False),
        sa.Column("theme", sa.JSON(), nullable=False),
        sa.Column("greeting", sa.Text(), nullable=False),
        sa.Column("enabled_tools", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("actor", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("target", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("repo", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )
    op.execute("ALTER TABLE document_chunks ADD COLUMN embedding vector(1536)")


def downgrade() -> None:
    op.drop_table("document_chunks")
    op.drop_table("audit_logs")
    op.drop_table("widget_configs")

