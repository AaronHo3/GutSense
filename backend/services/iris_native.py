"""
IRIS native Python client — uses sqlalchemy-iris on port 1972.

Architecture:
  1. On first call, creates SQLUser.GutSensePatients table in IRIS USER namespace
  2. Seeds it from the GutSense SQLite database (patients + risk assessments)
  3. Generates OpenAI text-embedding-3-small vectors for each patient summary
  4. Stores vectors in an IRIS VECTOR(DOUBLE, 1536) column
  5. Exposes vector-similarity search for "find similar patients"

Requires: pip install sqlalchemy-iris
"""

import json
import logging
import os
import sqlite3
import threading
import time
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
IRIS_HOST      = os.getenv("IRIS_HOST",      "localhost")
IRIS_PORT      = int(os.getenv("IRIS_PORT",  "1972"))
IRIS_NAMESPACE = os.getenv("IRIS_NAMESPACE", "USER")
IRIS_USER_ENV  = os.getenv("IRIS_USER",      "demo")
IRIS_PASS      = os.getenv("IRIS_PASS",      "demo")

TABLE      = "SQLUser.GutSensePatients"
VECTOR_DIM = 1536   # OpenAI text-embedding-3-small

_CACHE_TTL = 300    # 5 minutes

# ---------------------------------------------------------------------------
# Module state
# ---------------------------------------------------------------------------
_engine                        = None
_vector_supported: Optional[bool] = None
_seeded                        = False
_cache: dict                   = {}
_seed_lock                     = threading.Lock()


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

def _get_engine():
    global _engine
    if _engine is not None:
        return _engine
    try:
        url = f"iris://{IRIS_USER_ENV}:{IRIS_PASS}@{IRIS_HOST}:{IRIS_PORT}/{IRIS_NAMESPACE}"
        _engine = create_engine(url, echo=False)
        # Verify connectivity
        with _engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info(f"[IRIS] Connected {IRIS_HOST}:{IRIS_PORT}/{IRIS_NAMESPACE}")
        return _engine
    except Exception as e:
        _engine = None
        raise RuntimeError(f"IRIS connection failed: {e}")


def is_connected() -> bool:
    try:
        _get_engine()
        return True
    except Exception:
        return False


def clear_cache():
    global _engine, _seeded, _vector_supported
    _cache.clear()
    _engine = None
    _seeded = False
    _vector_supported = None  # Bug #4: was not reset, caused stale vector-support state


# ---------------------------------------------------------------------------
# Vector support probe
# ---------------------------------------------------------------------------

def _has_vector() -> bool:
    global _vector_supported
    if _vector_supported is not None:
        return _vector_supported
    try:
        with _get_engine().connect() as conn:
            conn.execute(text("SELECT TO_VECTOR('0.1,0.2,0.3', DOUBLE)"))
        _vector_supported = True
    except Exception:
        _vector_supported = False
    return _vector_supported


# ---------------------------------------------------------------------------
# Table management
# ---------------------------------------------------------------------------

