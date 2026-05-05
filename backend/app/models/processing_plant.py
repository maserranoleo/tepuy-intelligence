from geoalchemy2 import Geometry
from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, EntityBase


class ProcessingPlant(Base, EntityBase):
    """Gas processing, compression, cryogenic, or refinery gas-treatment plant.

    All plant sub-types share the same schema (POINT, operator, status,
    sources). The discriminating value lives in `properties.plant_type`:
    `"compression" | "processing" | "cryogenic" | "refinery_gas_treatment"`.
    Storing it in JSONB avoids a column migration when new sub-types appear
    (city gates, metering stations, LNG terminals).

    Capacity / throughput attributes also live in `properties` for v1 — the
    documented values across compression vs processing plants use different
    units (mmcfd processed vs HP installed) and aren't worth a column.
    """

    __tablename__ = "processing_plants"

    geometry: Mapped[object] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
        nullable=False,
    )

    operator: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (
        Index("ix_processing_plants_geometry", "geometry", postgresql_using="gist"),
    )
