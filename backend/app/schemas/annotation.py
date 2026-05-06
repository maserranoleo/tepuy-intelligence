from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

EntityKind = Literal["pipeline", "gas_field", "processing_plant"]
Severity = Literal["info", "watch", "risk"]


class AnnotationCreate(BaseModel):
    entity_kind: EntityKind
    entity_id: UUID
    body: str = Field(..., min_length=1, max_length=2000)
    severity: Severity = "info"


class Annotation(BaseModel):
    id: UUID
    entity_kind: EntityKind
    entity_id: UUID
    body: str
    severity: Severity
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
