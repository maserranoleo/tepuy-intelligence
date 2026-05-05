import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.pipeline import Pipeline
from app.sanctions.dependency import get_matcher
from app.sanctions.matcher import SanctionsMatcher
from app.schemas.pipeline import (
    PipelineFeature,
    PipelineFeatureCollection,
    PipelineProperties,
)

router = APIRouter(prefix="/api/pipelines", tags=["pipelines"])


def _row_to_feature(
    row: Pipeline, geojson: str, matcher: SanctionsMatcher
) -> PipelineFeature:
    return PipelineFeature(
        geometry=json.loads(geojson),
        properties=PipelineProperties(
            id=str(row.id),
            name=row.name,
            name_es=row.name_es,
            aliases=list(row.aliases or []),
            status=row.status,
            status_as_of=row.status_as_of,
            length_km=float(row.length_km) if row.length_km is not None else None,
            diameter_in=float(row.diameter_in) if row.diameter_in is not None else None,
            capacity_mmcfd=float(row.capacity_mmcfd) if row.capacity_mmcfd is not None else None,
            operator=row.operator,
            properties=row.properties or {},
            external_ids=row.external_ids or {},
            sources=row.sources or [],
            sanctions=[m.to_jsonable() for m in matcher.match(row.operator)],
        ),
    )


@router.get("", response_model=PipelineFeatureCollection)
def list_pipelines(
    db: Session = Depends(get_db),
    matcher: SanctionsMatcher = Depends(get_matcher),
) -> PipelineFeatureCollection:
    stmt = select(Pipeline, func.ST_AsGeoJSON(Pipeline.geometry)).order_by(Pipeline.name)
    features = [
        _row_to_feature(row, geojson, matcher)
        for row, geojson in db.execute(stmt).all()
    ]
    return PipelineFeatureCollection(features=features)


@router.get("/{pipeline_id}", response_model=PipelineFeature)
def get_pipeline(
    pipeline_id: UUID,
    db: Session = Depends(get_db),
    matcher: SanctionsMatcher = Depends(get_matcher),
) -> PipelineFeature:
    stmt = select(Pipeline, func.ST_AsGeoJSON(Pipeline.geometry)).where(
        Pipeline.id == pipeline_id
    )
    result = db.execute(stmt).first()
    if result is None:
        raise HTTPException(status_code=404, detail="pipeline not found")
    row, geojson = result
    return _row_to_feature(row, geojson, matcher)
