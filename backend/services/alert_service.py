"""
Creates Alert records when risk thresholds are crossed.
Called after each ingest + risk scoring cycle.
"""

import os
from sqlalchemy.orm import Session
import models

ALERT_THRESHOLD = float(os.getenv("RISK_ALERT_THRESHOLD", "60"))


def maybe_create_alert(
    db: Session,
    patient_id: int,
    reading_id: int,
    adjusted_score: float,
    risk_level: str,
    confounded_by: str | None,
) -> models.Alert | None:
    """
    Create an alert only if:
    - score >= threshold
    - not confounded by antibiotics (suppressed)
    - no unacknowledged alert for this reading already exists
    """
    if adjusted_score < ALERT_THRESHOLD:
        return None
    if confounded_by:  # confounded readings don't trigger alerts
        return None

    severity_map = {
        "yellow": "info",
        "orange": "warning",
        "red": "critical",
    }
    severity = severity_map.get(risk_level, "info")

    # Deduplicate: don't create another alert of the same severity while one is unacknowledged
    existing = (
        db.query(models.Alert)
        .filter(
            models.Alert.patient_id == patient_id,
            models.Alert.severity == severity,
            models.Alert.acknowledged == False,  # noqa: E712
        )
        .first()
    )
    if existing:
        return None

    message_map = {
        "info": "Your biomarker readings are elevated. Consider scheduling a physician consultation.",
        "warning": "Multiple biomarkers are significantly elevated. Please schedule a doctor's appointment soon.",
        "critical": "Critical biomarker levels detected. Please contact your physician immediately.",
    }

    alert = models.Alert(
        patient_id=patient_id,
        reading_id=reading_id,
        severity=severity,
        message=message_map[severity],
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert
