"""
Statistical distributions for each biomarker per patient archetype.

Uses temporal autocorrelation so readings drift gradually (realistic).
Each call to next_reading() returns a dict of biomarker values.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Optional


# Autocorrelation coefficients per marker (higher = more persistent)
ALPHA = {
    "hemoglobin_ng_ml":     0.70,
    "butyrate_mmol_kg":     0.75,
    "calprotectin_ug_g":    0.72,
    "basidio_ascomy_ratio":  0.80,
    "proteobacteria_index": 0.78,
    "methylation_score":    0.85,
}


def _lognormal(mean_true: float, sigma: float) -> float:
    """Sample from LogNormal with given true mean and sigma."""
    mu = np.log(mean_true) - 0.5 * sigma ** 2
    return float(np.random.lognormal(mu, sigma))


def _sample_fresh(archetype: str, drift_factor: float = 0.0) -> dict:
    """
    Generate one uncorrelated biomarker sample for the given archetype.
    drift_factor in [0,1] shifts at_risk markers toward critical range.
    """
    if archetype == "healthy":
        return {
            "hemoglobin_ng_ml":     _lognormal(8 + drift_factor * 5, 0.4),
            "butyrate_mmol_kg":     float(np.random.normal(20 - drift_factor * 2, 2.5)),
            "calprotectin_ug_g":    _lognormal(28 + drift_factor * 10, 0.45),
            "basidio_ascomy_ratio":  float(np.random.gamma(shape=2.0, scale=0.5 + drift_factor * 0.1)),
            "proteobacteria_index": float(np.random.beta(1.5, 8)),
            "methylation_score":    float(np.random.beta(1.5, 8)),
        }
    elif archetype == "at_risk":
        return {
            "hemoglobin_ng_ml":     _lognormal(30 + drift_factor * 20, 0.55),
            "butyrate_mmol_kg":     float(np.random.normal(12 - drift_factor * 3, 3.0)),
            "calprotectin_ug_g":    _lognormal(80 + drift_factor * 40, 0.55),
            "basidio_ascomy_ratio":  float(np.random.gamma(shape=3.0, scale=0.7 + drift_factor * 0.15)),
            "proteobacteria_index": float(np.random.beta(3, 5)),
            "methylation_score":    float(np.random.beta(3, 6)),
        }
    else:  # critical
        return {
            "hemoglobin_ng_ml":     _lognormal(90, 0.5),
            "butyrate_mmol_kg":     max(0.5, float(np.random.normal(5, 1.5))),
            "calprotectin_ug_g":    _lognormal(250, 0.5),
            "basidio_ascomy_ratio":  float(np.random.gamma(shape=5.0, scale=0.8)),
            "proteobacteria_index": float(np.random.beta(6, 3)),
            "methylation_score":    float(np.random.beta(6, 4)),
        }


def _clamp(reading: dict) -> dict:
    """Clamp values to physiologically plausible ranges."""
    reading["hemoglobin_ng_ml"]    = max(0.1, reading["hemoglobin_ng_ml"])
    reading["butyrate_mmol_kg"]    = max(0.1, reading["butyrate_mmol_kg"])
    reading["calprotectin_ug_g"]   = max(1.0, reading["calprotectin_ug_g"])
    reading["basidio_ascomy_ratio"] = max(0.1, reading["basidio_ascomy_ratio"])
    reading["proteobacteria_index"] = min(1.0, max(0.0, reading["proteobacteria_index"]))
    reading["methylation_score"]   = min(1.0, max(0.0, reading["methylation_score"]))
    return reading


@dataclass
class BiomarkerState:
    """
    Maintains the running state for a single patient's biomarker simulation.
    Call next_reading() for each new toilet visit.
    """
    archetype: str
    enable_drift: bool = False
    _prev: Optional[dict] = field(default=None, repr=False)
    _visit_count: int = 0

    def next_reading(self) -> dict:
        self._visit_count += 1

        # Drift factor grows slowly over simulated visits (max ~0.6 after 90 days * 2 visits)
        drift_factor = min(0.6, self._visit_count / 300.0) if self.enable_drift else 0.0

        fresh = _sample_fresh(self.archetype, drift_factor)

        if self._prev is None:
            self._prev = fresh
            return _clamp(dict(fresh))

        # Apply temporal autocorrelation
        correlated = {}
        for key in fresh:
            alpha = ALPHA[key]
            correlated[key] = alpha * self._prev[key] + (1 - alpha) * fresh[key]

        self._prev = correlated
        return _clamp(dict(correlated))
