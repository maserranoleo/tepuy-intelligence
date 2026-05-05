from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.pipeline import Source


class FlareEventProperties(BaseModel):
    id: str
    acquired_at: datetime
    satellite: str | None = None
    instrument: str | None = None
    confidence: str | None = None
    daynight: str | None = None
    brightness_ti4: float | None = None
    brightness_ti5: float | None = None
    frp: float | None = None
    source_name: str
    external_id: str
    sources: list[Source] = Field(default_factory=list)


class FlareEventFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    geometry: dict[str, Any]
    properties: FlareEventProperties


class FlareEventFeatureCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[FlareEventFeature]
