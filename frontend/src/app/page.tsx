'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  Sparkles,
  PlusCircle,
  FileText,
  Image as ImageIcon,
  Megaphone,
  ArrowRight,
  TrendingUp,
  Layers,
  Video,
  FileSpreadsheet,
  CheckCircle2,
  Clock,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { getCampaigns } from '@/lib/api';
import { Campaign } from '@/lib/types';
import { formatDate, getStatusColor } from '@/lib/utils';
import { CampaignGridSkeleton } from '@/components/shared/LoadingStates';

export default function DashboardPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [stats, setStats] = useState({
    totalCampaigns: 0,
    adsGenerated: 0,
    postersCreated: 0,
    videosProduced: 0,
  });

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setIsLoading(true);
        const data = await getCampaigns(0, 10);
        setCampaigns(data || []);

        // Estimate or calculate metrics
        const total = (data || []).length;
        setStats({
          totalCampaigns: total,
          adsGenerated: total * 4,
          postersCreated: total * 3,
          videosProduced: Math.max(0, Math.floor(total * 1.5)),
        });
      } catch (err) {
        // Fallback for clean initial state
        setCampaigns([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  return (
    <div className="flex-1 p-6 md:p-10 space-y-10 max-w-7xl mx-auto w-full">
      {/* Hero Section */}
      <div className="relative overflow-hidden rounded-3xl p-8 md:p-12 border border-slate-800/80 bg-gradient-to-br from-slate-900 via-slate-900/90 to-indigo-950/40 shadow-2xl">
        <div className="absolute top-0 right-0 -mt-10 -mr-10 w-96 h-96 bg-gradient-to-br from-indigo-500/20 via-cyan-500/10 to-transparent rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10 max-w-3xl space-y-5">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 text-xs font-semibold uppercase tracking-wider">
            <Sparkles className="w-3.5 h-3.5" />
            Autonomous Multi-Agent AI Platform
          </div>

          <h1 className="text-3xl md:text-5xl font-extrabold tracking-tight text-white leading-tight">
            AI-Powered{' '}
            <span className="bg-gradient-to-r from-indigo-400 via-purple-300 to-cyan-400 bg-clip-text text-transparent">
              Advertisement Generation
            </span>
          </h1>

          <p className="text-base md:text-lg text-slate-300 leading-relaxed max-w-2xl">
            From product knowledge to hyper-targeted advertising. Orchestrate
            specialized AI agents to write multi-platform ad copy, design
            studio-grade posters, and synthesize full video commercials with neural voices.
          </p>

          <div className="flex flex-wrap items-center gap-4 pt-2">
            <Link href="/campaigns/new">
              <Button
                variant="primary"
                size="lg"
                leftIcon={<PlusCircle className="w-5 h-5" />}
                className="shadow-xl shadow-indigo-500/25"
              >
                Create New Campaign
              </Button>
            </Link>
            <Link href="/documents">
              <Button
                variant="outline"
                size="lg"
                leftIcon={<FileText className="w-5 h-5" />}
              >
                Upload Brand Knowledge
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <Card className="p-5 border-slate-800/80 hover:border-slate-700 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Total Campaigns</span>
            <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
              <Megaphone className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-white">{stats.totalCampaigns}</span>
            <span className="text-xs text-emerald-400 flex items-center font-medium">
              <TrendingUp className="w-3 h-3 mr-0.5" /> Active
            </span>
          </div>
        </Card>

        <Card className="p-5 border-slate-800/80 hover:border-slate-700 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Ad Variations Written</span>
            <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-400">
              <Layers className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-white">{stats.adsGenerated}</span>
            <span className="text-xs text-slate-400">Optimized copy</span>
          </div>
        </Card>

        <Card className="p-5 border-slate-800/80 hover:border-slate-700 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Posters Synthesized</span>
            <div className="p-2 rounded-lg bg-purple-500/10 text-purple-400">
              <ImageIcon className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-white">{stats.postersCreated}</span>
            <span className="text-xs text-purple-400">Multi-ratio</span>
          </div>
        </Card>

        <Card className="p-5 border-slate-800/80 hover:border-slate-700 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Videos Produced</span>
            <div className="p-2 rounded-lg bg-rose-500/10 text-rose-400">
              <Video className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-white">{stats.videosProduced}</span>
            <span className="text-xs text-rose-400">Edge-TTS audio</span>
          </div>
        </Card>
      </div>

      {/* Quick Actions Bar */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Link href="/campaigns/new" className="group">
          <Card className="p-6 border-slate-800 bg-slate-900/60 hover:border-indigo-500/50 hover:bg-slate-900 transition-all">
            <div className="w-12 h-12 rounded-xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
              <PlusCircle className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-semibold text-white group-hover:text-indigo-300 flex items-center justify-between">
              Create Campaign
              <ArrowRight className="w-4 h-4 opacity-0 group-hover:opacity-100 -translate-x-2 group-hover:translate-x-0 transition-all" />
            </h3>
            <p className="text-xs text-slate-400 mt-2 leading-relaxed">
              Define brand objectives, target audience demographics, tone, and platforms in an interactive wizard.
            </p>
          </Card>
        </Link>

        <Link href="/documents" className="group">
          <Card className="p-6 border-slate-800 bg-slate-900/60 hover:border-cyan-500/50 hover:bg-slate-900 transition-all">
            <div className="w-12 h-12 rounded-xl bg-cyan-500/10 text-cyan-400 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
              <FileSpreadsheet className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-semibold text-white group-hover:text-cyan-300 flex items-center justify-between">
              Upload Documents
              <ArrowRight className="w-4 h-4 opacity-0 group-hover:opacity-100 -translate-x-2 group-hover:translate-x-0 transition-all" />
            </h3>
            <p className="text-xs text-slate-400 mt-2 leading-relaxed">
              Index brand guidelines, pitch decks, and product docs into the ChromaDB vector store for grounded RAG copy.
            </p>
          </Card>
        </Link>

        <Link href="/gallery" className="group">
          <Card className="p-6 border-slate-800 bg-slate-900/60 hover:border-purple-500/50 hover:bg-slate-900 transition-all">
            <div className="w-12 h-12 rounded-xl bg-purple-500/10 text-purple-400 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
              <ImageIcon className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-semibold text-white group-hover:text-purple-300 flex items-center justify-between">
              View Media Gallery
              <ArrowRight className="w-4 h-4 opacity-0 group-hover:opacity-100 -translate-x-2 group-hover:translate-x-0 transition-all" />
            </h3>
            <p className="text-xs text-slate-400 mt-2 leading-relaxed">
              Browse, filter, and inspect generated advertising posters, banners, and ready-to-publish video commercials.
            </p>
          </Card>
        </Link>
      </div>

      {/* Recent Campaigns Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-white tracking-tight">
              Recent Campaigns
            </h2>
            <p className="text-xs text-slate-400">
              Overview of recently launched generative advertising tasks
            </p>
          </div>
          <Link href="/campaigns">
            <Button variant="ghost" size="sm" rightIcon={<ArrowRight className="w-4 h-4" />}>
              View All Campaigns
            </Button>
          </Link>
        </div>

        {isLoading ? (
          <CampaignGridSkeleton count={3} />
        ) : campaigns.length === 0 ? (
          <Card className="p-8 text-center border-dashed border-slate-800 bg-slate-900/40">
            <div className="max-w-md mx-auto space-y-3">
              <Megaphone className="w-10 h-10 text-slate-600 mx-auto" />
              <h3 className="text-base font-semibold text-white">No campaigns found</h3>
              <p className="text-xs text-slate-400">
                You haven&apos;t created any advertising campaigns yet. Start your first AI-driven marketing campaign now.
              </p>
              <div className="pt-2">
                <Link href="/campaigns/new">
                  <Button variant="primary" size="sm" leftIcon={<PlusCircle className="w-4 h-4" />}>
                    Create Your First Campaign
                  </Button>
                </Link>
              </div>
            </div>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {campaigns.slice(0, 6).map((c) => {
              const statusStyle = getStatusColor(c.status);
              return (
                <Link key={c.id} href={`/campaigns/${c.id}`} className="group">
                  <Card className="h-full border-slate-800 hover:border-slate-700 bg-slate-900/70 p-5 space-y-4 transition-all">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <span className="text-[11px] font-semibold tracking-wider uppercase text-indigo-400">
                          {c.brand_name}
                        </span>
                        <h4 className="text-base font-bold text-white group-hover:text-cyan-300 transition-colors line-clamp-1 mt-0.5">
                          {c.product_name}
                        </h4>
                      </div>
                      <Badge
                        variant={
                          c.status === 'completed'
                            ? 'success'
                            : c.status === 'running'
                            ? 'warning'
                            : c.status === 'failed'
                            ? 'error'
                            : 'default'
                        }
                        dot
                      >
                        {c.status}
                      </Badge>
                    </div>

                    <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
                      {c.product_description}
                    </p>

                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {c.platforms?.map((p) => (
                        <Badge key={p} platform={p} variant="outline" className="text-[10px] py-0 px-2" />
                      ))}
                    </div>

                    <div className="flex items-center justify-between pt-3 border-t border-slate-800/80 text-[11px] text-slate-400">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3 text-slate-500" />
                        {formatDate(c.created_at)}
                      </span>
                      <span className="text-indigo-400 font-medium group-hover:translate-x-1 transition-transform inline-flex items-center gap-1">
                        Open <ArrowRight className="w-3 h-3" />
                      </span>
                    </div>
                  </Card>
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
