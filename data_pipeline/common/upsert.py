"""Upsert helpers shared across ingestion sources.

Idempotency model: each source provides a unique external ID, stored in the
target row's `external_ids` JSONB under a per-source key (e.g. `"gem"` or
`"manual_seed"`). We look up by that key, update if found, insert if not.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from shapely.geometry.base import BaseGeometry
from shapely.geometry import MultiLineString
from sqlalchemy import select
from sqlalchemy.orm import Session
from geoalchemy2.shape import from_shape

from app.models.pipeline import Pipeline


@dataclass
class SourceRef:
    source_name: str
    source_id: str | None = None
    url: str | None = None
    note: str | None = None
    retrieved_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_jsonb(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "source_id": self.source_id,
            "url": self.url,
            "note": self.note,
            "retrieved_at": self.retrieved_at.isoformat(),
        }


@dataclass
class PipelineRecord:
    """Normalized pipeline record ready to upsert."""

    source_name: str
    external_id: str
    name: str
    geometry: BaseGeometry  # LineString or MultiLineString
    name_es: str | None = None
    aliases: list[str] = field(default_factory=list)
    status: str = "unknown"
    status_as_of: datetime | None = None
    length_km: float | None = None
    diameter_in: float | None = None
    capacity_mmcfd: float | None = None
    operator: str | None = None
    properties: dict[str, Any] = field(default_factory=dict)
    sources: list[SourceRef] = field(default_factory=list)


def _to_multilinestring(geom: BaseGeometry) -> MultiLineString:
    if isinstance(geom, MultiLineString):
        return geom
    if geom.geom_type == "LineString":
        return MultiLineString([geom])
    raise ValueError(f"unsupported pipeline geometry: {geom.geom_type}")


def upsert_pipeline(db: Session, rec: PipelineRecord) -> Pipeline:
    """Look up by external_ids[source_name] = external_id; update or insert."""
    stmt = select(Pipeline).where(
        Pipeline.external_ids[rec.source_name].astext == rec.external_id
    )
    row = db.execute(stmt).scalar_one_or_none()

    geom = from_shape(_to_multilinestring(rec.geometry), srid=4326)

    if row is None:
        row = Pipeline(
            name=rec.name,
            name_es=rec.name_es,
            aliases=rec.aliases,
            status=rec.status,
            status_as_of=rec.status_as_of,
            length_km=rec.length_km,
            diameter_in=rec.diameter_in,
            capacity_mmcfd=rec.capacity_mmcfd,
            operator=rec.operator,
            geometry=geom,
            properties=rec.properties,
            external_ids={rec.source_name: rec.external_id},
            sources=[s.to_jsonb() for s in rec.sources],
        )
        db.add(row)
    else:
        row.name = rec.name
        row.name_es = rec.name_es
        row.aliases = rec.aliases
        row.status = rec.status
        row.status_as_of = rec.status_as_of
        row.length_km = rec.length_km
        row.diameter_in = rec.diameter_in
        row.capacity_mmcfd = rec.capacity_mmcfd
        row.operator = rec.operator
        row.geometry = geom
        row.properties = rec.properties
        row.external_ids = {**(row.external_ids or {}), rec.source_name: rec.external_id}
        row.sources = [s.to_jsonb() for s in rec.sources]
    return row
