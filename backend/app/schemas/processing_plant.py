from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.pipeline import Source


class ProcessingPlantProperties(BaseModel):
    """Properties block of a processing-plant GeoJSON Feature.

    `plant_type` (compression / processing / cryogenic / refinery_gas_treatment)
    and capacity attributes live in `properties` JSONB rather than as columns.
    """

    id: str
    name: str
    name_es: str | None = None
    aliases: list[str] = Field(default_factory=list)
    status: str
    status_as_of: datetime | None = None
    operator: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)
    external_ids: dict[str, str] = Field(default_factory=dict)
    sources: list[Source] = Field(default_factory=list)


class ProcessingPlantFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    geometry: dict[str, Any]
    properties: ProcessingPlantProperties


class ProcessingPlantFeatureCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[ProcessingPlantFeature]
