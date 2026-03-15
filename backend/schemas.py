from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


# ── Patient ────────────────────────────────────────────────────────────────────

class PatientBase(BaseModel):
    name: str
    age: int
    sex: str
    family_history: bool = False
    has_nod2_variant: bool = False

class PatientCreate(PatientBase):
    pass

class PatientOut(PatientBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ── Biomarker Reading ──────────────────────────────────────────────────────────

class ReadingIngest(BaseModel):
    patient_id: int
    timestamp: Optional[datetime] = None
    mpo_ng_ml: float
    haptoglobin_ug_g: float
    fibrinogen_ng_ml: float
    mmp9_ng_ml: float
    hemoglobin_fit_ng_ml: float
    mmp8_ng_ml: float
    pgrp_s_ng_ml: float
    calprotectin_ug_g: float
    visit_number: int = 1

class ReadingOut(BaseModel):
    id: int
    patient_id: int
    timestamp: datetime
    visit_number: int
    mpo_ng_ml: float
    haptoglobin_ug_g: float
    fibrinogen_ng_ml: float
    mmp9_ng_ml: float
    hemoglobin_fit_ng_ml: float
    mmp8_ng_ml: float
    pgrp_s_ng_ml: float
    calprotectin_ug_g: float

    class Config:
        from_attributes = True


# ── Risk Assessment ────────────────────────────────────────────────────────────

class RiskAssessmentOut(BaseModel):
    id: int
    reading_id: int
    patient_id: int
    timestamp: datetime
    raw_score: float
    adjusted_score: float
    risk_level: str
    trajectory: str
    confounded_by: Optional[str]
    score_breakdown: Optional[dict] = None
    patient_explanation: Optional[str]
    physician_summary: Optional[str]
    next_steps: Optional[List[str]]
    urgency_flag: str

    class Config:
        from_attributes = True


# ── Alert ──────────────────────────────────────────────────────────────────────

class AlertOut(BaseModel):
    id: int
    patient_id: int
    reading_id: Optional[int]
    severity: str
    message: str
    acknowledged: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Clinical Note ──────────────────────────────────────────────────────────────

class ClinicalNoteCreate(BaseModel):
    note_text: str
    is_physician_recommendation: bool = False

class ClinicalNoteOut(BaseModel):
    id: int
    patient_id: int
    note_text: str
    is_physician_recommendation: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Lifestyle Metadata ─────────────────────────────────────────────────────────

class LifestyleMetadataCreate(BaseModel):
    recent_antibiotic_use: bool = False
    fiber_intake_g_day: Optional[float] = None
    sleep_quality: Optional[int] = None
    notes: Optional[str] = None

class LifestyleMetadataOut(LifestyleMetadataCreate):
    id: int
    patient_id: int
    recorded_at: datetime

    class Config:
        from_attributes = True


# ── Physician patient summary ──────────────────────────────────────────────────

class PatientSummary(BaseModel):
    patient: PatientOut
    latest_risk: Optional[RiskAssessmentOut]
    unacknowledged_alerts: int
    latest_reading: Optional[ReadingOut]
