"""
Statistical distributions for each biomarker per patient archetype.

Uses temporal autocorrelation so readings drift gradually (realistic).
Each call to next_reading() returns a dict of biomarker values.

Biomarkers:
  mpo_ng_ml            — MPO;         healthy <100,   alarm >500
  haptoglobin_ug_g     — Haptoglobin; healthy <50,    alarm >200
  fibrinogen_ng_ml     — Fibrinogen;  healthy <100,   alarm >400
  mmp9_ng_ml           — MMP-9;       healthy <30,    alarm >150
  hemoglobin_fit_ng_ml — FIT Hgb;     healthy <10,    alarm >100
  mmp8_ng_ml           — MMP-8;       healthy <30,    alarm >150
  pgrp_s_ng_ml         — PGRP-S;      healthy <20,    alarm >100
  calprotectin_ug_g    — Calprotectin;healthy <50,    alarm >200
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Optional


# Autocorrelation coefficients per marker (higher = more persistent)
ALPHA = {
    "mpo_ng_ml":            0.72,
    "haptoglobin_ug_g":     0.70,
    "fibrinogen_ng_ml":     0.75,
    "mmp9_ng_ml":           0.73,
    "hemoglobin_fit_ng_ml": 0.70,
    "mmp8_ng_ml":           0.73,
    "pgrp_s_ng_ml":         0.68,
    "calprotectin_ug_g":    0.72,
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
            "mpo_ng_ml":            _lognormal(55 + drift_factor * 20, 0.40),
            "haptoglobin_ug_g":     _lognormal(14 + drift_factor * 8,  0.45),
            "fibrinogen_ng_ml":     _lognormal(45 + drift_factor * 20, 0.40),
            "mmp9_ng_ml":           _lognormal(11 + drift_factor * 5,  0.50),
            "hemoglobin_fit_ng_ml": _lognormal(4  + drift_factor * 2,  0.40),
            "mmp8_ng_ml":           _lognormal(11 + drift_factor * 5,  0.50),
            "pgrp_s_ng_ml":         _lognormal(7  + drift_factor * 3,  0.40),
            "calprotectin_ug_g":    _lognormal(28 + drift_factor * 10, 0.45),
        }
    elif archetype == "at_risk":
        return {
            "mpo_ng_ml":            _lognormal(200 + drift_factor * 80, 0.55),
            "haptoglobin_ug_g":     _lognormal(80  + drift_factor * 30, 0.55),
            "fibrinogen_ng_ml":     _lognormal(170 + drift_factor * 60, 0.55),
            "mmp9_ng_ml":           _lognormal(65  + drift_factor * 25, 0.55),
            "hemoglobin_fit_ng_ml": _lognormal(28  + drift_factor * 15, 0.55),
            "mmp8_ng_ml":           _lognormal(65  + drift_factor * 25, 0.55),
            "pgrp_s_ng_ml":         _lognormal(42  + drift_factor * 18, 0.50),
            "calprotectin_ug_g":    _lognormal(80  + drift_factor * 40, 0.55),
        }
    else:  # critical
        return {
            "mpo_ng_ml":            _lognormal(620, 0.50),
            "haptoglobin_ug_g":     _lognormal(260, 0.50),
            "fibrinogen_ng_ml":     _lognormal(510, 0.50),
            "mmp9_ng_ml":           _lognormal(200, 0.50),
            "hemoglobin_fit_ng_ml": _lognormal(130, 0.50),
            "mmp8_ng_ml":           _lognormal(200, 0.50),
            "pgrp_s_ng_ml":         _lognormal(140, 0.50),
            "calprotectin_ug_g":    _lognormal(260, 0.50),
        }


def _clamp(reading: dict) -> dict:
    """Clamp values to physiologically plausible ranges."""
    reading["mpo_ng_ml"]            = max(1.0,  reading["mpo_ng_ml"])
    reading["haptoglobin_ug_g"]     = max(0.5,  reading["haptoglobin_ug_g"])
    reading["fibrinogen_ng_ml"]     = max(1.0,  reading["fibrinogen_ng_ml"])
    reading["mmp9_ng_ml"]           = max(0.5,  reading["mmp9_ng_ml"])
    reading["hemoglobin_fit_ng_ml"] = max(0.1,  reading["hemoglobin_fit_ng_ml"])
    reading["mmp8_ng_ml"]           = max(0.5,  reading["mmp8_ng_ml"])
    reading["pgrp_s_ng_ml"]         = max(0.5,  reading["pgrp_s_ng_ml"])
    reading["calprotectin_ug_g"]    = max(1.0,  reading["calprotectin_ug_g"])
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
