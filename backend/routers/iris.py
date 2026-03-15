"""
IRIS router — three InterSystems features working together:

  1. IRIS Native Python (port 1972)
       Patient biomarker data stored in SQLUser.GutSensePatients
       with a VECTOR(DOUBLE, 1536) column for cosine similarity.

  2. FHIR R4 resources
       Every patient's data is modelled as a standards-compliant FHIR Bundle
       (Patient + 6 Observations + DiagnosticReport + RiskAssessment).
       Downloadable at GET /api/iris/patients/{id}/fhir

  3. LangChain + IRIS Vector Search RAG
       FHIR bundle text is embedded (OpenAI text-embedding-3-small) and stored
       in IRIS via LangChain's IRISVector store.  On patient lookup, similar
       FHIR cases are retrieved and fed to GPT-4o-mini as RAG context to produce
       a richer clinical narrative than the rule-based fallback.

Endpoints:
  GET  /api/iris/status                — connection + feature health check
  GET  /api/iris/patients              — all patients ranked by risk
  GET  /api/iris/patients/{id}         — detail: RAG summary + similar FHIR cases
  GET  /api/iris/patients/{id}/fhir    — full FHIR R4 Bundle (JSON)
  POST /api/iris/refresh               — clear all caches / re-seed on next request
"""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from services import iris_native, iris_langchain, fhir_generator

logger = logging.getLogger(__name__)
router = APIRouter(tags=["iris"])


# ---------------------------------------------------------------------------
# Startup seeding helper (called lazily on first patient list request)
# ---------------------------------------------------------------------------

_fhir_seeded = False


def _seed_langchain():
    """Build FHIR texts for all patients and seed IRIS Vector Search via LangChain."""
    global _fhir_seeded
    if _fhir_seeded or not iris_langchain.is_available():
        _fhir_seeded = True
        return

    try:
        patients = iris_native.get_patients()
        docs = []
        for p in patients:
            try:
                pid = int(p["fhir_id"])
            except (ValueError, TypeError):
                continue  # Bug #9 fix: skip non-integer fhir_ids gracefully
            bundle = fhir_generator.generate_fhir_bundle(pid)
            if bundle:
                fhir_text = fhir_generator.bundle_to_text(bundle)
                docs.append({
                    "patient_id":  p["fhir_id"],
                    "name":        p["name"],
                    "risk_level":  p["risk_level"],
                    "risk_score":  p["risk_score"],
                    "fhir_text":   fhir_text,
                })

        added = iris_langchain.seed_fhir_documents(docs)
        logger.info(f"[IRIS router] LangChain seed: {added} new documents")
    except Exception as e:
        logger.warning(f"[IRIS router] LangChain seed failed: {e}")
    finally:
        _fhir_seeded = True


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/api/iris/status")
def iris_status():
    """Health check: IRIS connection, Vector Search, LangChain RAG, FHIR."""
    connected = iris_native.is_connected()
    vec = iris_native._has_vector() if connected else False
    lc = iris_langchain.is_available()
    return {
        "connected":      connected,
        "fhir_base":      None,
        "vector_search":  vec,
        "langchain_rag":  lc,
        "iris_host":      f"{iris_native.IRIS_HOST}:{iris_native.IRIS_PORT}",
        "message": (
            f"IRIS {iris_native.IRIS_HOST}:{iris_native.IRIS_PORT} connected — "
            f"Vector Search {'✓' if vec else '✗'}  "
            f"LangChain RAG {'✓' if lc else '✗ (add OPENAI_API_KEY)'}"
            if connected
            else (
                f"Cannot connect to IRIS on "
                f"{iris_native.IRIS_HOST}:{iris_native.IRIS_PORT}. "
                "Ensure the Docker container is running and port 1972 is exposed."
            )
        ),
    }


