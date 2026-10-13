'use client';

import React from 'react';
import { cn } from '@/lib/utils';

export interface ProgressBarProps {
  progress: number; // 0 to 100
  label?: string;
  stepInfo?: string;
  className?: string;
  showPercent?: boolean;
}

export function ProgressBar({
  progress,
  label,
  stepInfo,
  className,
  showPercent = true,
}: ProgressBarProps) {
  const clampedProgress = Math.min(Math.max(Math.round(progress), 0), 100);

  return (
    <div className={cn('w-full space-y-1.5', className)}>
      <div className="flex items-center justify-between text-xs text-slate-300">
        <span className="font-medium text-slate-200">
          {label || 'Generating content...'}
        </span>
        {showPercent && (
          <span className="font-mono text-cyan-400 font-semibold">
            {clampedProgress}%
          </span>
        )}
      </div>

      {/* Progress track */}
      <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800 border border-slate-700/50">
        <div
          className="h-full bg-gradient-to-r from-indigo-500 via-purple-500 to-cyan-400 transition-all duration-500 ease-out shadow-sm"
          style={{ width: `${clampedProgress}%` }}
        />
      </div>

      {stepInfo && (
        <p className="text-[11px] text-slate-400 animate-pulse truncate">
          {stepInfo}
        </p>
      )}
    </div>
  );
}
