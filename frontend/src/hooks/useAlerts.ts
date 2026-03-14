import { useState, useEffect, useCallback } from 'react';
import { api } from '../api/endpoints';
import type { Alert } from '../types';

export function useAlerts(patientId: number, pollInterval = 10000) {
  const [alerts, setAlerts] = useState<Alert[]>([]);

  const fetch = useCallback(async () => {
    try {
      const data = await api.getAlerts(patientId);
      setAlerts(data);
    } catch {}
  }, [patientId]);

  useEffect(() => {
    fetch();
    const timer = setInterval(fetch, pollInterval);
    return () => clearInterval(timer);
  }, [fetch, pollInterval]);

  const acknowledge = async (alertId: number) => {
    await api.acknowledgeAlert(patientId, alertId);
    setAlerts(prev => prev.filter(a => a.id !== alertId));
  };

  return { alerts, acknowledge, refetch: fetch };
}
