from collections.abc import Iterator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.sanctions.matcher import SanctionsMatcher


def get_matcher(db: Session = Depends(get_db)) -> Iterator[SanctionsMatcher]:
    """Build a fresh SanctionsMatcher per request.

    Cheap (~ms) for the full SDN list; reused across every row in a single
    response. If you later want a longer-lived cache, swap in a TTL-cached
    factory here without touching the call sites.
    """
    yield SanctionsMatcher.from_db(db)
