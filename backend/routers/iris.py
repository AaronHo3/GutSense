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
                                       in {"2335-8", "35548-6", "94558-4"},
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


@router.post("/api/iris/refresh")
def refresh_iris_cache():
    """Clear all caches and force re-seed on next request."""
    global _fhir_seeded
    iris_native.clear_cache()
    iris_langchain.clear()
    _fhir_seeded = False
    return {"message": "All IRIS caches cleared. Next request will re-seed."}
