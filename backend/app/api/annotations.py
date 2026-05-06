from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.annotation import Annotation as AnnotationModel
from app.schemas.annotation import (
    Annotation,
    AnnotationCreate,
    EntityKind,
)

router = APIRouter(prefix="/api/annotations", tags=["annotations"])


@router.get("", response_model=list[Annotation])
def list_annotations(
    entity_kind: EntityKind = Query(...),
    entity_id: UUID = Query(...),
    db: Session = Depends(get_db),
) -> list[Annotation]:
    stmt = (
        select(AnnotationModel)
        .where(
            AnnotationModel.entity_kind == entity_kind,
            AnnotationModel.entity_id == entity_id,
        )
        .order_by(AnnotationModel.created_at.desc())
    )
    rows = db.execute(stmt).scalars().all()
    return [Annotation.model_validate(r) for r in rows]


@router.post("", response_model=Annotation, status_code=status.HTTP_201_CREATED)
def create_annotation(
    payload: AnnotationCreate,
    db: Session = Depends(get_db),
) -> Annotation:
    row = AnnotationModel(
        entity_kind=payload.entity_kind,
        entity_id=payload.entity_id,
        body=payload.body.strip(),
        severity=payload.severity,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return Annotation.model_validate(row)


@router.delete("/{annotation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_annotation(
    annotation_id: UUID,
    db: Session = Depends(get_db),
) -> Response:
    row = db.execute(
        select(AnnotationModel).where(AnnotationModel.id == annotation_id)
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="annotation not found")
    db.delete(row)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
