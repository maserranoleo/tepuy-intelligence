import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Index, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class FlareEvent(Base):
    """A satellite-detected thermal anomaly (candidate flare or fire).

    NOT an `EntityBase` — a flare event is a timestamped observation, not a
    long-lived asset with a name and status. We keep `sources` JSONB for
    provenance and an `external_id` for idempotent re-ingest. Persistence
    (was this flare detected at the same coordinates yesterday?) is computed
    downstream, not stored as a column.
    """

    __tablename__ = "flare_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    geometry: Mapped[object] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
        nullable=False,
    )

    acquired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    satellite: Mapped[str | None] = mapped_column(String, nullable=True)
    instrument: Mapped[str | None] = mapped_column(String, nullable=True)
    confidence: Mapped[str | None] = mapped_column(String, nullable=True)  # low/nominal/high or 0-100
    daynight: Mapped[str | None] = mapped_column(String(1), nullable=True)  # D or N
    brightness_ti4: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    brightness_ti5: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    frp: Mapped[float | None] = mapped_column(Numeric, nullable=True)  # fire radiative power, MW

    source_name: Mapped[str] = mapped_column(String, nullable=False)
    external_id: Mapped[str] = mapped_column(String, nullable=False)
    sources: Mapped[list] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_flare_events_geometry", "geometry", postgresql_using="gist"),
        Index("ix_flare_events_acquired_at", "acquired_at"),
        Index(
            "uq_flare_events_source_external",
            "source_name",
            "external_id",
            unique=True,
        ),
    )
