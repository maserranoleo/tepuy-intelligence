import json
from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException
from geoalchemy2 import Geography
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.flare_event import FlareEvent
from app.models.gas_field import GasField
from app.sanctions.dependency import get_matcher
from app.sanctions.matcher import SanctionsMatcher
from app.schemas.gas_field import (
    GasFieldFeature,
    GasFieldFeatureCollection,
    GasFieldProperties,
)
from app.services.flare_proximity import PROXIMITY_M, WINDOW_DAYS

router = APIRouter(prefix="/api/gas_fields", tags=["gas_fields"])


def _proximity_join_clause():
    """ON-clause for the LEFT JOIN to flare_events: within PROXIMITY_M
    metres of the asset and within the recent WINDOW_DAYS."""
    return sa.and_(
        sa.func.ST_DWithin(
            sa.cast(GasField.geometry, Geography),
            sa.cast(FlareEvent.geometry, Geography),
            PROXIMITY_M,
        ),
        FlareEvent.acquired_at
        >= sa.func.now() - sa.text(f"interval '{WINDOW_DAYS} days'"),
    )


def _row_to_feature(
    row: GasField,
    geojson: str,
    flare_count: int,
    last_flare: datetime | None,
    peak_frp: float | None,
    matcher: SanctionsMatcher,
) -> GasFieldFeature:
    return GasFieldFeature(
        geometry=json.loads(geojson),
        properties=GasFieldProperties(
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


@router.get("", response_model=GasFieldFeatureCollection)
def list_gas_fields(
    db: Session = Depends(get_db),
    matcher: SanctionsMatcher = Depends(get_matcher),
) -> GasFieldFeatureCollection:
    stmt = (
        sa.select(
            GasField,
            sa.func.ST_AsGeoJSON(GasField.geometry),
            sa.func.count(FlareEvent.id).label("flare_count"),
            sa.func.max(FlareEvent.acquired_at).label("last_flare"),
            sa.func.max(FlareEvent.frp).label("peak_frp"),
        )
        .outerjoin(FlareEvent, _proximity_join_clause())
        .group_by(GasField.id)
        .order_by(GasField.name)
    )
    features = [
        _row_to_feature(row, geojson, count, last_flare, peak_frp, matcher)
        for row, geojson, count, last_flare, peak_frp in db.execute(stmt).all()
    ]
    return GasFieldFeatureCollection(features=features)


@router.get("/{gas_field_id}", response_model=GasFieldFeature)
def get_gas_field(
    gas_field_id: UUID,
    db: Session = Depends(get_db),
    matcher: SanctionsMatcher = Depends(get_matcher),
) -> GasFieldFeature:
    stmt = (
        sa.select(
            GasField,
            sa.func.ST_AsGeoJSON(GasField.geometry),
            sa.func.count(FlareEvent.id).label("flare_count"),
            sa.func.max(FlareEvent.acquired_at).label("last_flare"),
            sa.func.max(FlareEvent.frp).label("peak_frp"),
        )
        .outerjoin(FlareEvent, _proximity_join_clause())
        .where(GasField.id == gas_field_id)
        .group_by(GasField.id)
    )
    result = db.execute(stmt).first()
    if result is None:
        raise HTTPException(status_code=404, detail="gas field not found")
    row, geojson, count, last_flare, peak_frp = result
    return _row_to_feature(row, geojson, count, last_flare, peak_frp, matcher)
