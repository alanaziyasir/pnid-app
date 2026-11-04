'use client';

import { useEffect, useState } from 'react';
import { DetectionResult, loadDetections } from '../../lib/detection';
import { logError } from '../../lib/logger';
import { trackEvent } from '../../lib/telemetry';

interface State {
  storedName: string | null;
  result: DetectionResult | null;
  loading: boolean;
  error: string;
}

export function useDetection(storedName: string | null) {
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<State>({
    storedName,
    result: null,
    loading: false,
    error: '',
  });
  useEffect(() => {
    const controller = new AbortController();
    const initial = { storedName, result: null };
    if (!storedName) {
      setState({ ...initial, loading: false, error: 'Please upload a diagram before processing.' });
      return () => controller.abort();
    }
    setState({ ...initial, loading: true, error: '' });
    trackEvent('detection_started');
    loadDetections(storedName, controller.signal)
      .then((result) => {
        if (!controller.signal.aborted) {
          trackEvent('detection_completed');
          setState({ storedName, result, loading: false, error: '' });
        }
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        trackEvent('detection_failed');
        logError('detection_failed');
        setState({
          ...initial,
          loading: false,
          error: error instanceof Error ? error.message : 'Detection is unavailable.',
        });
      });
    return () => controller.abort();
  }, [storedName, attempt]);
  const current =
    state.storedName === storedName
      ? state
      : { storedName, result: null, loading: true, error: '' };
  return { ...current, retry: () => setAttempt((value) => value + 1) };
}
