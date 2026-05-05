from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.sanctions import SanctionsMatch


class Source(BaseModel):
    source_name: str
    source_id: str | None = None
    retrieved_at: datetime
    url: str | None = None
    note: str | None = None


class PipelineProperties(BaseModel):
    """Properties block of a pipeline GeoJSON Feature.

    Documented schema — keep stable; downstream clients depend on these keys.
    """

    id: str
    name: str
    name_es: str | None = None
    aliases: list[str] = Field(default_factory=list)
    status: str
    status_as_of: datetime | None = None
    length_km: float | None = None
    diameter_in: float | None = None
    capacity_mmcfd: float | None = None
    operator: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)
    external_ids: dict[str, str] = Field(default_factory=dict)
    sources: list[Source] = Field(default_factory=list)
    sanctions: list[SanctionsMatch] = Field(default_factory=list)


class PipelineFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    geometry: dict[str, Any]
    properties: PipelineProperties


class PipelineFeatureCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[PipelineFeature]
