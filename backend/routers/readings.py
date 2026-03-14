from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from database import get_db
import models
import schemas

router = APIRouter(prefix="/api/patients/{patient_id}/readings", tags=["readings"])


@router.get("", response_model=list[schemas.ReadingOut])
def get_readings(
    patient_id: int,
    limit: int = Query(default=180, le=500),
    db: Session = Depends(get_db),
):
    return (
        db.query(models.BiomarkerReading)
        .filter(models.BiomarkerReading.patient_id == patient_id)
        .order_by(models.BiomarkerReading.timestamp.asc())
        .limit(limit)
        .all()
    )
