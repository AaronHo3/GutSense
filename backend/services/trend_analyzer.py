"""
Computes linear regression trend over the last N readings per patient.
Returns a trajectory label and per-marker slopes.
"""

from typing import Optional
import numpy as np
from sqlalchemy.orm import Session
import models

WINDOW = 14  # readings to include in trend analysis


def compute_trajectory(db: Session, patient_id: int, current_risk_score: float) -> str:
    """
    Look at the last WINDOW risk assessments for the patient and fit a line.
    Returns: Stable | Slowly Increasing | Rapidly Increasing | Improving
    """
    recent = (
        db.query(models.RiskAssessment)
        .filter(models.RiskAssessment.patient_id == patient_id)
        .order_by(models.RiskAssessment.timestamp.desc())
        .limit(WINDOW)
        .all()
    )

    if len(recent) < 3:
        return "Stable"

    scores = [r.adjusted_score for r in reversed(recent)]
    x = np.arange(len(scores), dtype=float)
    slope, _ = np.polyfit(x, scores, 1)

    if slope > 0.50:
        return "Rapidly Increasing"
    elif slope > 0.07:
        return "Slowly Increasing"
    elif slope < -0.07:
        return "Improving"
    else:
        return "Stable"
