from geoalchemy2 import Geometry
from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, EntityBase


class GasField(Base, EntityBase):
    """Gas-bearing reservoir / field. Geometry is a representative point
    (centroid of the licence area or the principal platform location).

    Reservoir-specific attributes (reservoir_type, reserves_tcf, basin) live
    in `properties` JSONB — `EntityBase` exists for exactly this case.
    """

    __tablename__ = "gas_fields"

    geometry: Mapped[object] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
        nullable=False,
    )

    operator: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (
        Index("ix_gas_fields_geometry", "geometry", postgresql_using="gist"),
    )
