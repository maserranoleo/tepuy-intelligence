import uuid
from datetime import datetime

from sqlalchemy import ARRAY, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class EntityBase:
    """Shared columns for every entity in the zoo (pipelines today; fields,
    plants, terminals, flares, incidents, operators tomorrow)."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    name_es: Mapped[str | None] = mapped_column(String, nullable=True)
    aliases: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list, server_default="{}"
    )
    status: Mapped[str] = mapped_column(String, nullable=False, default="unknown")
    status_as_of: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    properties: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")
    external_ids: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")
    sources: Mapped[list] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