@router.get("/api/iris/patients")
def get_iris_patients():
    """
    All patients from IRIS Native, ranked by risk score.
    Triggers LangChain seeding of FHIR documents in the background.
    """
    if not iris_native.is_connected():
        raise HTTPException(
            status_code=503,
            detail=(
                f"Cannot connect to IRIS on "
                f"{iris_native.IRIS_HOST}:{iris_native.IRIS_PORT}. "
                "Ensure the Docker container is running and port 1972 is exposed."
            ),
        )

    try:
        patients = iris_native.get_patients()
    except Exception as e:
        logger.error(f"[IRIS] get_patients failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    # Seed LangChain vector store (best-effort, runs in background thread to avoid blocking)
    import threading
    threading.Thread(target=_seed_langchain, daemon=True).start()

    return {"patients": patients, "total": len(patients)}


@router.get("/api/iris/patients/{patient_id}")
def get_iris_patient(patient_id: str):
    """
    Single patient detail with:
      - IRIS Vector Search similar cases (native cosine similarity)
      - LangChain RAG clinical narrative (if OpenAI key is configured)
      - FHIR R4 observation rows parsed from the bundle
    """
    if not iris_native.is_connected():
        raise HTTPException(status_code=503, detail="IRIS not reachable.")

    patient = iris_native.get_patient(patient_id)
    if not patient:
        raise HTTPException(
            status_code=404, detail=f"Patient '{patient_id}' not found in IRIS."
        )

    # ── FHIR Bundle ──────────────────────────────────────────────────────────
    try:
        bundle = fhir_generator.generate_fhir_bundle(int(patient_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="patient_id must be an integer")  # Bug #1 fix
    fhir_text = fhir_generator.bundle_to_text(bundle) if bundle else ""

    # ── LangChain RAG ────────────────────────────────────────────────────────
    rag_result = None
    if fhir_text and iris_langchain.is_available():
        rag_result = iris_langchain.generate_rag_summary(
            patient_name=patient["name"],
            patient_fhir_text=fhir_text,
            risk_level=patient["risk_level"],
            risk_score=patient["risk_score"],
            patient_id=patient_id,  # Bug #3 fix: pass ID for accurate self-exclusion
        )

    # ── IRIS native vector similarity (fallback similar cases) ───────────────
    native_similar = []
    if not (rag_result and rag_result.get("similar_cases")):
        try:
            native_similar = iris_native.find_similar(patient_id, top_k=3)
        except Exception as e:
            logger.warning(f"[IRIS] Native vector search failed: {e}")

    similar_cases = (rag_result or {}).get("similar_cases") or [
        {
            "patient_name": s["name"],
            "risk_level":   s["risk_level"],
            "risk_score":   s["risk_score"],
            "similarity":   s.get("similarity", 0.0),
            "summary":      s.get("summary", ""),
        }
        for s in native_similar
    ]

    # ── Observations from FHIR Bundle ────────────────────────────────────────
    obs_summaries = []
    report_summaries = []
    if bundle:
        for entry in bundle.get("entry", []):
            r = entry["resource"]
            rt = r.get("resourceType")
            if rt == "Observation":
                vq = r.get("valueQuantity", {})
                interps = r.get("interpretation", [])
                interp_code = None
                if interps:
                    coding = interps[0].get("coding", [{}])
                    interp_code = coding[0].get("code") if coding else None
                obs_summaries.append({
                    "loinc":           r.get("code", {}).get("coding", [{}])[0].get("code"),
                    "display":         r.get("code", {}).get("text", ""),
                    "value":           str(vq.get("value", "")),
                    "unit":            vq.get("unit"),
                    "interpretation":  interp_code,
                    "status":          r.get("status", "final"),
                    "date":            (r.get("effectiveDateTime") or "")[:10] or None,
                    "is_stool_related": True,
                    "is_high_weight":  r.get("code", {}).get("coding", [{}])[0].get("code")
                                       in {"2335-8", "35548-6", "72289-1"},  # Hgb-FIT, Calprotectin, MMP-9
                })
            elif rt == "DiagnosticReport":
                report_summaries.append({
                    "id":         r.get("id"),
                    "status":     r.get("status"),
                    "code":       r.get("code", {}).get("text", "Diagnostic Report"),
                    "date":       (r.get("effectiveDateTime") or "")[:10] or None,
                    "conclusion": r.get("conclusion"),
                })

    return {
        **patient,
        "rag_summary":    (rag_result or {}).get("summary"),
        "rag_powered_by": (rag_result or {}).get("powered_by"),
        "similar_cases":  similar_cases,
        "fhir_bundle_id": bundle.get("id") if bundle else None,
        "observations":   obs_summaries,
        "reports":        report_summaries,
    }


@router.get("/api/iris/patients/{patient_id}/fhir")
def get_fhir_bundle(patient_id: str):
    """Download the full FHIR R4 Bundle for a patient as JSON."""
    try:
        pid = int(patient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="patient_id must be an integer")

    bundle = fhir_generator.generate_fhir_bundle(pid)
    if not bundle:
        raise HTTPException(status_code=404, detail=f"No FHIR data for patient {patient_id}")

    return JSONResponse(
        content=bundle,
        headers={"Content-Disposition": f'attachment; filename="fhir-bundle-{patient_id}.json"'},
    )


@router.get("/api/iris/analytics")
def get_iris_analytics():
    """
    InterSystems Analytics — population-level insights powered by IRIS SQL.

    All aggregations run directly against the SQLUser.GutSensePatients table
    in IRIS (same engine as the native patient store) plus time-series data
    from the GutSense SQLite database for 90-day biomarker trends.
    """
    if not iris_native.is_connected():
        raise HTTPException(status_code=503, detail="IRIS not reachable.")

    from sqlalchemy import text as _text
    import sqlite3 as _sqlite3
    import os as _os

    engine = iris_native._get_engine()

    # ── 1. KPIs from IRIS SQL ─────────────────────────────────────────────────
    with engine.connect() as conn:
        kpi_row = conn.execute(_text(f"""
            SELECT
                COUNT(*)                          AS total_patients,
                SUM(CASE WHEN RiskLevel = 'high'   THEN 1 ELSE 0 END) AS high_risk,
                SUM(CASE WHEN RiskLevel = 'medium' THEN 1 ELSE 0 END) AS medium_risk,
                SUM(CASE WHEN RiskLevel = 'low'    THEN 1 ELSE 0 END) AS low_risk,
                AVG(RiskScore)                    AS avg_score,
                MAX(RiskScore)                    AS max_score,
                MIN(RiskScore)                    AS min_score
            FROM {iris_native.TABLE}
        """)).fetchone()

        dist_rows = conn.execute(_text(f"""
            SELECT RiskLevel, COUNT(*) AS cnt, AVG(RiskScore) AS avg_score
            FROM {iris_native.TABLE}
            GROUP BY RiskLevel
            ORDER BY avg_score DESC
        """)).fetchall()

        patient_rows = conn.execute(_text(f"""
            SELECT PatientId, Name, Gender, RiskScore, RiskLevel, Recommendation
            FROM {iris_native.TABLE}
            ORDER BY RiskScore DESC
        """)).fetchall()

    kpi = {
        "total_patients": int(kpi_row[0] or 0),
        "high_risk":      int(kpi_row[1] or 0),
        "medium_risk":    int(kpi_row[2] or 0),
        "low_risk":       int(kpi_row[3] or 0),
        "avg_score":      round(float(kpi_row[4] or 0), 1),
        "max_score":      round(float(kpi_row[5] or 0), 1),
        "min_score":      round(float(kpi_row[6] or 0), 1),
    }

    risk_distribution = [
        {
            "level":     row[0] or "unknown",
            "count":     int(row[1]),
            "avg_score": round(float(row[2] or 0), 1),
            "pct":       round(int(row[1]) / max(kpi["total_patients"], 1) * 100, 1),
        }
        for row in dist_rows
    ]

    cohort = [
        {
            "id":             row[0],
            "name":           row[1],
            "gender":         row[2],
            "risk_score":     round(float(row[3] or 0)),
            "risk_level":     row[4] or "low",
            "recommendation": row[5] or "",
        }
        for row in patient_rows
    ]

    # ── 2. Time-series from SQLite ────────────────────────────────────────────
    here = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    db_path = _os.path.join(here, "biomarker.db")

    biomarker_trends = []
    risk_trend       = []
    trajectory_dist  = []
    score_breakdown  = []

    if _os.path.exists(db_path):
        con = _sqlite3.connect(db_path)
        con.row_factory = _sqlite3.Row
        cur = con.cursor()

        # 30-day rolling average biomarkers across all patients
        cur.execute("""
            SELECT
                date(timestamp)           AS day,
                AVG(hemoglobin_fit_ng_ml) AS hgb_fit,
                AVG(calprotectin_ug_g)    AS calprotectin,
                AVG(mmp9_ng_ml)           AS mmp9,
                AVG(mpo_ng_ml)            AS mpo,
                AVG(mmp8_ng_ml)           AS mmp8,
                AVG(fibrinogen_ng_ml)     AS fibrinogen,
                AVG(haptoglobin_ug_g)     AS haptoglobin,
                AVG(pgrp_s_ng_ml)         AS pgrp_s
            FROM biomarker_readings
            WHERE timestamp >= datetime('now', '-30 days')
            GROUP BY day
            ORDER BY day
        """)
        for r in cur.fetchall():
            biomarker_trends.append({
                "day":          r["day"],
                "hgb_fit":      round(float(r["hgb_fit"] or 0), 1),
                "calprotectin": round(float(r["calprotectin"] or 0), 1),
                "mmp9":         round(float(r["mmp9"] or 0), 1),
                "mpo":          round(float(r["mpo"] or 0), 1),
                "mmp8":         round(float(r["mmp8"] or 0), 1),
                "fibrinogen":   round(float(r["fibrinogen"] or 0), 1),
                "haptoglobin":  round(float(r["haptoglobin"] or 0), 1),
                "pgrp_s":       round(float(r["pgrp_s"] or 0), 1),
            })

        # Risk score trend — weekly averages
        cur.execute("""
            SELECT
                strftime('%Y-W%W', timestamp) AS week,
                AVG(adjusted_score)           AS avg_score,
                COUNT(*)                      AS readings
            FROM risk_assessments
            WHERE timestamp >= datetime('now', '-90 days')
            GROUP BY week
            ORDER BY week
        """)
        for r in cur.fetchall():
            risk_trend.append({
                "week":      r["week"],
                "avg_score": round(float(r["avg_score"] or 0), 1),
                "readings":  int(r["readings"]),
            })

        # Trajectory breakdown
        cur.execute("""
            SELECT trajectory, COUNT(*) AS cnt
            FROM (
                SELECT patient_id, trajectory
                FROM risk_assessments
                GROUP BY patient_id
                HAVING id = MAX(id)
            )
            GROUP BY trajectory
        """)
        for r in cur.fetchall():
            trajectory_dist.append({"trajectory": r["trajectory"], "count": int(r["cnt"])})

        # Per-patient average score breakdown (last reading)
        cur.execute("""
            SELECT p.name, ra.score_breakdown
            FROM patients p
            JOIN risk_assessments ra ON ra.patient_id = p.id
              AND ra.id = (SELECT MAX(id) FROM risk_assessments WHERE patient_id = p.id)
            WHERE ra.score_breakdown IS NOT NULL
        """)
        import json as _json
        for r in cur.fetchall():
            try:
                bd = _json.loads(r["score_breakdown"])
                score_breakdown.append({"name": r["name"], **{k: round(float(v), 1) for k, v in bd.items()}})
            except Exception:
                pass

        con.close()

    # ── 3. Portal link ────────────────────────────────────────────────────────
    portal_url = (
        f"http://{iris_native.IRIS_HOST}:52773"
        "/csp/sys/%25CSP.Portal.Home.zen"
    )

    return {
        "kpis":              kpi,
        "risk_distribution": risk_distribution,
        "cohort":            cohort,
        "biomarker_trends":  biomarker_trends,
        "risk_trend":        risk_trend,
        "trajectory_dist":   trajectory_dist,
        "score_breakdown":   score_breakdown,
        "iris_portal_url":   portal_url,
        "data_source":       f"IRIS SQL — {iris_native.IRIS_HOST}:{iris_native.IRIS_PORT}/{iris_native.IRIS_NAMESPACE}",
    }


@router.post("/api/iris/refresh")
def refresh_iris_cache():
    """Clear all caches and force re-seed on next request."""
    global _fhir_seeded
    iris_native.clear_cache()
    iris_langchain.clear()
    _fhir_seeded = False
    return {"message": "All IRIS caches cleared. Next request will re-seed."}
