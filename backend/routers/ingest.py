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


def _get_similar_scores(db: Session, exclude_patient_id: int, reading: dict, top_k: int = 3) -> list:
    """
    Fast kNN on raw biomarker values using SQLite — no embeddings, no external calls.
    Returns the adjusted risk scores of the top_k most similar recent readings
    from other patients. Used as RAG features for the NN scorer.
    """
    try:
        recent = (
            db.query(models.RiskAssessment, models.BiomarkerReading)
            .join(models.BiomarkerReading, models.RiskAssessment.reading_id == models.BiomarkerReading.id)
            .filter(models.BiomarkerReading.patient_id != exclude_patient_id)
            .order_by(models.RiskAssessment.timestamp.desc())
            .limit(200)
            .all()
        )
        if not recent:
            return []

        def dist(br: models.BiomarkerReading) -> float:
            return (
                abs(br.hemoglobin_fit_ng_ml - reading["hemoglobin_fit_ng_ml"]) / 100.0 +
                abs(br.calprotectin_ug_g    - reading["calprotectin_ug_g"])    / 200.0 +
                abs(br.mpo_ng_ml            - reading["mpo_ng_ml"])            / 500.0 +
                abs(br.mmp9_ng_ml           - reading["mmp9_ng_ml"])           / 150.0 +
                abs(br.mmp8_ng_ml           - reading["mmp8_ng_ml"])           / 150.0 +
                abs(br.fibrinogen_ng_ml     - reading["fibrinogen_ng_ml"])     / 400.0 +
                abs(br.haptoglobin_ug_g     - reading["haptoglobin_ug_g"])     / 200.0 +
                abs(br.pgrp_s_ng_ml         - reading["pgrp_s_ng_ml"])         / 100.0
            )

        nearest = sorted(recent, key=lambda x: dist(x[1]))[:top_k]
        return [float(ra.adjusted_score) for ra, _ in nearest]
    except Exception as e:
        print(f"[ingest] kNN lookup failed (non-fatal): {e}")
        return []


def _build_clinical_text(patient, reading: models.BiomarkerReading, assessment: models.RiskAssessment) -> str:
    """Build a human-readable FHIR-style clinical text string for embedding."""
    sex_label = "male" if patient.sex == "M" else "female"
    fhx = "positive family history of CRC" if patient.family_history else "no family history"
    return (
        f"Patient: {patient.age}-year-old {sex_label}, {fhx}. "
        f"Risk score: {assessment.adjusted_score:.0f}/100, level: {assessment.risk_level}, "
        f"trajectory: {assessment.trajectory}. "
        f"FHIR Observations — "
        f"Hgb-FIT: {reading.hemoglobin_fit_ng_ml:.1f} ng/mL, "
        f"Calprotectin: {reading.calprotectin_ug_g:.0f} µg/g, "
        f"MPO: {reading.mpo_ng_ml:.1f} ng/mL, "
        f"MMP-9: {reading.mmp9_ng_ml:.1f} ng/mL, "
        f"MMP-8: {reading.mmp8_ng_ml:.1f} ng/mL, "
        f"Fibrinogen: {reading.fibrinogen_ng_ml:.1f} ng/mL, "
        f"Haptoglobin: {reading.haptoglobin_ug_g:.1f} µg/g, "
        f"PGRP-S: {reading.pgrp_s_ng_ml:.1f} ng/mL."
    )


def _update_claude_narrative(reading_id: int, patient: models.Patient, reading: models.BiomarkerReading):
    """
    Background thread:
    1. Build FHIR clinical text for this reading
    2. Fetch RAG context from IRIS (similar historical cases via vector search)
    3. Generate Claude narrative with pooled [current obs + RAG context]
    4. Update SQLite RiskAssessment with narrative
    5. Store this observation in IRIS (joins the RAG pool for future patients)
    """
    from database import SessionLocal
    from services import iris_native

    db = SessionLocal()
    try:
        assessment = (
            db.query(models.RiskAssessment)
            .filter(models.RiskAssessment.reading_id == reading_id)
            .first()
        )
        if not assessment:
            return

        # Step 1: build FHIR-style clinical text
        clinical_text = _build_clinical_text(patient, reading, assessment)

        # Step 2: RAG — fetch similar historical cases from IRIS
        rag_context = []
        try:
            rag_context = iris_native.get_rag_context(
                clinical_text=clinical_text,
                exclude_patient_id=str(patient.id),
                top_k=3,
            )
            if rag_context:
                print(f"[ingest] RAG: {len(rag_context)} similar cases retrieved from IRIS for reading {reading_id}")
        except Exception as e:
            print(f"[ingest] RAG fetch failed (non-fatal): {e}")

        # Step 3: Claude narrative with RAG context pooled in
        result = claude_client.generate_risk_narrative(
            reading_id=reading_id,
            patient_name=patient.name,
            patient_age=patient.age,
            patient_sex=patient.sex,
            family_history=patient.family_history,
            biomarkers={
                "mpo_ng_ml":            reading.mpo_ng_ml,
                "haptoglobin_ug_g":     reading.haptoglobin_ug_g,
                "fibrinogen_ng_ml":     reading.fibrinogen_ng_ml,
                "mmp9_ng_ml":           reading.mmp9_ng_ml,
                "hemoglobin_fit_ng_ml": reading.hemoglobin_fit_ng_ml,
                "mmp8_ng_ml":           reading.mmp8_ng_ml,
                "pgrp_s_ng_ml":         reading.pgrp_s_ng_ml,
                "calprotectin_ug_g":    reading.calprotectin_ug_g,
            },
            risk_score=assessment.adjusted_score,
            risk_level=assessment.risk_level,
            trajectory=assessment.trajectory,
            confounded_by=assessment.confounded_by,
            rag_context=rag_context,
        )

        # Step 4: persist narrative to SQLite
        assessment.patient_explanation = result["patient_explanation"]
        assessment.physician_summary = result["physician_summary"]
        assessment.next_steps = result["next_steps"]
        assessment.urgency_flag = result["urgency_flag"]
        db.commit()

        # Step 5: store this observation in IRIS so it joins the RAG pool
        outcome_text = result.get("physician_summary", "")
        try:
            iris_native.store_observation(
                patient_id=str(patient.id),
                patient_name=patient.name,
                risk_level=assessment.risk_level,
                risk_score=assessment.adjusted_score,
                trajectory=assessment.trajectory,
                clinical_text=clinical_text,
                outcome_text=outcome_text,
            )
        except Exception as e:
            print(f"[ingest] IRIS store failed (non-fatal): {e}")

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

    # NN scoring: fetch similar patients' risk scores as RAG features (fast SQLite kNN)
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
    rag_scores = _get_similar_scores(db, patient.id, reading_dict)

    raw_score, adjusted_score, risk_level, confounded_by, score_breakdown = compute_risk_score(
        reading=reading_dict,
        patient_age=patient.age,
        patient_family_history=patient.family_history,
        recent_antibiotic_use=recent_antibiotics,
        high_fiber=high_fiber,
        rag_scores=rag_scores,
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
