"""
Small neural network risk model.

Architecture:
  Inputs (13 features):
    - 8 sigmoid-transformed biomarker scores (0-100, from ai_risk_model.py)
    - age normalized (age / 80)
    - family_history (0 or 1)
    - 3 RAG scores: risk scores of the top-3 most similar historical patients
      retrieved via fast SQLite kNN on biomarker values

  Network: 13 → Dense(32, relu) → Dense(16, relu) → Dense(1, linear) → clamp 0-100

Training:
  5,000 synthetic samples generated from our biomarker simulator.
  Labels = sigmoid formula output + demographic adjustments (our clinical ground truth).
  RAG features are simulated as correlated noise around the label.
  Weights cached to disk; retrained at startup if missing.

In production:
  Replace synthetic labels with real clinical outcomes (colonoscopy results, CRC diagnoses).
  The architecture is identical — only the training data changes.
"""

import os
import math
import logging
import numpy as np
import joblib
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

_HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH  = os.path.join(_HERE, "risk_model.joblib")
SCALER_PATH = os.path.join(_HERE, "risk_scaler.joblib")

_model:  MLPRegressor   = None
_scaler: StandardScaler = None


# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------

def build_features(
    component_scores: dict,
    patient_age: int,
    family_history: bool,
    rag_scores: list,          # up to 3 floats; padded with 50.0 if fewer
) -> np.ndarray:
    """
    Pack all inputs into a fixed-length feature vector.
    component_scores: output of ai_risk_model sigmoid curves (keys match WEIGHTS).
    """
    biomarker_feats = [
        component_scores.get("hemoglobin_fit", 0.0),
        component_scores.get("calprotectin",   0.0),
        component_scores.get("mmp9",           0.0),
        component_scores.get("mpo",            0.0),
        component_scores.get("mmp8",           0.0),
        component_scores.get("fibrinogen",     0.0),
        component_scores.get("haptoglobin",    0.0),
        component_scores.get("pgrp_s",         0.0),
    ]
    patient_feats = [
        min(patient_age / 80.0, 1.0),
        1.0 if family_history else 0.0,
    ]
    # Always provide 3 RAG slots; default to 50 (neutral) when unavailable
    padded_rag = (list(rag_scores) + [50.0, 50.0, 50.0])[:3]

    return np.array(biomarker_feats + patient_feats + padded_rag, dtype=np.float32)


# ---------------------------------------------------------------------------
# Synthetic training data
# ---------------------------------------------------------------------------

def _generate_training_data(n_samples: int = 5000) -> tuple:
    """
    Generate synthetic (X, y) pairs.

    For each sample:
      - Pick an archetype (healthy / at_risk / critical)
      - Generate a reading from the simulator
      - Compute sigmoid component scores + weighted sum label
      - Simulate RAG scores as correlated noise around the label
    """
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(_HERE)))

    from services.ai_risk_model import (
        _score_hemoglobin_fit, _score_calprotectin,
        _score_mmp9, _score_mpo, _score_mmp8,
        _score_fibrinogen, _score_haptoglobin, _score_pgrp_s, WEIGHTS,
    )
    from simulator.biomarker_distributions import BiomarkerState

    rng = np.random.default_rng(42)
    archetypes  = ["healthy", "at_risk", "critical"]
    arch_probs  = [0.50, 0.35, 0.15]   # rough clinical prevalence

    X, y = [], []
    for _ in range(n_samples):
        archetype = rng.choice(archetypes, p=arch_probs)
        state     = BiomarkerState(archetype=archetype)
        reading   = state.next_reading()

        age        = int(rng.integers(28, 76))
        family_hx  = rng.random() < 0.20

        comp = {
            "hemoglobin_fit": _score_hemoglobin_fit(reading["hemoglobin_fit_ng_ml"]),
            "calprotectin":   _score_calprotectin(reading["calprotectin_ug_g"]),
            "mmp9":           _score_mmp9(reading["mmp9_ng_ml"]),
            "mpo":            _score_mpo(reading["mpo_ng_ml"]),
            "mmp8":           _score_mmp8(reading["mmp8_ng_ml"]),
            "fibrinogen":     _score_fibrinogen(reading["fibrinogen_ng_ml"]),
            "haptoglobin":    _score_haptoglobin(reading["haptoglobin_ug_g"]),
            "pgrp_s":         _score_pgrp_s(reading["pgrp_s_ng_ml"]),
        }

        raw   = sum(comp[k] * w for k, w in WEIGHTS.items())
        label = raw + (10 if age > 50 else 0) + (5 if family_hx else 0)
        label = float(np.clip(label, 0, 100))

        # Simulate what kNN would return: similar patients have similar scores
        rag = [
            float(np.clip(label + rng.normal(0, 8),  0, 100)),
            float(np.clip(label + rng.normal(0, 12), 0, 100)),
            float(np.clip(label + rng.normal(0, 18), 0, 100)),
        ]

        X.append(build_features(comp, age, family_hx, rag))
        y.append(label)

    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)


# ---------------------------------------------------------------------------
# Train / load
# ---------------------------------------------------------------------------

def train_model() -> tuple:
    """Train the MLP and persist weights. Returns (model, scaler)."""
    logger.info("[nn_risk_model] Generating training data...")
    X, y = _generate_training_data(n_samples=5000)

    scaler  = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = MLPRegressor(
        hidden_layer_sizes=(32, 16),
        activation="relu",
        solver="adam",
        max_iter=500,
        random_state=42,
        early_stopping=True,
        validation_fraction=0.15,
        n_iter_no_change=20,
        verbose=False,
    )
    model.fit(X_scaled, y)

    joblib.dump(model,  MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)

    val_score = getattr(model, "best_validation_score_", None)
    logger.info(f"[nn_risk_model] Trained. Val R²={val_score:.3f}" if val_score else "[nn_risk_model] Trained.")
    return model, scaler


def _load() -> tuple:
    global _model, _scaler
    if _model is not None:
        return _model, _scaler
    if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
        _model  = joblib.load(MODEL_PATH)
        _scaler = joblib.load(SCALER_PATH)
        logger.info("[nn_risk_model] Loaded cached weights.")
    else:
        _model, _scaler = train_model()
    return _model, _scaler


def ensure_trained():
    """Call at startup to warm the model (trains if weights missing)."""
    _load()


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------

def predict(
    component_scores: dict,
    patient_age: int,
    family_history: bool,
    rag_scores: list,
) -> float:
    """Return a risk score 0-100."""
    model, scaler = _load()
    feats = build_features(component_scores, patient_age, family_history, rag_scores)
    X     = scaler.transform(feats.reshape(1, -1))
    score = float(model.predict(X)[0])
    return float(np.clip(score, 0.0, 100.0))
