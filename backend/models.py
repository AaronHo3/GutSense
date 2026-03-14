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
    hemoglobin_ng_ml = Column(Float, nullable=False)       # occult blood; normal <20
    butyrate_mmol_kg = Column(Float, nullable=False)       # SCFA; normal >15
    calprotectin_ug_g = Column(Float, nullable=False)      # inflammation; normal <50
    basidio_ascomy_ratio = Column(Float, nullable=False)   # fungal dysbiosis; normal <1.5
    proteobacteria_index = Column(Float, nullable=False)   # pathobionts 0-1; normal <0.2
    methylation_score = Column(Float, nullable=False)      # SEPT9+SDC2, 0-1; normal <0.25

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
