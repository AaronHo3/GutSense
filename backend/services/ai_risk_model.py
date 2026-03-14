"""
Two-layer risk model:

Layer 1 — Deterministic scoring (synchronous).
  Maps each biomarker to 0-100 via sigmoid/linear curves, applies weights,
  then adjusts for patient demographics and lifestyle metadata.

Layer 2 — Claude narrative (async, result stored on the RiskAssessment).
  Called after the reading is persisted; updates the record with explanations.
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

def _score_hemoglobin(val: float) -> float:
    # healthy <20, concerning 20-100, alarm >100
    return _sigmoid(val, midpoint=50.0, steepness=0.04)


def _score_butyrate(val: float) -> float:
    # INVERTED — depletion = risk; healthy >15, alarm <5
    # Remap: high butyrate -> low score
    inverted = max(0.0, 25.0 - val)  # 25 is rough ceiling
    return _linear_clamp(inverted, low=0.0, high=22.0)


def _score_calprotectin(val: float) -> float:
    # healthy <50, concerning 50-200, alarm >200
    return _sigmoid(val, midpoint=120.0, steepness=0.025)


def _score_basidio_ascomy(val: float) -> float:
    # healthy <1.5, concerning 1.5-3, alarm >3
    return _sigmoid(val, midpoint=2.2, steepness=1.8)


def _score_proteobacteria(val: float) -> float:
    # 0-1 index; healthy <0.2, alarm >0.5
    return _linear_clamp(val, low=0.0, high=0.8)


def _score_methylation(val: float) -> float:
    # 0-1; healthy <0.25, alarm >0.5
    return _linear_clamp(val, low=0.0, high=0.9)


# ── Weights ────────────────────────────────────────────────────────────────────

WEIGHTS = {
    "hemoglobin":     0.25,
    "methylation":    0.25,
    "calprotectin":   0.20,
    "butyrate":       0.15,
    "basidio_ascomy": 0.10,
    "proteobacteria": 0.05,
}


# ── Main scoring function ──────────────────────────────────────────────────────

def compute_risk_score(
    reading: dict,
    patient_age: int,
    patient_family_history: bool,
    recent_antibiotic_use: bool = False,
    high_fiber: bool = False,
    trend_rising: bool = False,
) -> tuple[float, float, str, Optional[str], dict]:
    """
    Returns (raw_score, adjusted_score, risk_level, confounded_by, score_breakdown).
    raw_score: weighted composite before demographic/lifestyle adjustments.
    adjusted_score: final score used for alerts and display.
    risk_level: 'green' | 'yellow' | 'orange' | 'red'
    confounded_by: plain-text note if lifestyle factors may explain readings.
    score_breakdown: dict of per-marker component scores (0-100, before weighting).
    """
    component_scores = {
        "hemoglobin":     _score_hemoglobin(reading["hemoglobin_ng_ml"]),
        "methylation":    _score_methylation(reading["methylation_score"]),
        "calprotectin":   _score_calprotectin(reading["calprotectin_ug_g"]),
        "butyrate":       _score_butyrate(reading["butyrate_mmol_kg"]),
        "basidio_ascomy": _score_basidio_ascomy(reading["basidio_ascomy_ratio"]),
        "proteobacteria": _score_proteobacteria(reading["proteobacteria_index"]),
    }

    raw_score = sum(component_scores[k] * w for k, w in WEIGHTS.items())

    # Demographic modifiers
    adjusted = raw_score
    if patient_age > 50:
        adjusted += 10
    if patient_family_history:
        adjusted += 5
    if trend_rising:
        adjusted += 5

    # Lifestyle modifiers
    confounded_by = None
    if recent_antibiotic_use:
        adjusted -= 10
        confounded_by = (
            "Recent antibiotic use may be causing transient dysbiosis — "
            "microbiome markers may not reflect underlying disease state."
        )
    if high_fiber:
        adjusted -= 3

    adjusted = max(0.0, min(100.0, adjusted))
    raw_score = max(0.0, min(100.0, raw_score))

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
