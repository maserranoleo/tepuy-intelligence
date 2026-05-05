"""init: postgis + pipelines

Revision ID: 0001
Revises:
Create Date: 2026-05-04
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "pipelines",
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
            Geometry(geometry_type="MULTILINESTRING", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("length_km", sa.Numeric, nullable=True),
        sa.Column("diameter_in", sa.Numeric, nullable=True),
        sa.Column("capacity_mmcfd", sa.Numeric, nullable=True),
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
        "ix_pipelines_geometry", "pipelines", ["geometry"], postgresql_using="gist"
    )
    op.create_index(
        "ix_pipelines_external_ids_gem",
        "pipelines",
        ["external_ids"],
        postgresql_using="gin",
        postgresql_ops={"external_ids": "jsonb_path_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_pipelines_external_ids_gem", table_name="pipelines")
    op.drop_index("ix_pipelines_geometry", table_name="pipelines")
    op.drop_table("pipelines")
