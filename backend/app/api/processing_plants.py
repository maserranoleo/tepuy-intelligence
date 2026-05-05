import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.processing_plant import ProcessingPlant
from app.sanctions.dependency import get_matcher
from app.sanctions.matcher import SanctionsMatcher
from app.schemas.processing_plant import (
    ProcessingPlantFeature,
    ProcessingPlantFeatureCollection,
    ProcessingPlantProperties,
)

router = APIRouter(prefix="/api/processing_plants", tags=["processing_plants"])


def _row_to_feature(
    row: ProcessingPlant, geojson: str, matcher: SanctionsMatcher
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
        ),
    )


@router.get("", response_model=ProcessingPlantFeatureCollection)
def list_processing_plants(
    db: Session = Depends(get_db),
    matcher: SanctionsMatcher = Depends(get_matcher),
) -> ProcessingPlantFeatureCollection:
    stmt = select(ProcessingPlant, func.ST_AsGeoJSON(ProcessingPlant.geometry)).order_by(
        ProcessingPlant.name
    )
    features = [
        _row_to_feature(row, geojson, matcher)
        for row, geojson in db.execute(stmt).all()
    ]
    return ProcessingPlantFeatureCollection(features=features)


@router.get("/{processing_plant_id}", response_model=ProcessingPlantFeature)
def get_processing_plant(
    processing_plant_id: UUID,
    db: Session = Depends(get_db),
    matcher: SanctionsMatcher = Depends(get_matcher),
) -> ProcessingPlantFeature:
    stmt = select(ProcessingPlant, func.ST_AsGeoJSON(ProcessingPlant.geometry)).where(
        ProcessingPlant.id == processing_plant_id
    )
    result = db.execute(stmt).first()
    if result is None:
        raise HTTPException(status_code=404, detail="processing plant not found")
    row, geojson = result
    return _row_to_feature(row, geojson, matcher)
