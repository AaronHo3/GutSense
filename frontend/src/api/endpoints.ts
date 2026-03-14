import client from './client';
import type {
  Patient,
  BiomarkerReading,
  RiskAssessment,
  Alert,
  ClinicalNote,
  LifestyleMetadata,
  PatientSummary,
  IrisStatus,
  IrisPatientSummary,
  IrisPatientDetail,
} from '../types';

export const api = {
  // Patients
  getPatients: () => client.get<Patient[]>('/api/patients').then(r => r.data),
  getPatient: (id: number) => client.get<Patient>(`/api/patients/${id}`).then(r => r.data),

  // Readings
  getReadings: (patientId: number, limit = 180) =>
    client.get<BiomarkerReading[]>(`/api/patients/${patientId}/readings?limit=${limit}`).then(r => r.data),

  // Risk
  getLatestRisk: (patientId: number) =>
    client.get<RiskAssessment>(`/api/patients/${patientId}/risk/latest`).then(r => r.data),
  getRiskHistory: (patientId: number) =>
    client.get<RiskAssessment[]>(`/api/patients/${patientId}/risk/history`).then(r => r.data),

  // Alerts
  getAlerts: (patientId: number) =>
    client.get<Alert[]>(`/api/patients/${patientId}/alerts`).then(r => r.data),
  acknowledgeAlert: (patientId: number, alertId: number) =>
    client.post<Alert>(`/api/patients/${patientId}/alerts/${alertId}/acknowledge`).then(r => r.data),

  // Clinical notes
  getNotes: (patientId: number) =>
    client.get<ClinicalNote[]>(`/api/patients/${patientId}/notes`).then(r => r.data),
  addNote: (patientId: number, noteText: string, isRecommendation = false) =>
    client.post<ClinicalNote>(`/api/patients/${patientId}/notes`, {
      note_text: noteText,
      is_physician_recommendation: isRecommendation,
    }).then(r => r.data),

  // Lifestyle
  getLifestyle: (patientId: number) =>
    client.get<LifestyleMetadata | null>(`/api/patients/${patientId}/lifestyle`).then(r => r.data),
  updateLifestyle: (patientId: number, data: Partial<LifestyleMetadata>) =>
    client.post<LifestyleMetadata>(`/api/patients/${patientId}/lifestyle`, data).then(r => r.data),

  // Physician roster
  getPhysicianRoster: () =>
    client.get<PatientSummary[]>('/api/physician/patients').then(r => r.data),

  // Demo actions
  simulateSpike: (patientId: number) =>
    client.post(`/api/patients/${patientId}/simulate-spike`).then(r => r.data),

  // Recalculate score with current lifestyle
  recalculateScore: (patientId: number) =>
    client.post<RiskAssessment>(`/api/patients/${patientId}/recalculate`).then(r => r.data),

  // IRIS FHIR
  getIrisStatus: () =>
    client.get<IrisStatus>('/api/iris/status').then(r => r.data),
  getIrisPatients: () =>
    client.get<{ patients: IrisPatientSummary[]; total: number }>('/api/iris/patients').then(r => r.data),
  getIrisPatient: (fhirId: string) =>
    client.get<IrisPatientDetail>(`/api/iris/patients/${fhirId}`).then(r => r.data),
  refreshIrisCache: () =>
    client.post('/api/iris/refresh').then(r => r.data),
  getIrisFhirBundle: (patientId: string) =>
    client.get(`/api/iris/patients/${patientId}/fhir`).then(r => r.data),
};
