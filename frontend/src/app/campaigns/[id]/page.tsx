'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  Sparkles,
  Layers,
  Image as ImageIcon,
  Video,
  Copy,
  Check,
  Download,
  Play,
  RotateCw,
  ExternalLink,
  Clock,
  Send,
  Eye,
  AlertCircle,
  FileText,
  Sliders,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs';
import { Select } from '@/components/ui/Select';
import { ProgressBar } from '@/components/shared/ProgressBar';
import { JobStatusBadge } from '@/components/shared/JobStatusBadge';
import { RatingWidget } from '@/components/feedback/RatingWidget';
import { EmptyState } from '@/components/shared/EmptyState';
import { useJobStatus } from '@/hooks/useJobStatus';
import {
  getCampaign,
  generateFull,
  generateAdCopy,
  generatePoster,
  generateVideo,
} from '@/lib/api';
import {
  CampaignDetailResponse,
  AdCopyResponse,
  PosterResponse,
  VideoResponse,
} from '@/lib/types';
import { formatDate, formatMediaUrl, truncateText } from '@/lib/utils';

export default function CampaignDetailPage() {
  const params = useParams();
  const campaignId = params.id as string;

  const [campaignData, setCampaignData] =
    useState<CampaignDetailResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Active Job state
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [activeJobType, setActiveJobType] = useState<string>('pipeline');

  // Generation Modal States
  const [showCopyModal, setShowCopyModal] = useState<boolean>(false);
  const [copyPlatform, setCopyPlatform] = useState<string>('instagram');
  const [copyNumVariations, setCopyNumVariations] = useState<number>(3);

  const [showPosterModal, setShowPosterModal] = useState<boolean>(false);
  const [posterAspectRatio, setPosterAspectRatio] = useState<string>('1:1');
  const [posterPlatform, setPosterPlatform] = useState<string>('instagram');

  const [showVideoModal, setShowVideoModal] = useState<boolean>(false);
  const [videoDuration, setVideoDuration] = useState<number>(15);
  const [videoPlatform, setVideoPlatform] = useState<string>('tiktok');

  // Preview Image Modal
  const [previewImage, setPreviewImage] = useState<string | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const refreshData = useCallback(async () => {
    if (!campaignId) return;
    try {
      const data = await getCampaign(campaignId);
      setCampaignData(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load campaign');
    }
  }, [campaignId]);

  // Hook for tracking background jobs
  const { job, isLoading: jobRunning, isComplete, isFailed } = useJobStatus(
    activeJobId,
    () => {
      // Refresh campaign on completion
      refreshData();
    }
  );

  useEffect(() => {
    setIsLoading(true);
    refreshData().finally(() => setIsLoading(false));
  }, [refreshData]);

  const handleCopyText = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const handleTriggerFullPipeline = async () => {
    try {
      setError(null);
      setActiveJobType('Full Campaign Generation');
      const res = await generateFull(campaignId);
      setActiveJobId(res.job_id);
    } catch (err: any) {
      setError(err.message || 'Failed to start full generation');
    }
  };

  const handleTriggerAdCopy = async () => {
    try {
      setShowCopyModal(false);
      setError(null);
      setActiveJobType('Ad Copy Variations');
      const res = await generateAdCopy({
        campaign_id: campaignId,
        platform: copyPlatform,
        num_variations: copyNumVariations,
      });
      setActiveJobId(res.job_id);
    } catch (err: any) {
      setError(err.message || 'Failed to generate ad copy');
    }
  };

  const handleTriggerPoster = async () => {
    try {
      setShowPosterModal(false);
      setError(null);
      setActiveJobType('Promotional Poster');
      const res = await generatePoster({
        campaign_id: campaignId,
        aspect_ratio: posterAspectRatio,
        platform: posterPlatform,
      });
      setActiveJobId(res.job_id);
    } catch (err: any) {
      setError(err.message || 'Failed to generate poster');
    }
  };

  const handleTriggerVideo = async () => {
    try {
      setShowVideoModal(false);
      setError(null);
      setActiveJobType('Video Commercial');
      const res = await generateVideo({
        campaign_id: campaignId,
        duration_seconds: videoDuration,
        platform: videoPlatform,
      });
      setActiveJobId(res.job_id);
    } catch (err: any) {
      setError(err.message || 'Failed to generate video');
    }
  };

  if (isLoading) {
    return (
      <div className="flex-1 p-10 flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-3">
          <RotateCw className="w-8 h-8 animate-spin text-indigo-400" />
          <p className="text-sm text-slate-400">Loading campaign details...</p>
        </div>
      </div>
    );
  }

  if (error && !campaignData) {
    return (
      <div className="flex-1 p-10 max-w-3xl mx-auto">
        <EmptyState
          icon={AlertCircle}
          title="Campaign Not Found"
          description={error}
          actionLabel="Back to Campaigns"
          onAction={() => (window.location.href = '/campaigns')}
        />
      </div>
    );
  }

  const campaign = campaignData?.campaign;
  const adCopies = campaignData?.ad_copies || [];
  const posters = campaignData?.posters || [];
  const videos = campaignData?.videos || [];

  const getProgressValue = (value: number | { percentage?: number; steps_completed?: number; total_steps?: number } | undefined) => {
    if (typeof value === 'number' && Number.isFinite(value)) return value;
    if (typeof value === 'object' && value) {
      const progress =
        value.percentage ??
        ((value.steps_completed ?? 0) / Math.max(value.total_steps ?? 1, 1)) * 100;
      return Number.isFinite(progress) ? progress : 35;
    }
    return 35;
  };

  const getCurrentStep = (value: number | { current_step?: string; message?: string } | undefined) => {
    if (typeof value === 'object' && value) {
      return value.current_step || value.message;
    }
    return undefined;
  };

  return (
    <div className="flex-1 p-6 md:p-10 space-y-8 max-w-7xl mx-auto w-full">
      {/* Header Bar */}
      <div className="relative rounded-2xl border border-slate-800 bg-slate-900/60 p-6 md:p-8 backdrop-blur-md">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-2 max-w-2xl">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-indigo-400">
                {campaign?.brand_name}
              </span>
              <span className="text-slate-600">•</span>
              <Badge
                variant={
                  campaign?.status === 'completed'
                    ? 'success'
                    : campaign?.status === 'running'
                    ? 'warning'
                    : 'default'
                }
                dot
              >
                {campaign?.status}
              </Badge>
            </div>

            <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight">
              {campaign?.product_name}
            </h1>

            <p className="text-xs md:text-sm text-slate-300 leading-relaxed">
              {campaign?.product_description}
            </p>

            <div className="flex flex-wrap items-center gap-2 pt-2">
              <span className="text-xs text-slate-400 mr-1">Channels:</span>
              {campaign?.platforms?.map((p) => (
                <Badge key={p} platform={p} variant="outline" className="text-[10px]" />
              ))}
              <span className="text-slate-600">•</span>
              <span className="text-xs text-slate-400">
                Tone: <strong className="text-slate-200 capitalize">{campaign?.tone}</strong>
              </span>
              <span className="text-slate-600">•</span>
              <span className="text-xs text-slate-400">
                Goal:{' '}
                <strong className="text-slate-200 capitalize">
                  {campaign?.campaign_goal?.replace('_', ' ')}
                </strong>
              </span>
            </div>
          </div>

          {/* Action Trigger Buttons */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 shrink-0">
            <Button
              variant="primary"
              size="lg"
              isLoading={jobRunning}
              onClick={handleTriggerFullPipeline}
              leftIcon={<Sparkles className="w-5 h-5" />}
              className="shadow-indigo-500/25"
            >
              Generate Full Campaign
            </Button>
            <Button
              variant="outline"
              size="lg"
              onClick={refreshData}
              leftIcon={<RotateCw className="w-4 h-4" />}
            >
              Refresh
            </Button>
          </div>
        </div>

        {/* Real-time Job Progress Indicator Banner */}
        {activeJobId && (
          <div className="mt-6 pt-6 border-t border-slate-800">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-2">
              <div className="flex items-center gap-2">
                <JobStatusBadge job={job} />
                <span className="text-xs font-semibold text-slate-200">
                  {activeJobType}
                </span>
              </div>
              <span className="text-xs text-slate-400 font-mono">Job ID: {activeJobId.slice(0, 12)}</span>
            </div>
            {jobRunning && (
              <ProgressBar
                progress={getProgressValue(job?.progress)}
                stepInfo={
                  job?.current_step ||
                  getCurrentStep(job?.progress) ||
                  'Agentic workers generating creative assets...'
                }
              />
            )}
            {isComplete && (
              <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center gap-2">
                <Check className="w-4 h-4" />
                <span>Job completed successfully! Creative assets updated.</span>
              </div>
            )}
            {isFailed && (
              <div className="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4" />
                <span>Job failed: {job?.error || 'Unknown error during execution.'}</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Main Tabs Navigation */}
      <Tabs defaultValue="overview" className="w-full space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-3">
          <TabsList className="bg-slate-900/90 p-1">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger
              value="ad-copy"
              icon={<Layers className="w-4 h-4" />}
              badge={
                <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-slate-800 font-mono">
                  {adCopies.reduce((acc, c) => acc + (c.variations?.length || 0), 0)}
                </span>
              }
            >
              Ad Copy
            </TabsTrigger>
            <TabsTrigger
              value="posters"
              icon={<ImageIcon className="w-4 h-4" />}
              badge={
                <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-slate-800 font-mono">
                  {posters.length}
                </span>
              }
            >
              Posters
            </TabsTrigger>
            <TabsTrigger
              value="videos"
              icon={<Video className="w-4 h-4" />}
              badge={
                <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-slate-800 font-mono">
                  {videos.length}
                </span>
              }
            >
              Videos
            </TabsTrigger>
          </TabsList>
        </div>

        {/* OVERVIEW TAB */}
        <TabsContent value="overview">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              {/* Asset Generation Status Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <Card className="p-4 border-slate-800 bg-slate-900/60">
                  <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
                    <span className="font-semibold text-slate-200">Ad Variations</span>
                    <Layers className="w-4 h-4 text-cyan-400" />
                  </div>
                  <div className="text-2xl font-bold text-white">
                    {adCopies.reduce((acc, c) => acc + (c.variations?.length || 0), 0)}
                  </div>
                  <p className="text-[11px] text-slate-400 mt-1">Multi-platform variations</p>
                </Card>

                <Card className="p-4 border-slate-800 bg-slate-900/60">
                  <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
                    <span className="font-semibold text-slate-200">Posters</span>
                    <ImageIcon className="w-4 h-4 text-purple-400" />
                  </div>
                  <div className="text-2xl font-bold text-white">{posters.length}</div>
                  <p className="text-[11px] text-slate-400 mt-1">Promotional visuals</p>
                </Card>

                <Card className="p-4 border-slate-800 bg-slate-900/60">
                  <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
                    <span className="font-semibold text-slate-200">Videos</span>
                    <Video className="w-4 h-4 text-rose-400" />
                  </div>
                  <div className="text-2xl font-bold text-white">{videos.length}</div>
                  <p className="text-[11px] text-slate-400 mt-1">Commercial clips</p>
                </Card>
              </div>

              {/* Campaign Strategy Card */}
              <Card className="p-6 border-slate-800 bg-slate-900/60 space-y-4">
                <h3 className="text-base font-bold text-white">Targeting Strategy</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                  <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800">
                    <span className="text-slate-400 block mb-1">Target Audience</span>
                    <p className="text-slate-200 leading-relaxed">
                      {campaign?.target_audience}
                    </p>
                  </div>
                  <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800">
                    <span className="text-slate-400 block mb-1">Context / Instructions</span>
                    <p className="text-slate-200 leading-relaxed">
                      {campaign?.additional_context || 'None specified'}
                    </p>
                  </div>
                </div>
              </Card>

              {/* Quick Preview of Best Copy & Poster */}
              {adCopies.length > 0 && adCopies[0].variations?.length > 0 && (
                <Card className="p-6 border-slate-800 bg-slate-900/60 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-indigo-400 uppercase tracking-wider">
                      Featured Ad Variation
                    </span>
                    <Badge platform={adCopies[0].variations[0].platform} variant="outline" />
                  </div>
                  <h4 className="text-lg font-bold text-white">
                    {adCopies[0].variations[0].headline}
                  </h4>
                  <p className="text-sm text-slate-300">
                    {adCopies[0].variations[0].description}
                  </p>
                  <div className="text-xs font-semibold text-cyan-400">
                    CTA: {adCopies[0].variations[0].call_to_action}
                  </div>
                </Card>
              )}
            </div>

            {/* Sidebar Feedback & Metadata */}
            <div className="space-y-6">
              <Card className="p-6 border-slate-800 bg-slate-900/60 space-y-4">
                <h3 className="text-sm font-bold text-white">Rate Campaign Results</h3>
                <p className="text-xs text-slate-400">
                  Rate the AI multi-agent orchestration for this campaign to tune future iterations.
                </p>
                <RatingWidget
                  campaignId={campaignId}
                  contentType="campaign"
                />
              </Card>

              <Card className="p-6 border-slate-800 bg-slate-900/60 space-y-3 text-xs">
                <h3 className="text-sm font-bold text-white">Metadata</h3>
                <div className="flex justify-between py-1 border-b border-slate-800">
                  <span className="text-slate-400">Created:</span>
                  <span className="text-slate-200">{formatDate(campaign?.created_at)}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-800">
                  <span className="text-slate-400">Industry:</span>
                  <span className="text-slate-200">{campaign?.industry || 'Technology'}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-800">
                  <span className="text-slate-400">Language:</span>
                  <span className="text-slate-200">{campaign?.language || 'English'}</span>
                </div>
              </Card>
            </div>
          </div>
        </TabsContent>

        {/* AD COPY TAB */}
        <TabsContent value="ad-copy" className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-xl font-bold text-white">Ad Copy Variations</h2>
              <p className="text-xs text-slate-400">
                Persona-driven copy variations generated across multiple channels
              </p>
            </div>
            <Button
              variant="primary"
              size="md"
              onClick={() => setShowCopyModal(true)}
              leftIcon={<Sparkles className="w-4 h-4" />}
            >
              Generate Copy
            </Button>
          </div>

          {adCopies.length === 0 || adCopies.every((c) => !c.variations?.length) ? (
            <EmptyState
              icon={Layers}
              title="No Ad Copy Generated Yet"
              description="Click 'Generate Copy' to write headlines, body text, hashtags, and call-to-actions tailored for your audience."
              actionLabel="Generate Now"
              onAction={() => setShowCopyModal(true)}
              actionIcon={<Sparkles className="w-4 h-4" />}
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {adCopies.flatMap((c) =>
                c.variations.map((v, idx) => {
                  const cardKey = `${c.id}-${idx}`;
                  const isCopied = copiedKey === cardKey;

                  return (
                    <Card
                      key={cardKey}
                      className="p-6 border-slate-800 bg-slate-900/60 flex flex-col justify-between space-y-4"
                    >
                      <div className="space-y-3">
                        <div className="flex items-center justify-between gap-2">
                          <Badge platform={v.platform} variant="outline" />
                          <button
                            onClick={() =>
                              handleCopyText(
                                `${v.headline}\n\n${v.description}\n\n${v.call_to_action}\n\n${(v.hashtags || []).join(' ')}`,
                                cardKey
                              )
                            }
                            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
                            title="Copy full ad"
                          >
                            {isCopied ? (
                              <Check className="w-4 h-4 text-emerald-400" />
                            ) : (
                              <Copy className="w-4 h-4" />
                            )}
                          </button>
                        </div>

                        {v.slogan && (
                          <div className="text-xs font-bold text-indigo-400 tracking-wide uppercase">
                            &ldquo;{v.slogan}&rdquo;
                          </div>
                        )}

                        <h3 className="text-lg font-bold text-white leading-snug">
                          {v.headline}
                        </h3>

                        <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-line">
                          {v.description}
                        </p>

                        {v.caption && (
                          <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 text-xs text-slate-400 italic">
                            {v.caption}
                          </div>
                        )}

                        {v.hashtags && v.hashtags.length > 0 && (
                          <div className="flex flex-wrap gap-1.5 pt-1">
                            {v.hashtags.map((h, hIdx) => (
                              <span
                                key={hIdx}
                                className="text-xs font-mono text-cyan-400 hover:underline cursor-pointer"
                              >
                                {h.startsWith('#') ? h : `#${h}`}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>

                      <div className="pt-4 border-t border-slate-800 flex items-center justify-between text-xs">
                        <span className="font-semibold text-slate-200 bg-slate-800 px-3 py-1 rounded-md">
                          CTA: {v.call_to_action}
                        </span>
                        {v.quality_score && (
                          <span className="text-emerald-400 font-semibold font-mono">
                            Score: {v.quality_score}/10
                          </span>
                        )}
                      </div>
                    </Card>
                  );
                })
              )}
            </div>
          )}
        </TabsContent>

        {/* POSTERS TAB */}
        <TabsContent value="posters" className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-xl font-bold text-white">Visual Posters</h2>
              <p className="text-xs text-slate-400">
                Studio-grade marketing banners, Instagram stories, and ad images
              </p>
            </div>
            <Button
              variant="primary"
              size="md"
              onClick={() => setShowPosterModal(true)}
              leftIcon={<ImageIcon className="w-4 h-4" />}
            >
              Generate Poster
            </Button>
          </div>

          {posters.length === 0 ? (
            <EmptyState
              icon={ImageIcon}
              title="No Posters Generated Yet"
              description="Synthesize high-resolution promotional artwork in multiple aspect ratios (1:1, 9:16, 16:9)."
              actionLabel="Generate Poster"
              onAction={() => setShowPosterModal(true)}
              actionIcon={<Sparkles className="w-4 h-4" />}
            />
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {posters.map((poster) => {
                const fullUrl = formatMediaUrl(poster.image_url);
                return (
                  <Card
                    key={poster.id}
                    className="border-slate-800 bg-slate-900/60 overflow-hidden flex flex-col group"
                  >
                    {/* Image Preview Container */}
                    <div className="relative aspect-square w-full bg-slate-950 overflow-hidden flex items-center justify-center">
                      <img
                        src={fullUrl}
                        alt={poster.prompt || 'Generated ad poster'}
                        className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
                        onError={(e) => {
                          // Fallback placeholder styling
                          (e.target as HTMLElement).style.display = 'none';
                        }}
                      />
                      <div className="absolute inset-0 bg-slate-950/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-3">
                        <button
                          onClick={() => setPreviewImage(fullUrl)}
                          className="p-2.5 rounded-full bg-slate-900/90 text-white hover:bg-indigo-600 transition-colors shadow-lg"
                          title="Preview full size"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                        <a
                          href={fullUrl}
                          download={`poster-${poster.id}.png`}
                          target="_blank"
                          rel="noreferrer"
                          className="p-2.5 rounded-full bg-slate-900/90 text-white hover:bg-cyan-600 transition-colors shadow-lg"
                          title="Download Image"
                        >
                          <Download className="w-4 h-4" />
                        </a>
                      </div>
                    </div>

                    <div className="p-4 space-y-2 flex-1 flex flex-col justify-between">
                      <div className="flex items-center justify-between text-xs">
                        <Badge variant="outline">{poster.aspect_ratio || '1:1'}</Badge>
                        {poster.platform && (
                          <Badge platform={poster.platform} variant="outline" />
                        )}
                      </div>

                      {poster.prompt && (
                        <p className="text-xs text-slate-400 line-clamp-2">
                          {poster.prompt}
                        </p>
                      )}

                      <div className="pt-2 flex items-center justify-between text-[11px] text-slate-500">
                        <span>{formatDate(poster.created_at)}</span>
                        <a
                          href={fullUrl}
                          target="_blank"
                          rel="noreferrer"
                          className="text-cyan-400 hover:underline flex items-center gap-1 font-medium"
                        >
                          Open Raw <ExternalLink className="w-3 h-3" />
                        </a>
                      </div>
                    </div>
                  </Card>
                );
              })}
            </div>
          )}
        </TabsContent>

        {/* VIDEOS TAB */}
        <TabsContent value="videos" className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-xl font-bold text-white">Commercial Video Ads</h2>
              <p className="text-xs text-slate-400">
                Multi-scene animated commercials with Edge-TTS neural narration
              </p>
            </div>
            <Button
              variant="primary"
              size="md"
              onClick={() => setShowVideoModal(true)}
              leftIcon={<Video className="w-4 h-4" />}
            >
              Generate Video
            </Button>
          </div>

          {videos.length === 0 ? (
            <EmptyState
              icon={Video}
              title="No Video Ads Generated Yet"
              description="Assemble scripted scenes into a ready-to-broadcast MP4 ad video with voiceover."
              actionLabel="Generate Video"
              onAction={() => setShowVideoModal(true)}
              actionIcon={<Sparkles className="w-4 h-4" />}
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              {videos.map((vid) => {
                const videoUrl = formatMediaUrl(vid.video_url);

                return (
                  <Card
                    key={vid.id}
                    className="border-slate-800 bg-slate-900/60 overflow-hidden flex flex-col"
                  >
                    {/* HTML5 Video Player */}
                    <div className="relative aspect-video w-full bg-slate-950 flex items-center justify-center">
                      <video
                        controls
                        src={videoUrl}
                        poster={vid.thumbnail_url ? formatMediaUrl(vid.thumbnail_url) : undefined}
                        className="w-full h-full object-contain"
                      >
                        Your browser does not support the video tag.
                      </video>
                    </div>

                    <div className="p-6 space-y-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Badge variant="outline">
                            <Clock className="w-3 h-3 mr-1" />
                            {vid.duration || 15}s
                          </Badge>
                          {vid.platform && (
                            <Badge platform={vid.platform} variant="outline" />
                          )}
                        </div>
                        <a
                          href={videoUrl}
                          download={`video-${vid.id}.mp4`}
                          className="inline-flex items-center gap-1.5 text-xs text-cyan-400 hover:text-cyan-300 font-medium"
                        >
                          <Download className="w-3.5 h-3.5" /> Download MP4
                        </a>
                      </div>

                      {/* Video Script Scenes Breakdown */}
                      {vid.script && vid.script.scenes && (
                        <div className="space-y-2 pt-2 border-t border-slate-800">
                          <span className="text-xs font-semibold text-slate-300">
                            Scene Script Breakdown ({vid.script.scenes.length} scenes)
                          </span>
                          <div className="space-y-2 max-h-40 overflow-y-auto pr-1">
                            {vid.script.scenes.map((scene) => (
                              <div
                                key={scene.scene_number}
                                className="p-2.5 rounded-lg bg-slate-950/70 border border-slate-800 text-xs space-y-1"
                              >
                                <div className="flex justify-between text-indigo-400 font-semibold">
                                  <span>Scene {scene.scene_number}</span>
                                  <span>{scene.duration_seconds}s</span>
                                </div>
                                <div className="text-slate-300 text-[11px]">
                                  &ldquo;{scene.voiceover_text}&rdquo;
                                </div>
                                <div className="text-slate-500 text-[10px]">
                                  Visual: {scene.visual_description}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </Card>
                );
              })}
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Modal: Generate Ad Copy */}
      <Modal
        isOpen={showCopyModal}
        onClose={() => setShowCopyModal(false)}
        title="Generate Ad Copy Variations"
        description="Configure target platform and the number of creative variations."
      >
        <div className="space-y-4">
          <Select
            label="Target Channel"
            value={copyPlatform}
            onChange={(e) => setCopyPlatform(e.target.value)}
            options={[
              { value: 'instagram', label: 'Instagram' },
              { value: 'facebook', label: 'Facebook' },
              { value: 'twitter', label: 'Twitter / X' },
              { value: 'linkedin', label: 'LinkedIn' },
              { value: 'tiktok', label: 'TikTok' },
              { value: 'google_ads', label: 'Google Search Ads' },
            ]}
          />

          <Select
            label="Variation Count"
            value={copyNumVariations.toString()}
            onChange={(e) => setCopyNumVariations(Number(e.target.value))}
            options={[
              { value: '1', label: '1 Variation' },
              { value: '3', label: '3 Variations (Recommended)' },
              { value: '5', label: '5 Variations' },
            ]}
          />

          <div className="flex justify-end gap-3 pt-4">
            <Button variant="outline" onClick={() => setShowCopyModal(false)}>
              Cancel
            </Button>
            <Button variant="primary" onClick={handleTriggerAdCopy}>
              Start Generation
            </Button>
          </div>
        </div>
      </Modal>

      {/* Modal: Generate Poster */}
      <Modal
        isOpen={showPosterModal}
        onClose={() => setShowPosterModal(false)}
        title="Generate Promotional Poster"
        description="Select image dimensions and channel format."
      >
        <div className="space-y-4">
          <Select
            label="Aspect Ratio"
            value={posterAspectRatio}
            onChange={(e) => setPosterAspectRatio(e.target.value)}
            options={[
              { value: '1:1', label: 'Square (1:1) - Instagram Post / Feed' },
              { value: '9:16', label: 'Vertical Story (9:16) - TikTok / Reels' },
              { value: '16:9', label: 'Landscape (16:9) - Twitter / YouTube' },
              { value: '4:5', label: 'Portrait (4:5) - Instagram Feed' },
            ]}
          />

          <Select
            label="Target Platform"
            value={posterPlatform}
            onChange={(e) => setPosterPlatform(e.target.value)}
            options={[
              { value: 'instagram', label: 'Instagram' },
              { value: 'facebook', label: 'Facebook' },
              { value: 'twitter', label: 'Twitter / X' },
              { value: 'linkedin', label: 'LinkedIn' },
            ]}
          />

          <div className="flex justify-end gap-3 pt-4">
            <Button variant="outline" onClick={() => setShowPosterModal(false)}>
              Cancel
            </Button>
            <Button variant="primary" onClick={handleTriggerPoster}>
              Generate Poster
            </Button>
          </div>
        </div>
      </Modal>

      {/* Modal: Generate Video */}
      <Modal
        isOpen={showVideoModal}
        onClose={() => setShowVideoModal(false)}
        title="Generate Video Commercial"
        description="Configure target clip duration and platform formatting."
      >
        <div className="space-y-4">
          <Select
            label="Target Video Duration"
            value={videoDuration.toString()}
            onChange={(e) => setVideoDuration(Number(e.target.value))}
            options={[
              { value: '15', label: '15 Seconds (Micro-Ad / Stories)' },
              { value: '30', label: '30 Seconds (Standard Commercial)' },
            ]}
          />

          <Select
            label="Platform"
            value={videoPlatform}
            onChange={(e) => setVideoPlatform(e.target.value)}
            options={[
              { value: 'tiktok', label: 'TikTok (9:16 vertical)' },
              { value: 'instagram', label: 'Instagram Reels / Feed' },
              { value: 'youtube', label: 'YouTube Shorts / Pre-roll' },
            ]}
          />

          <div className="flex justify-end gap-3 pt-4">
            <Button variant="outline" onClick={() => setShowVideoModal(false)}>
              Cancel
            </Button>
            <Button variant="primary" onClick={handleTriggerVideo}>
              Synthesize Video
            </Button>
          </div>
        </div>
      </Modal>

      {/* Modal: Fullscreen Image Preview */}
      <Modal
        isOpen={!!previewImage}
        onClose={() => setPreviewImage(null)}
        maxWidth="4xl"
      >
        {previewImage && (
          <div className="flex flex-col items-center justify-center p-2">
            <img
              src={previewImage}
              alt="Poster Preview"
              className="max-h-[75vh] w-auto rounded-xl object-contain shadow-2xl"
            />
            <div className="mt-4 flex gap-4">
              <a
                href={previewImage}
                download="agentic-ads-poster.png"
                target="_blank"
                rel="noreferrer"
              >
                <Button variant="primary" leftIcon={<Download className="w-4 h-4" />}>
                  Download High-Res
                </Button>
              </a>
              <Button variant="outline" onClick={() => setPreviewImage(null)}>
                Close
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
