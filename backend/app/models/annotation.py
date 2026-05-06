import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Annotation(Base):
    """Analyst-authored note attached to a long-lived entity.

    NOT an `EntityBase` — annotations are user-generated content, not assets.
    Single-user model in v1: no author column; add when auth lands.

    `entity_kind` is a free string (pipeline / gas_field / processing_plant).
    We don't FK on entity_id because entity tables differ per kind; the API
    layer enforces the kind/id pair.
    """

    __tablename__ = "annotations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    entity_kind: Mapped[str] = mapped_column(String, nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    body: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False, default="info")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_annotations_entity", "entity_kind", "entity_id"),
        Index("ix_annotations_created_at", "created_at"),
    )
