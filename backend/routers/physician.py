"""
Physician-specific endpoints:
- GET  /api/physician/patients          — roster sorted by risk score
- POST /api/patients/{id}/notes         — add clinical note
- GET  /api/patients/{id}/notes         — list notes
- POST /api/patients/{id}/lifestyle     — update lifestyle metadata
- GET  /api/patients/{id}/lifestyle     — get latest lifestyle metadata
- POST /api/patients/{id}/simulate-spike — inject a critical reading (demo)
"""

import threading
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
import schemas
from services.ai_risk_model import compute_risk_score, urgency_from_level
from services.alert_service import maybe_create_alert
from services.trend_analyzer import compute_trajectory
from services import claude_client
from routers.ingest import _update_claude_narrative

router = APIRouter(tags=["physician"])


# ── Patient roster ─────────────────────────────────────────────────────────────

@router.get("/api/physician/patients", response_model=list[schemas.PatientSummary])
def physician_roster(db: Session = Depends(get_db)):
    patients = db.query(models.Patient).all()
    summaries = []
    for p in patients:
        latest_risk = (
            db.query(models.RiskAssessment)
            .filter(models.RiskAssessment.patient_id == p.id)
            .order_by(models.RiskAssessment.timestamp.desc())
            .first()
        )
        latest_reading = (
            db.query(models.BiomarkerReading)
            .filter(models.BiomarkerReading.patient_id == p.id)
            .order_by(models.BiomarkerReading.timestamp.desc())
            .first()
        )
        unack_alerts = (
            db.query(models.Alert)
            .filter(models.Alert.patient_id == p.id, models.Alert.acknowledged == False)
            .count()
        )
        summaries.append(schemas.PatientSummary(
            patient=p,
            latest_risk=latest_risk,
            unacknowledged_alerts=unack_alerts,
            latest_reading=latest_reading,
        ))

    # Sort by adjusted_score descending (highest risk first)
    summaries.sort(
        key=lambda s: s.latest_risk.adjusted_score if s.latest_risk else 0,
        reverse=True,
    )
    return summaries


# ── Clinical notes ─────────────────────────────────────────────────────────────

@router.post("/api/patients/{patient_id}/notes", response_model=schemas.ClinicalNoteOut, status_code=201)
def add_note(patient_id: int, body: schemas.ClinicalNoteCreate, db: Session = Depends(get_db)):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(404, "Patient not found")
    note = models.ClinicalNote(patient_id=patient_id, **body.model_dump())
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.get("/api/patients/{patient_id}/notes", response_model=list[schemas.ClinicalNoteOut])
def get_notes(patient_id: int, db: Session = Depends(get_db)):
    return (
        db.query(models.ClinicalNote)
        .filter(models.ClinicalNote.patient_id == patient_id)
        .order_by(models.ClinicalNote.created_at.desc())
        .all()
    )


# ── Lifestyle metadata ─────────────────────────────────────────────────────────

@router.post("/api/patients/{patient_id}/lifestyle", response_model=schemas.LifestyleMetadataOut, status_code=201)
def update_lifestyle(patient_id: int, body: schemas.LifestyleMetadataCreate, db: Session = Depends(get_db)):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(404, "Patient not found")
    meta = models.LifestyleMetadata(patient_id=patient_id, **body.model_dump())
    db.add(meta)
    db.commit()
    db.refresh(meta)
    return meta


@router.get("/api/patients/{patient_id}/lifestyle", response_model=schemas.LifestyleMetadataOut | None)
def get_lifestyle(patient_id: int, db: Session = Depends(get_db)):
    return (
        db.query(models.LifestyleMetadata)
        .filter(models.LifestyleMetadata.patient_id == patient_id)
        .order_by(models.LifestyleMetadata.recorded_at.desc())
        .first()
    )


# ── Demo: Simulate spike ───────────────────────────────────────────────────────

SPIKE_READING = {
    "mpo_ng_ml":            850.0,
    "haptoglobin_ug_g":     310.0,
    "fibrinogen_ng_ml":     680.0,
    "mmp9_ng_ml":           240.0,
    "hemoglobin_fit_ng_ml": 175.0,
    "mmp8_ng_ml":           235.0,
    "pgrp_s_ng_ml":         185.0,
    "calprotectin_ug_g":    430.0,
}


