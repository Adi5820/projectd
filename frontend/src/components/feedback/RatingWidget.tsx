'use client';

import React, { useState } from 'react';
import { Star, Send, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { submitFeedback } from '@/lib/api';
import { FeedbackCreate } from '@/lib/types';
import { cn } from '@/lib/utils';

export interface RatingWidgetProps {
  campaignId: string;
  contentType: 'ad_copy' | 'poster' | 'video' | 'campaign';
  contentId?: string;
  className?: string;
  onSubmitted?: () => void;
}

export function RatingWidget({
  campaignId,
  contentType,
  contentId,
  className,
  onSubmitted,
}: RatingWidgetProps) {
  const [rating, setRating] = useState<number>(0);
  const [hoverRating, setHoverRating] = useState<number>(0);
  const [comment, setComment] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [isSubmitted, setIsSubmitted] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (rating === 0) {
      setError('Please select a star rating');
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);
      const payload: FeedbackCreate = {
        campaign_id: campaignId,
        content_type: contentType,
        content_id: contentId,
        rating,
        comment: comment.trim() || undefined,
      };

      await submitFeedback(payload);
      setIsSubmitted(true);
      if (onSubmitted) onSubmitted();
    } catch (err: any) {
      setError(err.message || 'Failed to submit feedback');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isSubmitted) {
    return (
      <div className={cn('p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center gap-2 text-xs', className)}>
        <CheckCircle2 className="w-4 h-4 shrink-0" />
        <span>Thank you for your feedback! Rating recorded.</span>
      </div>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      className={cn(
        'p-4 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm space-y-3',
        className
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-slate-300">
          Rate this {contentType.replace('_', ' ')}
        </span>
        <div className="flex items-center gap-1">
          {[1, 2, 3, 4, 5].map((star) => (
            <button
              key={star}
              type="button"
              onClick={() => setRating(star)}
              onMouseEnter={() => setHoverRating(star)}
              onMouseLeave={() => setHoverRating(0)}
              className="p-1 focus:outline-none transition-transform hover:scale-110"
              aria-label={`Rate ${star} stars`}
            >
              <Star
                className={cn(
                  'w-4 h-4 transition-colors',
                  (hoverRating || rating) >= star
                    ? 'fill-amber-400 text-amber-400'
                    : 'text-slate-600'
                )}
              />
            </button>
          ))}
        </div>
      </div>

      <textarea
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        placeholder="Optional comments or suggestions..."
        rows={2}
        className="w-full text-xs rounded-lg bg-slate-950/80 border border-slate-800 p-2.5 text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-indigo-500"
      />

      {error && <p className="text-xs text-rose-400">{error}</p>}

      <div className="flex justify-end">
        <Button
          type="submit"
          size="sm"
          variant="secondary"
          isLoading={isSubmitting}
          leftIcon={<Send className="w-3 h-3" />}
          disabled={rating === 0}
        >
          Submit Feedback
        </Button>
      </div>
    </form>
  );
}
