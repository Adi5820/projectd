'use client';

import { useState, useEffect, useCallback } from 'react';
import { getJobStatus } from '@/lib/api';
import { JobResponse } from '@/lib/types';

interface UseJobStatusResult {
  job: JobResponse | null;
  isLoading: boolean;
  isComplete: boolean;
  isFailed: boolean;
  error: string | null;
  reset: () => void;
}

export function useJobStatus(
  jobId: string | null,
  onComplete?: (job: JobResponse) => void
): UseJobStatusResult {
  const [job, setJob] = useState<JobResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const reset = useCallback(() => {
    setJob(null);
    setIsLoading(false);
    setError(null);
  }, []);

  useEffect(() => {
    if (!jobId) {
      setJob(null);
      setIsLoading(false);
      setError(null);
      return;
    }

    let isMounted = true;
    let timerId: NodeJS.Timeout | null = null;
    setIsLoading(true);
    setError(null);

    const checkStatus = async () => {
      try {
        const data = await getJobStatus(jobId);
        if (!isMounted) return;

        setJob(data);

        if (data.status === 'completed') {
          setIsLoading(false);
          if (onComplete) {
            onComplete(data);
          }
        } else if (data.status === 'failed') {
          setIsLoading(false);
          setError(data.error || data.message || 'Job execution failed');
        } else {
          // Continue polling if pending or running
          timerId = setTimeout(checkStatus, 2000);
        }
      } catch (err: any) {
        if (!isMounted) return;
        setError(err.message || 'Failed to poll job status');
        setIsLoading(false);
      }
    };

    checkStatus();

    return () => {
      isMounted = false;
      if (timerId) {
        clearTimeout(timerId);
      }
    };
  }, [jobId, onComplete]);

  const isComplete = job?.status === 'completed';
  const isFailed = job?.status === 'failed';

  return {
    job,
    isLoading,
    isComplete,
    isFailed,
    error,
    reset,
  };
}
