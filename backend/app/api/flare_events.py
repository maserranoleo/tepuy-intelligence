import json
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.flare_event import FlareEvent
from app.schemas.flare_event import (
    FlareEventFeature,
    FlareEventFeatureCollection,
    FlareEventProperties,
)

router = APIRouter(prefix="/api/flare_events", tags=["flare_events"])

DEFAULT_DAYS = 14
MAX_DAYS = 30


def _row_to_feature(row: FlareEvent, geojson: str) -> FlareEventFeature:
    return FlareEventFeature(
        geometry=json.loads(geojson),
        properties=FlareEventProperties(
            id=str(row.id),
            acquired_at=row.acquired_at,
            satellite=row.satellite,
            instrument=row.instrument,
            confidence=row.confidence,
            daynight=row.daynight,
            brightness_ti4=float(row.brightness_ti4) if row.brightness_ti4 is not None else None,
            brightness_ti5=float(row.brightness_ti5) if row.brightness_ti5 is not None else None,
            frp=float(row.frp) if row.frp is not None else None,
            source_name=row.source_name,
            external_id=row.external_id,
            sources=row.sources or [],
        ),
    )


@router.get("", response_model=FlareEventFeatureCollection)
def list_flare_events(
    days: int = Query(DEFAULT_DAYS, ge=1, le=MAX_DAYS),
    db: Session = Depends(get_db),
) -> FlareEventFeatureCollection:
    cutoff = datetime.now(UTC) - timedelta(days=days)
    stmt = (
        select(FlareEvent, func.ST_AsGeoJSON(FlareEvent.geometry))
        .where(FlareEvent.acquired_at >= cutoff)
        .order_by(FlareEvent.acquired_at.desc())
    )
    features = [_row_to_feature(row, geojson) for row, geojson in db.execute(stmt).all()]
    return FlareEventFeatureCollection(features=features)
