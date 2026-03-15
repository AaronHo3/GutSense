from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from database import Base


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    sex = Column(String, nullable=False)  # M / F
    family_history = Column(Boolean, default=False)
    has_nod2_variant = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    readings = relationship("BiomarkerReading", back_populates="patient")
    risk_assessments = relationship("RiskAssessment", back_populates="patient")
    alerts = relationship("Alert", back_populates="patient")
    clinical_notes = relationship("ClinicalNote", back_populates="patient")
    lifestyle_metadata = relationship("LifestyleMetadata", back_populates="patient")


class BiomarkerReading(Base):
    __tablename__ = "biomarker_readings"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    visit_number = Column(Integer, nullable=False, default=1)

    # Primary biomarkers
    mpo_ng_ml = Column(Float, nullable=False)              # Myeloperoxidase; normal <100
    haptoglobin_ug_g = Column(Float, nullable=False)       # Haptoglobin (fecal); normal <50
    fibrinogen_ng_ml = Column(Float, nullable=False)       # Fibrinogen (fecal); normal <100
    mmp9_ng_ml = Column(Float, nullable=False)             # MMP-9; normal <30
    hemoglobin_fit_ng_ml = Column(Float, nullable=False)   # Hemoglobin FIT; normal <10
    mmp8_ng_ml = Column(Float, nullable=False)             # MMP-8; normal <30
    pgrp_s_ng_ml = Column(Float, nullable=False)           # PGRP-S; normal <20
    calprotectin_ug_g = Column(Float, nullable=False)      # Calprotectin; normal <50

    patient = relationship("Patient", back_populates="readings")
    risk_assessment = relationship("RiskAssessment", back_populates="reading", uselist=False)


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id = Column(Integer, primary_key=True, index=True)
    reading_id = Column(Integer, ForeignKey("biomarker_readings.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    raw_score = Column(Float, nullable=False)       # 0-100 before contextual adjustments
    adjusted_score = Column(Float, nullable=False)  # 0-100 final score
    risk_level = Column(String, nullable=False)     # green / yellow / orange / red
    trajectory = Column(String, default="Stable")  # Stable / Slowly Increasing / Rapidly Increasing / Improving
    confounded_by = Column(String, nullable=True)   # e.g. "recent antibiotic use"

    # Per-biomarker component scores (0-100 each, before weighting)
    score_breakdown = Column(JSON, nullable=True)   # dict: marker -> component score

    # Claude-generated content
    patient_explanation = Column(Text, nullable=True)
    physician_summary = Column(Text, nullable=True)
    next_steps = Column(JSON, nullable=True)        # list of strings
    urgency_flag = Column(String, default="routine")  # routine / elevated / urgent

    reading = relationship("BiomarkerReading", back_populates="risk_assessment")
    patient = relationship("Patient", back_populates="risk_assessments")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    reading_id = Column(Integer, ForeignKey("biomarker_readings.id"), nullable=True)
    severity = Column(String, nullable=False)  # info / warning / critical
    message = Column(Text, nullable=False)
    acknowledged = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    patient = relationship("Patient", back_populates="alerts")


class ClinicalNote(Base):
    __tablename__ = "clinical_notes"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    note_text = Column(Text, nullable=False)
    is_physician_recommendation = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="clinical_notes")


class LifestyleMetadata(Base):
    __tablename__ = "lifestyle_metadata"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow)
    recent_antibiotic_use = Column(Boolean, default=False)
    fiber_intake_g_day = Column(Float, nullable=True)   # grams/day; high >25g
    sleep_quality = Column(Integer, nullable=True)       # 1-5 scale
    notes = Column(Text, nullable=True)

    patient = relationship("Patient", back_populates="lifestyle_metadata")
