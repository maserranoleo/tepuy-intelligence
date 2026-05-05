"""flare_events observation table

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-04
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "flare_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "geometry",
            Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("satellite", sa.String, nullable=True),
        sa.Column("instrument", sa.String, nullable=True),
        sa.Column("confidence", sa.String, nullable=True),
        sa.Column("daynight", sa.String(length=1), nullable=True),
        sa.Column("brightness_ti4", sa.Numeric, nullable=True),
        sa.Column("brightness_ti5", sa.Numeric, nullable=True),
        sa.Column("frp", sa.Numeric, nullable=True),
        sa.Column("source_name", sa.String, nullable=False),
        sa.Column("external_id", sa.String, nullable=False),
        sa.Column(
            "sources",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_flare_events_geometry", "flare_events", ["geometry"], postgresql_using="gist"
    )
    op.create_index(
        "ix_flare_events_acquired_at", "flare_events", ["acquired_at"]
    )
    op.create_index(
        "uq_flare_events_source_external",
        "flare_events",
        ["source_name", "external_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_flare_events_source_external", table_name="flare_events")
    op.drop_index("ix_flare_events_acquired_at", table_name="flare_events")
    op.drop_index("ix_flare_events_geometry", table_name="flare_events")
    op.drop_table("flare_events")
