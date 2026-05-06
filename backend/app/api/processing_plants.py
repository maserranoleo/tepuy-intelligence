import json
from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException
from geoalchemy2 import Geography
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.flare_event import FlareEvent
from app.models.processing_plant import ProcessingPlant
from app.sanctions.dependency import get_matcher
from app.sanctions.matcher import SanctionsMatcher
from app.schemas.processing_plant import (
    ProcessingPlantFeature,
    ProcessingPlantFeatureCollection,
    ProcessingPlantProperties,
)
from app.services.flare_proximity import PROXIMITY_M, WINDOW_DAYS

router = APIRouter(prefix="/api/processing_plants", tags=["processing_plants"])


def _proximity_join_clause():
    return sa.and_(
        sa.func.ST_DWithin(
            sa.cast(ProcessingPlant.geometry, Geography),
            sa.cast(FlareEvent.geometry, Geography),
            PROXIMITY_M,
        ),
        FlareEvent.acquired_at
        >= sa.func.now() - sa.text(f"interval '{WINDOW_DAYS} days'"),
    )


def _row_to_feature(
    row: ProcessingPlant,
    geojson: str,
    flare_count: int,
    last_flare: datetime | None,
    peak_frp: float | None,
    matcher: SanctionsMatcher,
) -> ProcessingPlantFeature:
    return ProcessingPlantFeature(
        geometry=json.loads(geojson),
        properties=ProcessingPlantProperties(
            id=str(row.id),
            name=row.name,
            name_es=row.name_es,
            aliases=list(row.aliases or []),
            status=row.status,
            status_as_of=row.status_as_of,
            operator=row.operator,
            properties=row.properties or {},
            external_ids=row.external_ids or {},
            sources=row.sources or [],
            sanctions=[m.to_jsonable() for m in matcher.match(row.operator)],
            recent_flare_count=int(flare_count or 0),
            last_flare_at=last_flare,
            peak_frp_mw=float(peak_frp) if peak_frp is not None else None,
        ),
    )


@router.get("", response_model=ProcessingPlantFeatureCollection)
def list_processing_plants(
    db: Session = Depends(get_db),
    matcher: SanctionsMatcher = Depends(get_matcher),
) -> ProcessingPlantFeatureCollection:
    stmt = (
        sa.select(
            ProcessingPlant,
            sa.func.ST_AsGeoJSON(ProcessingPlant.geometry),
            sa.func.count(FlareEvent.id).label("flare_count"),
            sa.func.max(FlareEvent.acquired_at).label("last_flare"),
            sa.func.max(FlareEvent.frp).label("peak_frp"),
        )
        .outerjoin(FlareEvent, _proximity_join_clause())
        .group_by(ProcessingPlant.id)
        .order_by(ProcessingPlant.name)
    )
    features = [
        _row_to_feature(row, geojson, count, last_flare, peak_frp, matcher)
        for row, geojson, count, last_flare, peak_frp in db.execute(stmt).all()
    ]
    return ProcessingPlantFeatureCollection(features=features)


@router.get("/{processing_plant_id}", response_model=ProcessingPlantFeature)
def get_processing_plant(
    processing_plant_id: UUID,
    db: Session = Depends(get_db),
    matcher: SanctionsMatcher = Depends(get_matcher),
) -> ProcessingPlantFeature:
    stmt = (
        sa.select(
            ProcessingPlant,
            sa.func.ST_AsGeoJSON(ProcessingPlant.geometry),
            sa.func.count(FlareEvent.id).label("flare_count"),
            sa.func.max(FlareEvent.acquired_at).label("last_flare"),
            sa.func.max(FlareEvent.frp).label("peak_frp"),
        )
        .outerjoin(FlareEvent, _proximity_join_clause())
        .where(ProcessingPlant.id == processing_plant_id)
        .group_by(ProcessingPlant.id)
    )
    result = db.execute(stmt).first()
    if result is None:
        raise HTTPException(status_code=404, detail="processing plant not found")
    row, geojson, count, last_flare, peak_frp = result
    return _row_to_feature(row, geojson, count, last_flare, peak_frp, matcher)
