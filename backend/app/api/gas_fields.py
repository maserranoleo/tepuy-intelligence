import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.gas_field import GasField
from app.sanctions.dependency import get_matcher
from app.sanctions.matcher import SanctionsMatcher
from app.schemas.gas_field import (
    GasFieldFeature,
    GasFieldFeatureCollection,
    GasFieldProperties,
)

router = APIRouter(prefix="/api/gas_fields", tags=["gas_fields"])


def _row_to_feature(
    row: GasField, geojson: str, matcher: SanctionsMatcher
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
        ),
    )


@router.get("", response_model=GasFieldFeatureCollection)
def list_gas_fields(
    db: Session = Depends(get_db),
    matcher: SanctionsMatcher = Depends(get_matcher),
) -> GasFieldFeatureCollection:
    stmt = select(GasField, func.ST_AsGeoJSON(GasField.geometry)).order_by(GasField.name)
    features = [
        _row_to_feature(row, geojson, matcher)
        for row, geojson in db.execute(stmt).all()
    ]
    return GasFieldFeatureCollection(features=features)


@router.get("/{gas_field_id}", response_model=GasFieldFeature)
def get_gas_field(
    gas_field_id: UUID,
    db: Session = Depends(get_db),
    matcher: SanctionsMatcher = Depends(get_matcher),
) -> GasFieldFeature:
    stmt = select(GasField, func.ST_AsGeoJSON(GasField.geometry)).where(
        GasField.id == gas_field_id
    )
    result = db.execute(stmt).first()
    if result is None:
        raise HTTPException(status_code=404, detail="gas field not found")
    row, geojson = result
    return _row_to_feature(row, geojson, matcher)
