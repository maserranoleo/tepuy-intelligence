from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.pipeline import Source
from app.schemas.sanctions import SanctionsMatch


class GasFieldProperties(BaseModel):
    """Properties block of a gas-field GeoJSON Feature.

    Reservoir-type, reserves estimate, and basin live in `properties` (the
    JSONB escape valve) rather than as dedicated columns.
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
    sanctions: list[SanctionsMatch] = Field(default_factory=list)


class GasFieldFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    geometry: dict[str, Any]
    properties: GasFieldProperties


class GasFieldFeatureCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[GasFieldFeature]
