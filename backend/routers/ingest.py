"""
POST /api/ingest — entry point for sensor (or simulator) data.

On each call:
1. Store the BiomarkerReading
2. Fetch latest lifestyle metadata to inform scoring
3. Compute risk score (Layer 1)
4. Compute trajectory from recent history
5. Store RiskAssessment (without Claude text yet)
6. Trigger Claude narrative generation (background thread)
7. Create alert if score >= threshold
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

router = APIRouter(prefix="/api/ingest", tags=["ingest"])


def _update_claude_narrative(reading_id: int, patient: models.Patient, reading: models.BiomarkerReading):
    """Background thread: call Claude and update the RiskAssessment record."""
    from database import SessionLocal
    db = SessionLocal()
    try:
        assessment = (
            db.query(models.RiskAssessment)
            .filter(models.RiskAssessment.reading_id == reading_id)
            .first()
        )
        if not assessment:
            return

        result = claude_client.generate_risk_narrative(
            reading_id=reading_id,
            patient_name=patient.name,
            patient_age=patient.age,
            patient_sex=patient.sex,
            family_history=patient.family_history,
            biomarkers={
                "hemoglobin_ng_ml":     reading.hemoglobin_ng_ml,
                "butyrate_mmol_kg":     reading.butyrate_mmol_kg,
                "calprotectin_ug_g":    reading.calprotectin_ug_g,
                "basidio_ascomy_ratio":  reading.basidio_ascomy_ratio,
                "proteobacteria_index": reading.proteobacteria_index,
                "methylation_score":    reading.methylation_score,
            },
            risk_score=assessment.adjusted_score,
            risk_level=assessment.risk_level,
            trajectory=assessment.trajectory,
            confounded_by=assessment.confounded_by,
        )

        assessment.patient_explanation = result["patient_explanation"]
        assessment.physician_summary = result["physician_summary"]
        assessment.next_steps = result["next_steps"]
        assessment.urgency_flag = result["urgency_flag"]
        db.commit()
    except Exception as e:
        print(f"[ingest] Claude narrative update failed for reading {reading_id}: {e}")
    finally:
        db.close()


@router.post("", status_code=201)
def ingest_reading(body: schemas.ReadingIngest, db: Session = Depends(get_db), skip_narrative: bool = False):
    # Validate patient exists
    patient = db.query(models.Patient).filter(models.Patient.id == body.patient_id).first()
    if not patient:
        raise HTTPException(404, f"Patient {body.patient_id} not found")

    # Persist reading
    reading_data = body.model_dump()
    ts = reading_data.pop("timestamp", None) or datetime.utcnow()
    reading = models.BiomarkerReading(timestamp=ts, **reading_data)
    db.add(reading)
    db.commit()
    db.refresh(reading)

    # Fetch latest lifestyle metadata
    lifestyle = (
        db.query(models.LifestyleMetadata)
        .filter(models.LifestyleMetadata.patient_id == patient.id)
        .order_by(models.LifestyleMetadata.recorded_at.desc())
        .first()
    )
    recent_antibiotics = lifestyle.recent_antibiotic_use if lifestyle else False
    high_fiber = (lifestyle.fiber_intake_g_day or 0) >= 25 if lifestyle else False

    # Layer 1: deterministic scoring
    raw_score, adjusted_score, risk_level, confounded_by, score_breakdown = compute_risk_score(
        reading={
            "hemoglobin_ng_ml":     reading.hemoglobin_ng_ml,
            "butyrate_mmol_kg":     reading.butyrate_mmol_kg,
            "calprotectin_ug_g":    reading.calprotectin_ug_g,
            "basidio_ascomy_ratio":  reading.basidio_ascomy_ratio,
            "proteobacteria_index": reading.proteobacteria_index,
            "methylation_score":    reading.methylation_score,
        },
        patient_age=patient.age,
        patient_family_history=patient.family_history,
        recent_antibiotic_use=recent_antibiotics,
        high_fiber=high_fiber,
    )

    # Trajectory from recent history
    trajectory = compute_trajectory(db, patient.id, adjusted_score)

    # Persist RiskAssessment (Claude fields filled later)
    assessment = models.RiskAssessment(
        reading_id=reading.id,
        patient_id=patient.id,
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

    # Alert creation
    maybe_create_alert(db, patient.id, reading.id, adjusted_score, risk_level, confounded_by)

    # Kick off Claude narrative in background (skipped for historical backfill)
    if not skip_narrative:
        threading.Thread(
            target=_update_claude_narrative,
            args=(reading.id, patient, reading),
            daemon=True,
        ).start()

    return {
        "reading_id": reading.id,
        "assessment_id": assessment.id,
        "adjusted_score": round(adjusted_score, 1),
        "risk_level": risk_level,
        "trajectory": trajectory,
    }
