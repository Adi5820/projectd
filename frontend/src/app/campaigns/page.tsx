'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  Megaphone,
  PlusCircle,
  Search,
  Clock,
  ArrowRight,
  Filter,
  Sparkles,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/shared/EmptyState';
import { CampaignGridSkeleton } from '@/components/shared/LoadingStates';
import { getCampaigns } from '@/lib/api';
import { Campaign } from '@/lib/types';
import { formatDate } from '@/lib/utils';

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  useEffect(() => {
    loadCampaigns();
  }, []);

  const loadCampaigns = async () => {
    try {
      setIsLoading(true);
      const data = await getCampaigns(0, 100);
      setCampaigns(data || []);
    } catch (err) {
      setCampaigns([]);
    } finally {
      setIsLoading(false);
    }
  };

  const filteredCampaigns = campaigns.filter((c) => {
    const matchesSearch =
      c.brand_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.product_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (c.industry && c.industry.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesStatus =
      statusFilter === 'all' || c.status.toLowerCase() === statusFilter.toLowerCase();

    return matchesSearch && matchesStatus;
  });

  return (
    <div className="flex-1 p-6 md:p-10 space-y-8 max-w-7xl mx-auto w-full">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-white">
            Campaigns
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Manage your AI advertising campaigns and generated assets
          </p>
        </div>
        <Link href="/campaigns/new">
          <Button variant="primary" leftIcon={<PlusCircle className="w-4 h-4" />}>
            New Campaign
          </Button>
        </Link>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center gap-4">
        <div className="relative flex-1 w-full">
          <Input
            placeholder="Search by brand name, product, or industry..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            leftIcon={<Search className="w-4 h-4" />}
          />
        </div>
        <div className="flex items-center gap-2 self-start sm:self-auto shrink-0">
          <Filter className="w-4 h-4 text-slate-400" />
          <div className="inline-flex rounded-lg bg-slate-900 border border-slate-800 p-1 text-xs">
            {['all', 'completed', 'running', 'draft'].map((status) => (
              <button
                key={status}
                type="button"
                onClick={() => setStatusFilter(status)}
                className={`px-3 py-1 rounded-md font-medium capitalize transition-colors ${
                  statusFilter === status
                    ? 'bg-indigo-600 text-white shadow'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {status}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Campaign Cards Grid */}
      {isLoading ? (
        <CampaignGridSkeleton count={6} />
      ) : filteredCampaigns.length === 0 ? (
        searchQuery || statusFilter !== 'all' ? (
          <EmptyState
            title="No matching campaigns"
            description={`No campaigns matched "${searchQuery || statusFilter}". Try adjusting your filters.`}
            actionLabel="Clear Filters"
            onAction={() => {
              setSearchQuery('');
              setStatusFilter('all');
            }}
          />
        ) : (
          <EmptyState
            icon={Megaphone}
            title="No campaigns yet"
            description="Create your first campaign to generate high-performing ad copy, promotional posters, and video ads."
            actionLabel="Create Campaign"
            onAction={() => {
              window.location.href = '/campaigns/new';
            }}
            actionIcon={<PlusCircle className="w-4 h-4" />}
          />
        )
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredCampaigns.map((c) => (
            <Link key={c.id} href={`/campaigns/${c.id}`} className="group">
              <Card
                hoverEffect
                className="h-full border-slate-800 bg-slate-900/60 p-6 flex flex-col justify-between"
              >
                <div className="space-y-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <span className="text-[11px] font-bold uppercase tracking-wider text-indigo-400">
                        {c.brand_name}
                      </span>
                      <h3 className="text-lg font-bold text-white group-hover:text-cyan-300 transition-colors mt-0.5 line-clamp-1">
                        {c.product_name}
                      </h3>
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

                  <p className="text-xs text-slate-300 line-clamp-2 leading-relaxed">
                    {c.product_description}
                  </p>

                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {c.platforms?.map((plat) => (
                      <Badge
                        key={plat}
                        platform={plat}
                        variant="outline"
                        className="text-[10px]"
                      />
                    ))}
                  </div>
                </div>

                <div className="pt-5 mt-5 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
                  <div className="flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5 text-slate-500" />
                    <span>{formatDate(c.created_at)}</span>
                  </div>
                  <span className="inline-flex items-center gap-1 font-medium text-indigo-400 group-hover:translate-x-1 transition-transform">
                    View Results <ArrowRight className="w-3.5 h-3.5" />
                  </span>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
