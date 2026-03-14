import { useState, useEffect, useCallback } from 'react';
import { api } from '../api/endpoints';
import type { BiomarkerReading, RiskAssessment } from '../types';

export function usePatientData(patientId: number, pollInterval = 10000) {
  const [readings, setReadings] = useState<BiomarkerReading[]>([]);
  const [latestRisk, setLatestRisk] = useState<RiskAssessment | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    try {
      const [r, risk] = await Promise.all([
        api.getReadings(patientId),
        api.getLatestRisk(patientId).catch(() => null),
      ]);
      setReadings(r);
      setLatestRisk(risk);
      setError(null);
    } catch (e) {
      setError('Failed to load patient data');
    } finally {
      setLoading(false);
    }
  }, [patientId]);

  useEffect(() => {
    fetch();
    const timer = setInterval(fetch, pollInterval);
    return () => clearInterval(timer);
  }, [fetch, pollInterval]);

  return { readings, latestRisk, loading, error, refetch: fetch };
}
