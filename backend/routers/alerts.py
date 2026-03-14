from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
import schemas

router = APIRouter(prefix="/api/patients/{patient_id}/alerts", tags=["alerts"])


@router.get("", response_model=list[schemas.AlertOut])
def get_alerts(patient_id: int, acknowledged: bool = False, db: Session = Depends(get_db)):
    q = db.query(models.Alert).filter(models.Alert.patient_id == patient_id)
    if not acknowledged:
        q = q.filter(models.Alert.acknowledged == False)
    return q.order_by(models.Alert.created_at.desc()).all()


@router.post("/{alert_id}/acknowledge", response_model=schemas.AlertOut)
def acknowledge_alert(patient_id: int, alert_id: int, db: Session = Depends(get_db)):
    alert = (
        db.query(models.Alert)
        .filter(models.Alert.id == alert_id, models.Alert.patient_id == patient_id)
        .first()
    )
    if not alert:
        raise HTTPException(404, "Alert not found")
    alert.acknowledged = True
    db.commit()
    db.refresh(alert)
    return alert
