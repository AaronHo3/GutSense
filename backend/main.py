"""
FastAPI application entry point.

On startup:
1. Creates DB tables
2. Seeds 5 demo patients if none exist
3. Runs 90-day historical backfill if no readings exist
"""

import os
import threading
from dotenv import load_dotenv
load_dotenv(override=True)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db, SessionLocal
from routers import ingest, patients, readings, risk, alerts, physician, iris

app = FastAPI(title="Smart Toilet Biomarker API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(ingest.router)
app.include_router(patients.router)
app.include_router(readings.router)
app.include_router(risk.router)
app.include_router(alerts.router)
app.include_router(physician.router)
app.include_router(iris.router)


@app.get("/health")
def health():
    return {"status": "ok"}


def _seed_patients() -> dict[str, int]:
    """Seed demo patients. Returns name -> id mapping."""
    from simulator.patient_profiles import DEMO_PATIENTS
    import models

    db = SessionLocal()
    try:
        existing = db.query(models.Patient).all()
        if existing:
            return {p.name: p.id for p in existing}

        print("[startup] Seeding demo patients...")
        name_to_id = {}
        for profile in DEMO_PATIENTS:
            p = models.Patient(
                name=profile["name"],
                age=profile["age"],
                sex=profile["sex"],
                family_history=profile["family_history"],
                has_nod2_variant=profile["has_nod2_variant"],
            )
            db.add(p)
            db.commit()
            db.refresh(p)
            name_to_id[p.name] = p.id
            print(f"  + {p.name} (id={p.id})")
        return name_to_id
    finally:
        db.close()


def _run_backfill(name_to_id: dict[str, int]):
    """Check if backfill is needed, run it, then fill narratives for latest readings."""
    import models
    from simulator.sensor_simulator import backfill

    db = SessionLocal()
    try:
        count = db.query(models.BiomarkerReading).count()
        if count > 0:
            print(f"[startup] {count} readings already exist, skipping backfill.")
            _fill_narratives()
            return
    finally:
        db.close()

    print("[startup] Running 90-day backfill (this may take ~30 seconds)...")
    backfill(db_session=None, patient_id_map=name_to_id)
    _fill_narratives()


def _fill_narratives():
    """
    After backfill, generate placeholder narratives for the most recent
    risk assessment per patient (one Claude/fallback call per patient = 5 total).
    """
    import models
    from services import claude_client

    db = SessionLocal()
    try:
        patients = db.query(models.Patient).all()
        for patient in patients:
            assessment = (
                db.query(models.RiskAssessment)
                .filter(
                    models.RiskAssessment.patient_id == patient.id,
                    models.RiskAssessment.patient_explanation == None,  # noqa: E711
                )
                .order_by(models.RiskAssessment.timestamp.desc())
                .first()
            )
            if not assessment:
                continue

            reading = db.query(models.BiomarkerReading).filter(
                models.BiomarkerReading.id == assessment.reading_id
            ).first()
            if not reading:
                continue

            result = claude_client.generate_risk_narrative(
                reading_id=assessment.reading_id,
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
            print(f"[startup] Narrative filled for {patient.name} (risk_level={assessment.risk_level})")
    except Exception as e:
        print(f"[startup] _fill_narratives error: {e}")
    finally:
        db.close()


@app.on_event("startup")
def startup():
    init_db()
    name_to_id = _seed_patients()
    # Run backfill in a background thread so the server starts immediately
    threading.Thread(target=_run_backfill, args=(name_to_id,), daemon=True).start()
