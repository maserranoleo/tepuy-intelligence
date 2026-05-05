import uuid
from datetime import datetime

from sqlalchemy import ARRAY, DateTime, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SanctionsEntry(Base):
    """OFAC SDN (Specially Designated Nationals) reference entry.

    Reference data — not an `EntityBase`. We don't carry name aliases,
    geometry, or user-facing status; we keep enough to support fuzzy-match
    of operator strings against the list and to cite the OFAC entry in
    the UI.

    Idempotency: upsert keyed on `ent_num` (OFAC's stable entity number).
    """

    __tablename__ = "sanctions_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    ent_num: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    sdn_name: Mapped[str] = mapped_column(String, nullable=False)
    sdn_name_normalized: Mapped[str] = mapped_column(String, nullable=False)
    sdn_type: Mapped[str | None] = mapped_column(String, nullable=True)
    programs: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list, server_default="{}"
    )
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)

    source_url: Mapped[str] = mapped_column(String, nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    raw: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_sanctions_entries_name_norm", "sdn_name_normalized"),
        Index("ix_sanctions_entries_programs", "programs", postgresql_using="gin"),
    )
