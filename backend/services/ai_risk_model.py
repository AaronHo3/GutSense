"""
Two-layer risk model:

Layer 1 — Deterministic scoring (synchronous).
  Maps each biomarker to 0-100 via sigmoid/linear curves, applies weights,
  then adjusts for patient demographics and lifestyle metadata.

Layer 2 — Claude narrative (async, result stored on the RiskAssessment).
  Called after the reading is persisted; updates the record with explanations.

Biomarkers (8):
  mpo_ng_ml            — Myeloperoxidase; oxidative stress / neutrophil activity
  haptoglobin_ug_g     — Haptoglobin (fecal); acute-phase protein, binds free Hb
  fibrinogen_ng_ml     — Fibrinogen (fecal); coagulation / inflammation marker
  mmp9_ng_ml           — MMP-9; matrix metalloproteinase, ECM degradation in CRC
  hemoglobin_fit_ng_ml — Haemoglobin FIT; occult blood, most validated CRC screen
  mmp8_ng_ml           — MMP-8; neutrophil collagenase, elevated in CRC
  pgrp_s_ng_ml         — PGRP-S; innate immunity peptidoglycan recognition protein
  calprotectin_ug_g    — Calprotectin; gold-standard mucosal inflammation marker
"""

import math
from typing import Optional


# ── Helper curves ──────────────────────────────────────────────────────────────

def _sigmoid(x: float, midpoint: float, steepness: float) -> float:
    """Maps x -> [0, 100] with inflection at midpoint."""
    return 100.0 / (1.0 + math.exp(-steepness * (x - midpoint)))


def _linear_clamp(x: float, low: float, high: float) -> float:
    """Maps x linearly from low->0 to high->100, clamped."""
    if x <= low:
        return 0.0
    if x >= high:
        return 100.0
    return (x - low) / (high - low) * 100.0


# ── Per-biomarker component scores ────────────────────────────────────────────

def _score_mpo(val: float) -> float:
    # normal <100 ng/mL, alarm >500 ng/mL
    return _sigmoid(val, midpoint=280.0, steepness=0.012)


def _score_haptoglobin(val: float) -> float:
    # normal <50 µg/g, alarm >200 µg/g
    return _sigmoid(val, midpoint=110.0, steepness=0.030)


def _score_fibrinogen(val: float) -> float:
    # normal <100 ng/mL, alarm >400 ng/mL
    return _sigmoid(val, midpoint=230.0, steepness=0.012)


def _score_mmp9(val: float) -> float:
    # normal <30 ng/mL, alarm >150 ng/mL
    return _sigmoid(val, midpoint=80.0, steepness=0.040)


def _score_hemoglobin_fit(val: float) -> float:
    # normal <10 ng/mL, alarm >100 ng/mL
    return _sigmoid(val, midpoint=50.0, steepness=0.040)


def _score_mmp8(val: float) -> float:
    # normal <30 ng/mL, alarm >150 ng/mL
    return _sigmoid(val, midpoint=80.0, steepness=0.040)


def _score_pgrp_s(val: float) -> float:
    # normal <20 ng/mL, alarm >100 ng/mL
    return _sigmoid(val, midpoint=55.0, steepness=0.060)


def _score_calprotectin(val: float) -> float:
    # normal <50 µg/g, alarm >200 µg/g
    return _sigmoid(val, midpoint=120.0, steepness=0.025)


# ── Weights ────────────────────────────────────────────────────────────────────
# Total = 1.00
# hemoglobin_fit: most validated non-invasive CRC screening marker (FIT)
# calprotectin:   gold-standard mucosal inflammation
# mmp9/mpo:       matrix degradation + oxidative burst strongly linked to CRC
# mmp8:           neutrophil collagenase, elevated pre-malignant lesions
# fibrinogen:     acute-phase elevation in CRC
# haptoglobin:    binds free Hb; elevated in GI bleeding
# pgrp_s:         innate immunity; less directly validated

WEIGHTS = {
    "hemoglobin_fit": 0.25,
    "calprotectin":   0.20,
    "mmp9":           0.15,
    "mpo":            0.15,
    "mmp8":           0.10,
    "fibrinogen":     0.08,
    "haptoglobin":    0.05,
    "pgrp_s":         0.02,
}


# ── Main scoring function ──────────────────────────────────────────────────────

def compute_risk_score(
    reading: dict,
    patient_age: int,
    patient_family_history: bool,
    recent_antibiotic_use: bool = False,
    high_fiber: bool = False,
    trend_rising: bool = False,
    rag_scores: list = None,
) -> tuple[float, float, str, Optional[str], dict]:
    """
    Returns (raw_score, adjusted_score, risk_level, confounded_by, score_breakdown).

    Layer 1 — sigmoid curves convert raw biomarker values to 0-100 component scores.
    Layer 2 — small neural network (nn_risk_model) combines component scores,
               patient features, and RAG scores (top-k similar historical patients
               from SQLite kNN) into a final 0-100 risk score.

    rag_scores: list of 0-3 floats — risk scores of the most similar historical
                patients, retrieved via fast SQLite distance lookup in ingest.py.
                If empty or unavailable, the NN uses a neutral default (50.0).
    """
    from services import nn_risk_model

    # Feature engineering: sigmoid curves normalise raw values to 0-100
    component_scores = {
        "hemoglobin_fit": _score_hemoglobin_fit(reading["hemoglobin_fit_ng_ml"]),
        "calprotectin":   _score_calprotectin(reading["calprotectin_ug_g"]),
        "mmp9":           _score_mmp9(reading["mmp9_ng_ml"]),
        "mpo":            _score_mpo(reading["mpo_ng_ml"]),
        "mmp8":           _score_mmp8(reading["mmp8_ng_ml"]),
        "fibrinogen":     _score_fibrinogen(reading["fibrinogen_ng_ml"]),
        "haptoglobin":    _score_haptoglobin(reading["haptoglobin_ug_g"]),
        "pgrp_s":         _score_pgrp_s(reading["pgrp_s_ng_ml"]),
    }

    # Weighted sum kept as raw_score for display/breakdown reference
    raw_score = sum(component_scores[k] * w for k, w in WEIGHTS.items())
    raw_score = max(0.0, min(100.0, raw_score))

    # NN produces the actual adjusted score, incorporating RAG context
    adjusted = nn_risk_model.predict(
        component_scores=component_scores,
        patient_age=patient_age,
        family_history=patient_family_history,
        rag_scores=rag_scores or [],
    )

    # Lifestyle adjustments applied after NN (interpretable overrides)
    confounded_by = None
    if recent_antibiotic_use:
        adjusted = max(0.0, adjusted - 10)
        confounded_by = (
            "Recent antibiotic use may be causing transient mucosal disruption — "
            "inflammatory markers may not reflect underlying disease state."
        )
    if high_fiber:
        adjusted = max(0.0, adjusted - 3)

    adjusted = max(0.0, min(100.0, adjusted))

    if adjusted <= 30:
        risk_level = "green"
    elif adjusted <= 60:
        risk_level = "yellow"
    elif adjusted <= 80:
        risk_level = "orange"
    else:
        risk_level = "red"

    return raw_score, adjusted, risk_level, confounded_by, component_scores


def urgency_from_level(risk_level: str) -> str:
    return {"green": "routine", "yellow": "elevated", "orange": "urgent", "red": "urgent"}[risk_level]
