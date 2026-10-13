'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Image as ImageIcon,
  Video,
  Filter,
  Download,
  Eye,
  Play,
  RotateCw,
  Clock,
  Sparkles,
  ExternalLink,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';
import { EmptyState } from '@/components/shared/EmptyState';
import { getCampaigns, getPosters, getVideos } from '@/lib/api';
import { Campaign, PosterResponse, VideoResponse } from '@/lib/types';
import { formatDate, formatMediaUrl } from '@/lib/utils';

interface GalleryItem {
  id: string;
  type: 'poster' | 'video';
  campaign_id: string;
  campaign_brand?: string;
  campaign_product?: string;
  media_url: string;
  thumbnail_url?: string;
  aspect_ratio?: string;
  duration?: number;
  platform?: string;
  prompt?: string;
  created_at: string;
}

export default function GalleryPage() {
  const [items, setItems] = useState<GalleryItem[]>([]);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Filters
  const [contentType, setContentType] = useState<'all' | 'poster' | 'video'>('all');
  const [selectedCampaign, setSelectedCampaign] = useState<string>('all');
  const [selectedPlatform, setSelectedPlatform] = useState<string>('all');

  // Preview modals
  const [previewPoster, setPreviewPoster] = useState<GalleryItem | null>(null);
  const [previewVideo, setPreviewVideo] = useState<GalleryItem | null>(null);

  useEffect(() => {
    loadAllMedia();
  }, []);

  const loadAllMedia = async () => {
    try {
      setIsLoading(true);
      const campList = await getCampaigns(0, 50);
      setCampaigns(campList || []);

      const allItems: GalleryItem[] = [];

      // Fetch posters and videos across campaigns
      await Promise.all(
        (campList || []).map(async (c) => {
          try {
            const [posters, videos] = await Promise.all([
              getPosters(c.id).catch(() => [] as PosterResponse[]),
              getVideos(c.id).catch(() => [] as VideoResponse[]),
            ]);

            posters.forEach((p) => {
              allItems.push({
                id: p.id,
                type: 'poster',
                campaign_id: c.id,
                campaign_brand: c.brand_name,
                campaign_product: c.product_name,
                media_url: p.image_url,
                aspect_ratio: p.aspect_ratio,
                platform: p.platform,
                prompt: p.prompt,
                created_at: p.created_at,
              });
            });

            videos.forEach((v) => {
              allItems.push({
                id: v.id,
                type: 'video',
                campaign_id: c.id,
                campaign_brand: c.brand_name,
                campaign_product: c.product_name,
                media_url: v.video_url,
                thumbnail_url: v.thumbnail_url,
                duration: v.duration,
                platform: v.platform,
                created_at: v.created_at,
              });
            });
          } catch {
            // Ignore single campaign errors
          }
        })
      );

      // Sort newest first
      allItems.sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );

      setItems(allItems);
    } catch {
      setItems([]);
    } finally {
      setIsLoading(false);
    }
  };

  const filteredItems = items.filter((item) => {
    const matchesType = contentType === 'all' || item.type === contentType;
    const matchesCampaign =
      selectedCampaign === 'all' || item.campaign_id === selectedCampaign;
    const matchesPlatform =
      selectedPlatform === 'all' ||
      item.platform?.toLowerCase() === selectedPlatform.toLowerCase();

    return matchesType && matchesCampaign && matchesPlatform;
  });

  return (
    <div className="flex-1 p-6 md:p-10 space-y-8 max-w-7xl mx-auto w-full">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-white flex items-center gap-2.5">
            <ImageIcon className="w-7 h-7 text-indigo-400" />
            Media Gallery
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Browse all visual assets, promotional posters, and commercial videos generated across your campaigns
          </p>
        </div>
        <Button
          variant="outline"
          onClick={loadAllMedia}
          leftIcon={<RotateCw className="w-4 h-4" />}
        >
          Refresh Gallery
        </Button>
      </div>

      {/* Filter Toolbar */}
      <div className="flex flex-wrap items-center gap-4 p-4 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-md">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-400" />
          <span className="text-xs font-semibold uppercase text-slate-400">
            Filter:
          </span>
        </div>

        {/* Content Type Filter */}
        <div className="inline-flex rounded-lg bg-slate-950 p-1 border border-slate-800 text-xs">
          {(['all', 'poster', 'video'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setContentType(t)}
              className={`px-3 py-1 rounded-md font-medium capitalize transition-all ${
                contentType === t
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              {t === 'all' ? 'All Formats' : `${t}s`}
            </button>
          ))}
        </div>

        {/* Campaign Filter */}
        <select
          value={selectedCampaign}
          onChange={(e) => setSelectedCampaign(e.target.value)}
          className="rounded-lg bg-slate-950 border border-slate-800 px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
        >
          <option value="all">All Campaigns</option>
          {campaigns.map((c) => (
            <option key={c.id} value={c.id}>
              {c.brand_name} - {c.product_name}
            </option>
          ))}
        </select>

        {/* Platform Filter */}
        <select
          value={selectedPlatform}
          onChange={(e) => setSelectedPlatform(e.target.value)}
          className="rounded-lg bg-slate-950 border border-slate-800 px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
        >
          <option value="all">All Channels</option>
          <option value="instagram">Instagram</option>
          <option value="facebook">Facebook</option>
          <option value="twitter">Twitter / X</option>
          <option value="linkedin">LinkedIn</option>
          <option value="tiktok">TikTok</option>
          <option value="youtube">YouTube</option>
        </select>
      </div>

      {/* Gallery Items Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
          {Array.from({ length: 8 }).map((_, i) => (
            <div
              key={i}
              className="h-64 rounded-xl bg-slate-900/60 border border-slate-800 animate-pulse"
            />
          ))}
        </div>
      ) : filteredItems.length === 0 ? (
        <EmptyState
          icon={ImageIcon}
          title="No Media Generated Yet"
          description="Launch a campaign or generate posters and videos to view them in this central gallery."
          actionLabel="Create Campaign"
          onAction={() => (window.location.href = '/campaigns/new')}
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
          {filteredItems.map((item) => {
            const mediaUrl = formatMediaUrl(item.media_url);

            return (
              <Card
                key={item.id}
                className="group border-slate-800 bg-slate-900/60 overflow-hidden flex flex-col justify-between hover:border-slate-700 transition-all"
              >
                {/* Media Container */}
                <div className="relative aspect-square w-full bg-slate-950 overflow-hidden flex items-center justify-center">
                  {item.type === 'poster' ? (
                    <img
                      src={mediaUrl}
                      alt={item.prompt || 'Generated poster'}
                      className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
                      onError={(e) => {
                        (e.target as HTMLElement).style.display = 'none';
                      }}
                    />
                  ) : (
                    <div className="relative w-full h-full flex items-center justify-center bg-slate-950">
                      {item.thumbnail_url ? (
                        <img
                          src={formatMediaUrl(item.thumbnail_url)}
                          alt="Video thumbnail"
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <Video className="w-12 h-12 text-slate-700" />
                      )}
                      <div className="absolute inset-0 flex items-center justify-center bg-black/40">
                        <div className="w-12 h-12 rounded-full bg-indigo-600/90 flex items-center justify-center text-white shadow-lg">
                          <Play className="w-5 h-5 ml-0.5 fill-white" />
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Hover Overlay Controls */}
                  <div className="absolute inset-0 bg-slate-950/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-3">
                    <button
                      onClick={() =>
                        item.type === 'poster'
                          ? setPreviewPoster(item)
                          : setPreviewVideo(item)
                      }
                      className="p-2.5 rounded-full bg-slate-900 text-white hover:bg-indigo-600 transition-colors shadow-lg"
                      title="Inspect full asset"
                    >
                      {item.type === 'poster' ? (
                        <Eye className="w-4 h-4" />
                      ) : (
                        <Play className="w-4 h-4" />
                      )}
                    </button>
                    <a
                      href={mediaUrl}
                      download={`asset-${item.id}`}
                      target="_blank"
                      rel="noreferrer"
                      className="p-2.5 rounded-full bg-slate-900 text-white hover:bg-cyan-600 transition-colors shadow-lg"
                      title="Download file"
                    >
                      <Download className="w-4 h-4" />
                    </a>
                  </div>
                </div>

                {/* Metadata details */}
                <div className="p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-bold uppercase text-indigo-400 truncate max-w-[120px]">
                      {item.campaign_brand || 'Campaign'}
                    </span>
                    <Badge variant="outline" className="text-[10px]">
                      {item.type === 'poster'
                        ? item.aspect_ratio || '1:1'
                        : `${item.duration || 15}s`}
                    </Badge>
                  </div>

                  <Link
                    href={`/campaigns/${item.campaign_id}`}
                    className="block text-xs font-semibold text-white hover:text-cyan-300 truncate transition-colors"
                  >
                    {item.campaign_product || 'View Campaign'}
                  </Link>

                  <div className="pt-2 flex items-center justify-between text-[11px] text-slate-500 border-t border-slate-800/80">
                    <span>{formatDate(item.created_at)}</span>
                    {item.platform && <Badge platform={item.platform} variant="outline" />}
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* Poster Modal */}
      <Modal
        isOpen={!!previewPoster}
        onClose={() => setPreviewPoster(null)}
        maxWidth="4xl"
        title={previewPoster?.campaign_product || 'Generated Poster'}
      >
        {previewPoster && (
          <div className="flex flex-col items-center justify-center p-2">
            <img
              src={formatMediaUrl(previewPoster.media_url)}
              alt="Full preview"
              className="max-h-[70vh] w-auto rounded-xl object-contain shadow-2xl"
            />
            {previewPoster.prompt && (
              <p className="mt-4 text-xs text-slate-400 text-center max-w-xl">
                Prompt: {previewPoster.prompt}
              </p>
            )}
            <div className="mt-4 flex gap-4">
              <a
                href={formatMediaUrl(previewPoster.media_url)}
                download="poster.png"
                target="_blank"
                rel="noreferrer"
              >
                <Button variant="primary" leftIcon={<Download className="w-4 h-4" />}>
                  Download Poster
                </Button>
              </a>
              <Button variant="outline" onClick={() => setPreviewPoster(null)}>
                Close
              </Button>
            </div>
          </div>
        )}
      </Modal>

      {/* Video Modal */}
      <Modal
        isOpen={!!previewVideo}
        onClose={() => setPreviewVideo(null)}
        maxWidth="4xl"
        title={previewVideo?.campaign_product || 'Commercial Video Preview'}
      >
        {previewVideo && (
          <div className="space-y-4">
            <div className="aspect-video w-full bg-slate-950 rounded-xl overflow-hidden flex items-center justify-center">
              <video
                controls
                autoPlay
                src={formatMediaUrl(previewVideo.media_url)}
                className="w-full h-full object-contain"
              />
            </div>
            <div className="flex justify-end gap-3">
              <a
                href={formatMediaUrl(previewVideo.media_url)}
                download="video.mp4"
                target="_blank"
                rel="noreferrer"
              >
                <Button variant="primary" leftIcon={<Download className="w-4 h-4" />}>
                  Download Video
                </Button>
              </a>
              <Button variant="outline" onClick={() => setPreviewVideo(null)}>
                Close
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
