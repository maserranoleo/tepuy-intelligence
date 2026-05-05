"""gas_fields entity

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-04
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "gas_fields",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("name_es", sa.String, nullable=True),
        sa.Column(
            "aliases",
            postgresql.ARRAY(sa.String),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("status", sa.String, nullable=False, server_default="unknown"),
        sa.Column("status_as_of", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "properties",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "external_ids",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "sources",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "geometry",
            Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("operator", sa.String, nullable=True),
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
        "ix_gas_fields_geometry", "gas_fields", ["geometry"], postgresql_using="gist"
    )


def downgrade() -> None:
    op.drop_index("ix_gas_fields_geometry", table_name="gas_fields")
    op.drop_table("gas_fields")
