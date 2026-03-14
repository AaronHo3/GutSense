from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
import schemas

router = APIRouter(prefix="/api/patients/{patient_id}/risk", tags=["risk"])


@router.get("/latest", response_model=schemas.RiskAssessmentOut)
def latest_risk(patient_id: int, db: Session = Depends(get_db)):
    assessment = (
        db.query(models.RiskAssessment)
        .filter(models.RiskAssessment.patient_id == patient_id)
        .order_by(models.RiskAssessment.timestamp.desc())
        .first()
    )
    if not assessment:
        raise HTTPException(404, "No risk assessment found")
    return assessment


@router.get("/history", response_model=list[schemas.RiskAssessmentOut])
def risk_history(patient_id: int, limit: int = 180, db: Session = Depends(get_db)):
    return (
        db.query(models.RiskAssessment)
        .filter(models.RiskAssessment.patient_id == patient_id)
        .order_by(models.RiskAssessment.timestamp.asc())
        .limit(limit)
        .all()
    )
