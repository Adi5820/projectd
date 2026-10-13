'use client';

import React from 'react';
import { JobResponse, JobStatus } from '@/lib/types';
import { Loader2, CheckCircle2, AlertTriangle, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface JobStatusBadgeProps {
  job?: JobResponse | null;
  status?: JobStatus | string;
  className?: string;
  showStep?: boolean;
}

export function JobStatusBadge({
  job,
  status: manualStatus,
  className,
  showStep = true,
}: JobStatusBadgeProps) {
  const currentStatus = (job?.status || manualStatus || 'pending') as JobStatus;
  const progressValue =
    typeof job?.progress === 'number'
      ? job.progress
      : typeof job?.progress === 'object' && job.progress
      ? job.progress.percentage ??
        ((job.progress.steps_completed ?? 0) /
          Math.max(job.progress.total_steps ?? 1, 1)) *
          100
      : 0;
  const currentStep =
    job?.current_step ||
    job?.message ||
    (typeof job?.progress === 'object' && job.progress
      ? job.progress.current_step || job.progress.message
      : undefined);

  const config = {
    pending: {
      color: 'bg-slate-800/80 text-slate-300 border-slate-700',
      icon: <Clock className="w-3.5 h-3.5 text-slate-400" />,
      label: 'Queued',
    },
    queued: {
      color: 'bg-slate-800/80 text-slate-300 border-slate-700',
      icon: <Clock className="w-3.5 h-3.5 text-slate-400" />,
      label: 'Queued',
    },
    running: {
      color: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
      icon: <Loader2 className="w-3.5 h-3.5 animate-spin text-amber-400" />,
      label: 'Processing',
    },
    completed: {
      color: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
      icon: <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />,
      label: 'Completed',
    },
    partial: {
      color: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
      icon: <Loader2 className="w-3.5 h-3.5 animate-spin text-amber-400" />,
      label: 'Partial',
    },
    failed: {
      color: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
      icon: <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />,
      label: 'Failed',
    },
  };

  const statusConfig = config[currentStatus] || config.pending;

  return (
    <div className={cn('inline-flex flex-col gap-1', className)}>
      <div
        className={cn(
          'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border shadow-sm',
          statusConfig.color
        )}
      >
        {statusConfig.icon}
        <span className="capitalize">{statusConfig.label}</span>
        {Number.isFinite(progressValue) && currentStatus === 'running' && (
          <span className="font-semibold text-amber-300 ml-1">
            {Math.round(progressValue)}%
          </span>
        )}
      </div>

      {showStep && (currentStatus === 'running' || currentStatus === 'queued') && currentStep && (
        <span className="text-[11px] text-slate-400 truncate max-w-xs pl-1">
          {currentStep}
        </span>
      )}
    </div>
  );
}
