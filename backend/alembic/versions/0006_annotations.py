"""annotations table

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-04
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "annotations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_kind", sa.String, nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("severity", sa.String, nullable=False, server_default="info"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_annotations_entity",
        "annotations",
        ["entity_kind", "entity_id"],
    )
    op.create_index(
        "ix_annotations_created_at",
        "annotations",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_annotations_created_at", table_name="annotations")
    op.drop_index("ix_annotations_entity", table_name="annotations")
    op.drop_table("annotations")
