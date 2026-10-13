'use client';

import React, { HTMLAttributes } from 'react';
import { cn } from '@/lib/utils';
import {
  Share2,
  Instagram,
  Twitter,
  Linkedin,
  Youtube,
  Globe,
  Radio,
  CheckCircle2,
  Clock,
  AlertCircle,
  FileText,
} from 'lucide-react';

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'success' | 'warning' | 'error' | 'outline' | 'gradient';
  platform?: string;
  dot?: boolean;
}

export function Badge({
  className,
  variant = 'default',
  platform,
  dot = false,
  children,
  ...props
}: BadgeProps) {
  const getPlatformIcon = (plat?: string) => {
    switch (plat?.toLowerCase()) {
      case 'instagram':
        return <Instagram className="w-3 h-3 text-pink-400" />;
      case 'twitter':
      case 'x':
        return <Twitter className="w-3 h-3 text-sky-400" />;
      case 'linkedin':
        return <Linkedin className="w-3 h-3 text-blue-400" />;
      case 'youtube':
        return <Youtube className="w-3 h-3 text-red-400" />;
      case 'tiktok':
        return <Radio className="w-3 h-3 text-teal-400" />;
      case 'facebook':
        return <Share2 className="w-3 h-3 text-blue-500" />;
      case 'google_ads':
        return <Globe className="w-3 h-3 text-amber-400" />;
      default:
        return null;
    }
  };

  const variants = {
    default: 'bg-slate-800 text-slate-300 border-slate-700/60',
    success: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    warning: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    error: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
    outline: 'bg-transparent text-slate-400 border-slate-700',
    gradient: 'bg-gradient-to-r from-indigo-500/20 to-cyan-500/20 text-cyan-300 border-cyan-500/30',
  };

  const dotColors = {
    default: 'bg-slate-400',
    success: 'bg-emerald-400',
    warning: 'bg-amber-400 animate-pulse',
    error: 'bg-rose-400',
    outline: 'bg-slate-500',
    gradient: 'bg-cyan-400',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border transition-colors',
        variants[variant],
        className
      )}
      {...props}
    >
      {dot && <span className={cn('w-1.5 h-1.5 rounded-full', dotColors[variant])} />}
      {platform && getPlatformIcon(platform)}
      <span>{children || platform}</span>
    </span>
  );
}
