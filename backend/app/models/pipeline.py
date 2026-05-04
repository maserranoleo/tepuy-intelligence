from geoalchemy2 import Geometry
from sqlalchemy import Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, EntityBase


class Pipeline(Base, EntityBase):
    __tablename__ = "pipelines"

    geometry: Mapped[object] = mapped_column(
        Geometry(geometry_type="MULTILINESTRING", srid=4326, spatial_index=False),
        nullable=False,
    )

    length_km: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    diameter_in: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    capacity_mmcfd: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    operator: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (
        Index("ix_pipelines_geometry", "geometry", postgresql_using="gist"),
        Index(
            "ix_pipelines_external_ids_gem",
            "external_ids",
            postgresql_using="btree",
            postgresql_ops={"external_ids": "jsonb_path_ops"},
        ),
    )
