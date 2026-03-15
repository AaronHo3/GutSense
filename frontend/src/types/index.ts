export interface Patient {
  id: number;
  name: string;
  age: number;
  sex: string;
  family_history: boolean;
  has_nod2_variant: boolean;
  created_at: string;
}

export interface BiomarkerReading {
  id: number;
  patient_id: number;
  timestamp: string;
  visit_number: number;
  mpo_ng_ml: number;
  haptoglobin_ug_g: number;
  fibrinogen_ng_ml: number;
  mmp9_ng_ml: number;
  hemoglobin_fit_ng_ml: number;
  mmp8_ng_ml: number;
  pgrp_s_ng_ml: number;
  calprotectin_ug_g: number;
}

export interface RiskAssessment {
  id: number;
  reading_id: number;
  patient_id: number;
  timestamp: string;
  raw_score: number;
  adjusted_score: number;
  risk_level: 'green' | 'yellow' | 'orange' | 'red';
  trajectory: string;
  confounded_by: string | null;
  score_breakdown: Record<string, number> | null;
  patient_explanation: string | null;
  physician_summary: string | null;
  next_steps: string[] | null;
  urgency_flag: string;
}

export interface Alert {
  id: number;
  patient_id: number;
  reading_id: number | null;
  severity: 'info' | 'warning' | 'critical';
  message: string;
  acknowledged: boolean;
  created_at: string;
}

export interface ClinicalNote {
  id: number;
  patient_id: number;
  note_text: string;
  is_physician_recommendation: boolean;
  created_at: string;
}

export interface LifestyleMetadata {
  id: number;
  patient_id: number;
  recorded_at: string;
  recent_antibiotic_use: boolean;
  fiber_intake_g_day: number | null;
  sleep_quality: number | null;
  notes: string | null;
}

export interface PatientSummary {
  patient: Patient;
  latest_risk: RiskAssessment | null;
  unacknowledged_alerts: number;
  latest_reading: BiomarkerReading | null;
}

// IRIS FHIR types
export interface IrisStatus {
  connected: boolean;
  fhir_base: string | null;
  vector_search: boolean;
  langchain_rag: boolean;
  iris_host: string;
  message: string;
}

export interface IrisPatientSummary {
  fhir_id: string;
  name: string;
  age: number | null;
  gender: string;
  risk_score: number;
  risk_level: 'low' | 'medium' | 'high';
  summary: string;
  key_findings: string[];
  recommendation: string;
  risk_factors: string[];
  diagnostic_reports_count: number;
  observations_count: number;
}

export interface IrisObservation {
  loinc: string | null;
  display: string;
  value: string | null;
  unit: string | null;
  interpretation: string | null;
  status: string;
  date: string | null;
  is_stool_related: boolean;
  is_high_weight: boolean;
}

export interface IrisReport {
  id: string | null;
  status: string | null;
  code: string;
  date: string | null;
  conclusion: string | null;
}

export interface IrisSimilarCase {
  patient_name: string;
  risk_level: 'low' | 'medium' | 'high';
  risk_score: number;
  similarity: number;
  summary: string;
}

export interface IrisPatientDetail extends IrisPatientSummary {
  rag_summary: string | null;
  rag_powered_by: string | null;
  similar_cases: IrisSimilarCase[];
  fhir_bundle_id: string | null;
  observations: IrisObservation[];
  reports: IrisReport[];
}