def _table_exists() -> bool:
    try:
        with _get_engine().connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*)
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = 'SQLUser'
                  AND TABLE_NAME   = 'GutSensePatients'
            """))
            return result.fetchone()[0] > 0
    except Exception:
        return False


def _create_table():
    vector_col = (
        f", SummaryVector VECTOR(DOUBLE, {VECTOR_DIM})"
        if _has_vector() else ""
    )
    ddl = f"""
        CREATE TABLE {TABLE} (
            PatientId    VARCHAR(50),
            Name         VARCHAR(100),
            Age          INTEGER,
            Gender       VARCHAR(20),
            RiskScore    FLOAT,
            RiskLevel    VARCHAR(20),
            Summary      VARCHAR(4000),
            KeyFindings  VARCHAR(2000),
            Recommendation VARCHAR(500),
            BiomarkerText VARCHAR(2000)
            {vector_col}
        )
    """
    with _get_engine().connect() as conn:
        conn.execute(text(ddl))
        conn.commit()
    logger.info(f"[IRIS] Created {TABLE} (vectors={'yes' if _has_vector() else 'no'})")


def _row_count() -> int:
    try:
        with _get_engine().connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {TABLE}"))
            return result.fetchone()[0]
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# OpenAI embedding
# ---------------------------------------------------------------------------

def _embed(text_str: str) -> Optional[list]:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        resp = client.embeddings.create(
            model="text-embedding-3-small",
            input=text_str[:8000],
        )
        return resp.data[0].embedding
    except Exception as e:
        logger.warning(f"[IRIS] Embedding failed: {e}")
        return None


def _vec_to_str(vec: list) -> str:
    """Convert float list to comma-separated string for TO_VECTOR()."""
    return ",".join(str(v) for v in vec)


# ---------------------------------------------------------------------------
# Seed from GutSense SQLite
# ---------------------------------------------------------------------------

def _sqlite_path() -> str:
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(here, "biomarker.db")


def _load_from_sqlite() -> list:
    db_path = _sqlite_path()
    if not os.path.exists(db_path):
        logger.warning(f"[IRIS] SQLite DB not found at {db_path}")
        return []

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    cur.execute("""
        SELECT
            p.id, p.name, p.age, p.sex, p.family_history,
            ra.adjusted_score, ra.risk_level, ra.trajectory,
            ra.patient_explanation, ra.physician_summary,
            ra.next_steps, ra.confounded_by,
            br.hemoglobin_ng_ml, br.butyrate_mmol_kg,
            br.calprotectin_ug_g, br.basidio_ascomy_ratio,
            br.proteobacteria_index, br.methylation_score
        FROM patients p
        LEFT JOIN risk_assessments ra ON ra.patient_id = p.id
            AND ra.id = (
                SELECT id FROM risk_assessments
                WHERE patient_id = p.id
                ORDER BY timestamp DESC LIMIT 1
            )
        LEFT JOIN biomarker_readings br ON br.id = ra.reading_id
        ORDER BY p.id
    """)
    rows = cur.fetchall()
    con.close()

    result = []
    for r in rows:
        next_steps = []
        if r["next_steps"]:
            try:
                next_steps = json.loads(r["next_steps"])
            except Exception:
                next_steps = [r["next_steps"]]

        biomarker_text = (
            f"Hemoglobin {r['hemoglobin_ng_ml']:.1f}ng/mL, "
            f"Butyrate {r['butyrate_mmol_kg']:.2f}mmol/kg, "
            f"Calprotectin {r['calprotectin_ug_g']:.0f}μg/g, "
            f"Fungal ratio {r['basidio_ascomy_ratio']:.2f}, "
            f"Proteobacteria {r['proteobacteria_index']:.3f}, "
            f"Methylation {r['methylation_score']:.3f}"
        ) if r["hemoglobin_ng_ml"] is not None else "No biomarker data"

        key_findings = next_steps[:4] if next_steps else ["No significant findings"]
        summary = (
            r["patient_explanation"]
            or r["physician_summary"]
            or f"Risk level {r['risk_level']}, score {r['adjusted_score']}/100."
        )
        recommendation = next_steps[0] if next_steps else "Continue routine screening."

        embed_text = (
            f"Patient {r['name']}, age {r['age']}, {r['sex']}. "
            f"Family history: {'yes' if r['family_history'] else 'no'}. "
            f"Risk: {r['risk_level']} ({r['adjusted_score']}/100), "
            f"trajectory: {r['trajectory']}. "
            f"Biomarkers: {biomarker_text}. "
            f"Assessment: {summary}"
        )

        result.append({
            "patient_id":     str(r["id"]),
            "name":           r["name"],
            "age":            r["age"],
            "gender":         r["sex"],
            "risk_score":     float(r["adjusted_score"] or 0),
            "risk_level":     _map_risk_level(r["risk_level"]),
            "summary":        summary[:4000],
            "key_findings":   json.dumps(key_findings),
            "recommendation": recommendation[:500],
            "biomarker_text": biomarker_text[:2000],
            "embed_text":     embed_text,
        })

    return result


def _map_risk_level(level: Optional[str]) -> str:
    mapping = {"green": "low", "yellow": "medium", "orange": "high", "red": "high"}
    return mapping.get(level or "green", "low")


# ---------------------------------------------------------------------------
# Seed IRIS table
# ---------------------------------------------------------------------------

def _seed():
    """Thread-safe seed: only one thread seeds; others wait and return."""
    with _seed_lock:  # Bug #2 fix: prevents concurrent duplicate seeding
        global _seeded
        if _seeded:
            return

        if not _table_exists():
            _create_table()

        if _row_count() > 0:
            _seeded = True
            return

        patients = _load_from_sqlite()
        if not patients:
            logger.warning("[IRIS] No patients to seed")
            _seeded = True
            return

        use_vec = _has_vector()
        engine = _get_engine()

        for p in patients:
            vec = _embed(p["embed_text"]) if use_vec else None

            with engine.connect() as conn:
                if use_vec and vec:
                    conn.execute(text(f"""
                        INSERT INTO {TABLE}
                          (PatientId, Name, Age, Gender, RiskScore, RiskLevel,
                           Summary, KeyFindings, Recommendation, BiomarkerText,
                           SummaryVector)
                        VALUES (:pid, :name, :age, :gender, :rscore, :rlevel,
                                :summary, :kf, :rec, :bt,
                                TO_VECTOR(:vec, DOUBLE))
                    """), {
                        "pid":     p["patient_id"],
                        "name":    p["name"],
                        "age":     p["age"],
                        "gender":  p["gender"],
                        "rscore":  p["risk_score"],
                        "rlevel":  p["risk_level"],
                        "summary": p["summary"],
                        "kf":      p["key_findings"],
                        "rec":     p["recommendation"],
                        "bt":      p["biomarker_text"],
                        "vec":     _vec_to_str(vec),
                    })
                else:
                    conn.execute(text(f"""
                        INSERT INTO {TABLE}
                          (PatientId, Name, Age, Gender, RiskScore, RiskLevel,
                           Summary, KeyFindings, Recommendation, BiomarkerText)
                        VALUES (:pid, :name, :age, :gender, :rscore, :rlevel,
                                :summary, :kf, :rec, :bt)
                    """), {
                        "pid":     p["patient_id"],
                        "name":    p["name"],
                        "age":     p["age"],
                        "gender":  p["gender"],
                        "rscore":  p["risk_score"],
                        "rlevel":  p["risk_level"],
                        "summary": p["summary"],
                        "kf":      p["key_findings"],
                        "rec":     p["recommendation"],
                        "bt":      p["biomarker_text"],
                    })
                conn.commit()

            logger.info(
                f"[IRIS] Seeded {p['name']} "
                f"(risk={p['risk_level']}, vec={'yes' if vec else 'no'})"
            )

        _seeded = True
        logger.info(f"[IRIS] Seeded {len(patients)} patients into {TABLE}")


# ---------------------------------------------------------------------------
# Public query API
# ---------------------------------------------------------------------------

def get_patients() -> list:
    """Return all patients from IRIS, ordered by risk score descending."""
    key = "patients"
    cached = _cache.get(key)
    if cached and time.time() - cached["ts"] < _CACHE_TTL:
        return cached["data"]

    _seed()
    with _get_engine().connect() as conn:
        result = conn.execute(text(f"""
            SELECT PatientId, Name, Age, Gender, RiskScore, RiskLevel,
                   Summary, KeyFindings, Recommendation, BiomarkerText
            FROM {TABLE}
            ORDER BY RiskScore DESC
        """))
        rows = result.fetchall()

    data = [_row_to_dict(r) for r in rows]
    _cache[key] = {"data": data, "ts": time.time()}
    return data


def get_patient(patient_id: str) -> Optional[dict]:
    """Return a single patient by PatientId."""
    _seed()
    with _get_engine().connect() as conn:
        result = conn.execute(text(f"""
            SELECT PatientId, Name, Age, Gender, RiskScore, RiskLevel,
                   Summary, KeyFindings, Recommendation, BiomarkerText
            FROM {TABLE}
            WHERE PatientId = :pid
        """), {"pid": patient_id})
        row = result.fetchone()
    return _row_to_dict(row) if row else None


def find_similar(patient_id: str, top_k: int = 3) -> list:
    """
    Return the top_k most similar patients using IRIS Vector Search.
    Falls back to empty list if vectors aren't available.
    """
    if not _has_vector():
        return []

    _seed()
    with _get_engine().connect() as conn:
        # Get query patient's vector as string
        vec_result = conn.execute(text(
            f"SELECT CAST(SummaryVector AS VARCHAR(65000)) FROM {TABLE} WHERE PatientId = :pid"
        ), {"pid": patient_id})
        vec_row = vec_result.fetchone()
        if not vec_row or vec_row[0] is None:
            return []

        query_vec_str = str(vec_row[0])

        # Bug #5 fix: IRIS TOP clause doesn't accept bound params — use literal
        sim_result = conn.execute(text(f"""
            SELECT TOP {int(top_k)} PatientId, Name, Age, Gender, RiskScore, RiskLevel,
                   Summary, KeyFindings, Recommendation, BiomarkerText,
                   VECTOR_COSINE(SummaryVector, TO_VECTOR(:vec, DOUBLE)) AS Similarity
            FROM {TABLE}
            WHERE PatientId <> :pid
            ORDER BY Similarity DESC
        """), {"vec": query_vec_str, "pid": patient_id})
        rows = sim_result.fetchall()

    result = []
    for r in rows:
        d = _row_to_dict(r[:10])
        d["similarity"] = float(r[10]) if r[10] is not None else 0.0
        result.append(d)
    return result


def _row_to_dict(row) -> dict:
    # Bug #6 fix: guard against schema mismatch returning fewer columns
    if not row or len(row) < 10:
        return {}
    patient_id, name, age, gender, risk_score, risk_level, \
        summary, key_findings, recommendation, biomarker_text = row[:10]

    findings: list = []
    if key_findings:
        try:
            findings = json.loads(key_findings)
        except Exception:
            findings = [key_findings]

    return {
        "fhir_id":                  patient_id or "unknown",
        "name":                     name or "Unknown",
        "age":                      int(age) if age is not None else 0,  # Bug #8 fix: ensure int
        "gender":                   gender or "unknown",
        "risk_score":               round(float(risk_score or 0)),
        "risk_level":               risk_level or "low",
        "summary":                  summary or "",
        "key_findings":             findings,
        "recommendation":           recommendation or "",
        "risk_factors":             findings[:3],
        "diagnostic_reports_count": 1,
        "observations_count":       6,
        "biomarker_text":           biomarker_text or "",
    }
