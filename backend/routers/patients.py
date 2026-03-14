from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
import schemas

router = APIRouter(prefix="/api/patients", tags=["patients"])


@router.get("", response_model=list[schemas.PatientOut])
def list_patients(db: Session = Depends(get_db)):
    return db.query(models.Patient).order_by(models.Patient.id).all()


@router.get("/{patient_id}", response_model=schemas.PatientOut)
def get_patient(patient_id: int, db: Session = Depends(get_db)):
    p = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not p:
        raise HTTPException(404, "Patient not found")
    return p


@router.post("", response_model=schemas.PatientOut, status_code=201)
def create_patient(body: schemas.PatientCreate, db: Session = Depends(get_db)):
    p = models.Patient(**body.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p
