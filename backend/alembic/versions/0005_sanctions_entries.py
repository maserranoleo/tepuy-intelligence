"""sanctions_entries reference table

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-04
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sanctions_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ent_num", sa.Integer, nullable=False, unique=True),
        sa.Column("sdn_name", sa.String, nullable=False),
        sa.Column("sdn_name_normalized", sa.String, nullable=False),
        sa.Column("sdn_type", sa.String, nullable=True),
        sa.Column(
            "programs",
            postgresql.ARRAY(sa.String),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("title", sa.String, nullable=True),
        sa.Column("remarks", sa.Text, nullable=True),
        sa.Column("source_url", sa.String, nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "raw",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_sanctions_entries_name_norm",
        "sanctions_entries",
        ["sdn_name_normalized"],
    )
    op.create_index(
        "ix_sanctions_entries_programs",
        "sanctions_entries",
        ["programs"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_sanctions_entries_programs", table_name="sanctions_entries")
    op.drop_index("ix_sanctions_entries_name_norm", table_name="sanctions_entries")
    op.drop_table("sanctions_entries")
