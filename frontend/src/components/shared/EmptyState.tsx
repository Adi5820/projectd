'use client';

import React, { ReactNode } from 'react';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';
import { LucideIcon, Sparkles } from 'lucide-react';

export interface EmptyStateProps {
  icon?: LucideIcon | ReactNode;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  actionIcon?: ReactNode;
  className?: string;
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  actionLabel,
  onAction,
  actionIcon,
  className,
}: EmptyStateProps) {
  const renderIcon = () => {
    if (!Icon) {
      return <Sparkles className="w-8 h-8 text-indigo-400" />;
    }
    if (typeof Icon === 'function') {
      const Component = Icon as LucideIcon;
      return <Component className="w-8 h-8 text-indigo-400" />;
    }
    return Icon;
  };

  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center text-center p-8 sm:p-12 rounded-2xl border border-dashed border-slate-800 bg-slate-900/30 max-w-lg mx-auto',
        className
      )}
    >
      <div className="flex items-center justify-center w-16 h-16 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 mb-4 shadow-inner">
        {renderIcon()}
      </div>
      <h3 className="text-lg font-semibold text-white mb-2">{title}</h3>
      <p className="text-sm text-slate-400 max-w-sm mb-6 leading-relaxed">
        {description}
      </p>
      {actionLabel && onAction && (
        <Button
          onClick={onAction}
          variant="primary"
          leftIcon={actionIcon}
          className="shadow-md"
        >
          {actionLabel}
        </Button>
      )}
    </div>
  );
}