@router.post("/api/patients/{patient_id}/simulate-spike", status_code=201)
def simulate_spike(patient_id: int, db: Session = Depends(get_db)):
    """Inject a critical-level reading for demo purposes."""
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(404, "Patient not found")

    last = (
        db.query(models.BiomarkerReading)
        .filter(models.BiomarkerReading.patient_id == patient_id)
        .order_by(models.BiomarkerReading.timestamp.desc())
        .first()
    )
    visit_num = (last.visit_number + 1) if last else 1

    reading = models.BiomarkerReading(
        patient_id=patient_id,
        timestamp=datetime.utcnow(),
        visit_number=visit_num,
        **SPIKE_READING,
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)

    raw_score, adjusted_score, risk_level, confounded_by, score_breakdown = compute_risk_score(
        reading=SPIKE_READING,
        patient_age=patient.age,
        patient_family_history=patient.family_history,
    )
    trajectory = compute_trajectory(db, patient_id, adjusted_score)

    assessment = models.RiskAssessment(
        reading_id=reading.id,
        patient_id=patient_id,
        raw_score=raw_score,
        adjusted_score=adjusted_score,
        risk_level=risk_level,
        trajectory=trajectory,
        confounded_by=confounded_by,
        score_breakdown=score_breakdown,
        urgency_flag=urgency_from_level(risk_level),
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    maybe_create_alert(db, patient_id, reading.id, adjusted_score, risk_level, confounded_by)

    threading.Thread(
        target=_update_claude_narrative,
        args=(reading.id, patient, reading),
        daemon=True,
    ).start()

    return {
        "reading_id": reading.id,
        "adjusted_score": round(adjusted_score, 1),
        "risk_level": risk_level,
    }


# ── Referral generation ────────────────────────────────────────────────────────

@router.post("/api/patients/{patient_id}/referral")
def generate_referral(patient_id: int, db: Session = Depends(get_db)):
    """Generate a GI referral letter for the patient using Claude."""
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(404, "Patient not found")

    reading = (
        db.query(models.BiomarkerReading)
        .filter(models.BiomarkerReading.patient_id == patient_id)
        .order_by(models.BiomarkerReading.timestamp.desc())
        .first()
    )
    assessment = (
        db.query(models.RiskAssessment)
        .filter(models.RiskAssessment.patient_id == patient_id)
        .order_by(models.RiskAssessment.timestamp.desc())
        .first()
    )
    if not reading or not assessment:
        raise HTTPException(404, "No readings or assessment found")

    biomarkers = {
        "mpo_ng_ml":            reading.mpo_ng_ml,
        "haptoglobin_ug_g":     reading.haptoglobin_ug_g,
        "fibrinogen_ng_ml":     reading.fibrinogen_ng_ml,
        "mmp9_ng_ml":           reading.mmp9_ng_ml,
        "hemoglobin_fit_ng_ml": reading.hemoglobin_fit_ng_ml,
        "mmp8_ng_ml":           reading.mmp8_ng_ml,
        "pgrp_s_ng_ml":         reading.pgrp_s_ng_ml,
        "calprotectin_ug_g":    reading.calprotectin_ug_g,
    }

    letter = claude_client.generate_referral(
        patient_name=patient.name,
        patient_age=patient.age,
        patient_sex=patient.sex,
        family_history=patient.family_history,
        has_nod2_variant=getattr(patient, "has_nod2_variant", False),
        biomarkers=biomarkers,
        risk_score=assessment.adjusted_score,
        risk_level=assessment.risk_level,
        trajectory=assessment.trajectory,
        physician_summary=assessment.physician_summary or "",
        next_steps=assessment.next_steps or [],
    )
    return {"letter": letter, "risk_level": assessment.risk_level, "risk_score": round(assessment.adjusted_score, 1)}


@router.post("/api/patients/{patient_id}/referral/send", status_code=201)
def send_referral(patient_id: int, body: dict, db: Session = Depends(get_db)):
    """Save the referral letter as a clinical note (simulates sending)."""
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(404, "Patient not found")

    letter = body.get("letter", "")
    if not letter:
        raise HTTPException(400, "Letter text is required")

    note = models.ClinicalNote(
        patient_id=patient_id,
        note_text=f"[REFERRAL SENT]\n\n{letter}",
        is_physician_recommendation=True,
    )
    db.add(note)
    db.commit()
    return {"sent": True, "message": "Referral logged as clinical note"}


# ── Recalculate score with current lifestyle ────────────────────────────────────

@router.post("/api/patients/{patient_id}/recalculate", response_model=schemas.RiskAssessmentOut)
def recalculate_score(patient_id: int, db: Session = Depends(get_db)):
    """Re-run risk scoring on the latest reading using current lifestyle data."""
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(404, "Patient not found")

    reading = (
        db.query(models.BiomarkerReading)
        .filter(models.BiomarkerReading.patient_id == patient_id)
        .order_by(models.BiomarkerReading.timestamp.desc())
        .first()
    )
    if not reading:
        raise HTTPException(404, "No readings found for patient")

    assessment = (
        db.query(models.RiskAssessment)
        .filter(models.RiskAssessment.patient_id == patient_id)
        .order_by(models.RiskAssessment.timestamp.desc())
        .first()
    )
    if not assessment:
        raise HTTPException(404, "No assessment found for patient")

    lifestyle = (
        db.query(models.LifestyleMetadata)
        .filter(models.LifestyleMetadata.patient_id == patient_id)
        .order_by(models.LifestyleMetadata.recorded_at.desc())
        .first()
    )
    recent_antibiotics = lifestyle.recent_antibiotic_use if lifestyle else False
    high_fiber = (lifestyle.fiber_intake_g_day or 0) >= 25 if lifestyle else False

    reading_dict = {
        "mpo_ng_ml":            reading.mpo_ng_ml,
        "haptoglobin_ug_g":     reading.haptoglobin_ug_g,
        "fibrinogen_ng_ml":     reading.fibrinogen_ng_ml,
        "mmp9_ng_ml":           reading.mmp9_ng_ml,
        "hemoglobin_fit_ng_ml": reading.hemoglobin_fit_ng_ml,
        "mmp8_ng_ml":           reading.mmp8_ng_ml,
        "pgrp_s_ng_ml":         reading.pgrp_s_ng_ml,
        "calprotectin_ug_g":    reading.calprotectin_ug_g,
    }

    raw_score, adjusted_score, risk_level, confounded_by, score_breakdown = compute_risk_score(
        reading=reading_dict,
        patient_age=patient.age,
        patient_family_history=patient.family_history,
        recent_antibiotic_use=recent_antibiotics,
        high_fiber=high_fiber,
    )
    trajectory = compute_trajectory(db, patient_id, adjusted_score)

    assessment.raw_score = raw_score
    assessment.adjusted_score = adjusted_score
    assessment.risk_level = risk_level
    assessment.trajectory = trajectory
    assessment.confounded_by = confounded_by
    assessment.score_breakdown = score_breakdown
    assessment.urgency_flag = urgency_from_level(risk_level)
    db.commit()
    db.refresh(assessment)
    return assessment
