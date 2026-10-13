'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Sparkles,
  ArrowRight,
  ArrowLeft,
  Check,
  Building2,
  Target,
  Share2,
  Settings2,
  CheckCircle2,
  Instagram,
  Twitter,
  Linkedin,
  Youtube,
  Radio,
  Globe,
  Loader2,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { Select } from '@/components/ui/Select';
import { Card } from '@/components/ui/Card';
import { createCampaign } from '@/lib/api';
import { CampaignCreate } from '@/lib/types';

interface FormData {
  brand_name: string;
  product_name: string;
  product_description: string;
  industry: string;
  campaign_goal: string;
  target_audience: string;
  tone: string;
  platforms: string[];
  language: string;
  additional_context: string;
}

const initialFormData: FormData = {
  brand_name: '',
  product_name: '',
  product_description: '',
  industry: 'Technology',
  campaign_goal: 'brand_awareness',
  target_audience: '',
  tone: 'professional',
  platforms: ['instagram', 'facebook', 'twitter'],
  language: 'English',
  additional_context: '',
};

const steps = [
  { id: 1, title: 'Brand Info', icon: Building2 },
  { id: 2, title: 'Goals & Tone', icon: Target },
  { id: 3, title: 'Platforms', icon: Share2 },
  { id: 4, title: 'Details', icon: Settings2 },
  { id: 5, title: 'Review & Launch', icon: CheckCircle2 },
];

const availablePlatforms = [
  { id: 'instagram', name: 'Instagram', icon: Instagram, color: 'text-pink-400' },
  { id: 'facebook', name: 'Facebook', icon: Share2, color: 'text-blue-500' },
  { id: 'twitter', name: 'Twitter / X', icon: Twitter, color: 'text-sky-400' },
  { id: 'linkedin', name: 'LinkedIn', icon: Linkedin, color: 'text-blue-400' },
  { id: 'youtube', name: 'YouTube', icon: Youtube, color: 'text-red-500' },
  { id: 'tiktok', name: 'TikTok', icon: Radio, color: 'text-teal-400' },
  { id: 'google_ads', name: 'Google Ads', icon: Globe, color: 'text-amber-400' },
];

export default function NewCampaignPage() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [formData, setFormData] = useState<FormData>(initialFormData);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validateStep = (step: number): boolean => {
    const errs: Record<string, string> = {};

    if (step === 1) {
      if (!formData.brand_name.trim()) errs.brand_name = 'Brand name is required';
      if (!formData.product_name.trim()) errs.product_name = 'Product name is required';
      if (!formData.product_description.trim())
        errs.product_description = 'Product description is required';
    }

    if (step === 2) {
      if (!formData.target_audience.trim())
        errs.target_audience = 'Target audience description is required';
    }

    if (step === 3) {
      if (formData.platforms.length === 0)
        errs.platforms = 'Select at least one platform for the campaign';
    }

    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleNext = () => {
    if (validateStep(currentStep)) {
      setCurrentStep((prev) => Math.min(prev + 1, steps.length));
    }
  };

  const handleBack = () => {
    setCurrentStep((prev) => Math.max(prev - 1, 1));
  };

  const togglePlatform = (platformId: string) => {
    setFormData((prev) => {
      const exists = prev.platforms.includes(platformId);
      const updated = exists
        ? prev.platforms.filter((p) => p !== platformId)
        : [...prev.platforms, platformId];
      return { ...prev, platforms: updated };
    });
  };

  const handleSubmit = async () => {
    try {
      setIsSubmitting(true);
      const campaignPayload: CampaignCreate = {
        brand_name: formData.brand_name,
        product_name: formData.product_name,
        product_description: formData.product_description,
        industry: formData.industry,
        campaign_goal: formData.campaign_goal,
        target_audience: formData.target_audience,
        tone: formData.tone,
        platforms: formData.platforms,
        language: formData.language,
        additional_context: formData.additional_context,
      };

      const result = await createCampaign(campaignPayload);
      router.push(`/campaigns/${result.id}`);
    } catch (err: any) {
      setErrors({ submit: err.message || 'Failed to create campaign' });
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex-1 p-6 md:p-10 space-y-8 max-w-4xl mx-auto w-full">
      {/* Page Title */}
      <div>
        <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-white flex items-center gap-2.5">
          <Sparkles className="w-6 h-6 text-indigo-400" />
          Create New Campaign
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Configure your autonomous marketing campaign parameters
        </p>
      </div>

      {/* Step Indicators */}
      <div className="flex items-center justify-between relative px-2">
        <div className="absolute top-1/2 left-0 right-0 h-0.5 bg-slate-800 -translate-y-1/2 z-0" />
        {steps.map((s) => {
          const Icon = s.icon;
          const isDone = s.id < currentStep;
          const isCurrent = s.id === currentStep;

          return (
            <div key={s.id} className="relative z-10 flex flex-col items-center">
              <button
                type="button"
                onClick={() => {
                  if (s.id < currentStep) setCurrentStep(s.id);
                }}
                className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-xs transition-all duration-300 ${
                  isDone
                    ? 'bg-emerald-500 text-slate-950 shadow-md shadow-emerald-500/20'
                    : isCurrent
                    ? 'bg-gradient-to-r from-indigo-500 to-cyan-500 text-white ring-4 ring-indigo-500/20 shadow-lg'
                    : 'bg-slate-900 border border-slate-800 text-slate-400'
                }`}
              >
                {isDone ? <Check className="w-4 h-4 stroke-[3]" /> : <Icon className="w-4 h-4" />}
              </button>
              <span
                className={`text-[11px] font-medium mt-2 hidden sm:block ${
                  isCurrent ? 'text-cyan-300 font-semibold' : 'text-slate-400'
                }`}
              >
                {s.title}
              </span>
            </div>
          );
        })}
      </div>

      {/* Step Content */}
      <Card className="p-6 md:p-8 border-slate-800 bg-slate-900/70">
        {/* Step 1: Brand Info */}
        {currentStep === 1 && (
          <div className="space-y-6 animate-in fade-in duration-200">
            <div>
              <h2 className="text-xl font-bold text-white">Brand & Product Details</h2>
              <p className="text-xs text-slate-400 mt-1">
                Provide basic information about your company and the product you are promoting.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              <Input
                label="Brand Name"
                placeholder="e.g. ApexGear, Lumina Health"
                value={formData.brand_name}
                onChange={(e) => setFormData({ ...formData, brand_name: e.target.value })}
                error={errors.brand_name}
                required
              />

              <Input
                label="Product Name"
                placeholder="e.g. CloudPulse Pro, HydroFlow 2.0"
                value={formData.product_name}
                onChange={(e) => setFormData({ ...formData, product_name: e.target.value })}
                error={errors.product_name}
                required
              />
            </div>

            <Textarea
              label="Product Description & Value Proposition"
              placeholder="Explain what the product does, key features, pricing advantage, and problem solved..."
              rows={4}
              value={formData.product_description}
              onChange={(e) =>
                setFormData({ ...formData, product_description: e.target.value })
              }
              error={errors.product_description}
              required
            />

            <Select
              label="Industry / Domain"
              value={formData.industry}
              onChange={(e) => setFormData({ ...formData, industry: e.target.value })}
              options={[
                { value: 'Technology', label: 'Technology / SaaS' },
                { value: 'E-commerce', label: 'E-commerce & Retail' },
                { value: 'Health & Wellness', label: 'Health & Wellness' },
                { value: 'Finance & Fintech', label: 'Finance & Fintech' },
                { value: 'Education', label: 'Education & EdTech' },
                { value: 'Travel & Hospitality', label: 'Travel & Hospitality' },
                { value: 'Entertainment & Gaming', label: 'Entertainment & Gaming' },
                { value: 'Automotive', label: 'Automotive' },
                { value: 'Real Estate', label: 'Real Estate' },
              ]}
            />
          </div>
        )}

        {/* Step 2: Campaign Goals */}
        {currentStep === 2 && (
          <div className="space-y-6 animate-in fade-in duration-200">
            <div>
              <h2 className="text-xl font-bold text-white">Campaign Goals & Target Audience</h2>
              <p className="text-xs text-slate-400 mt-1">
                Align AI copy and visuals with your specific marketing objective.
              </p>
            </div>

            <div className="space-y-2">
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300">
                Primary Campaign Goal
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {[
                  { id: 'brand_awareness', label: 'Brand Awareness', desc: 'Maximize reach and impressions' },
                  { id: 'lead_generation', label: 'Lead Generation', desc: 'Capture signups and inquiries' },
                  { id: 'sales_conversion', label: 'Direct Sales', desc: 'Drive checkouts and purchases' },
                  { id: 'website_traffic', label: 'Traffic Growth', desc: 'Funnel visitors to landing page' },
                  { id: 'engagement', label: 'User Engagement', desc: 'Boost social interactions and shares' },
                ].map((goal) => (
                  <div
                    key={goal.id}
                    onClick={() => setFormData({ ...formData, campaign_goal: goal.id })}
                    className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                      formData.campaign_goal === goal.id
                        ? 'border-indigo-500 bg-indigo-500/10 text-white shadow-md shadow-indigo-500/10'
                        : 'border-slate-800 bg-slate-900/50 text-slate-400 hover:border-slate-700'
                    }`}
                  >
                    <div className="text-sm font-semibold">{goal.label}</div>
                    <div className="text-[11px] text-slate-400 mt-1">{goal.desc}</div>
                  </div>
                ))}
              </div>
            </div>

            <Textarea
              label="Target Audience Demographics & Persona"
              placeholder="e.g. Remote software engineers aged 25-45, tech leads, tech-savvy founders who value productivity..."
              rows={3}
              value={formData.target_audience}
              onChange={(e) =>
                setFormData({ ...formData, target_audience: e.target.value })
              }
              error={errors.target_audience}
              required
            />

            <Select
              label="Tone of Voice"
              value={formData.tone}
              onChange={(e) => setFormData({ ...formData, tone: e.target.value })}
              options={[
                { value: 'professional', label: 'Professional & Authoritative' },
                { value: 'casual', label: 'Casual & Conversational' },
                { value: 'inspirational', label: 'Inspirational & Motivating' },
                { value: 'humorous', label: 'Humorous & Witty' },
                { value: 'urgent', label: 'Urgent & Action-Oriented (FOMO)' },
                { value: 'luxury', label: 'Luxury & Sophisticated' },
                { value: 'playful', label: 'Playful & Creative' },
              ]}
            />
          </div>
        )}

        {/* Step 3: Platform Selection */}
        {currentStep === 3 && (
          <div className="space-y-6 animate-in fade-in duration-200">
            <div>
              <h2 className="text-xl font-bold text-white">Select Target Channels</h2>
              <p className="text-xs text-slate-400 mt-1">
                Choose the digital platforms to generate tailored copy lengths, hashtags, and aspect ratios for.
              </p>
            </div>

            {errors.platforms && (
              <p className="text-xs text-rose-400">{errors.platforms}</p>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
              {availablePlatforms.map((plat) => {
                const Icon = plat.icon;
                const isSelected = formData.platforms.includes(plat.id);

                return (
                  <div
                    key={plat.id}
                    onClick={() => togglePlatform(plat.id)}
                    className={`flex items-center justify-between p-4 rounded-xl border cursor-pointer select-none transition-all ${
                      isSelected
                        ? 'border-indigo-500 bg-indigo-500/10 shadow-sm'
                        : 'border-slate-800 bg-slate-900/40 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-lg bg-slate-800/80 ${plat.color}`}>
                        <Icon className="w-5 h-5" />
                      </div>
                      <span className="text-sm font-semibold text-white">
                        {plat.name}
                      </span>
                    </div>
                    <div
                      className={`w-5 h-5 rounded-md flex items-center justify-center border transition-colors ${
                        isSelected
                          ? 'bg-indigo-600 border-indigo-500 text-white'
                          : 'border-slate-700 bg-slate-800'
                      }`}
                    >
                      {isSelected && <Check className="w-3.5 h-3.5 stroke-[3]" />}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Step 4: Additional Details */}
        {currentStep === 4 && (
          <div className="space-y-6 animate-in fade-in duration-200">
            <div>
              <h2 className="text-xl font-bold text-white">Language & Additional Context</h2>
              <p className="text-xs text-slate-400 mt-1">
                Provide custom guidelines or restrictions for the AI generation agents.
              </p>
            </div>

            <Select
              label="Primary Language"
              value={formData.language}
              onChange={(e) => setFormData({ ...formData, language: e.target.value })}
              options={[
                { value: 'English', label: 'English (US / Global)' },
                { value: 'Spanish', label: 'Spanish' },
                { value: 'French', label: 'French' },
                { value: 'German', label: 'German' },
                { value: 'Japanese', label: 'Japanese' },
                { value: 'Hindi', label: 'Hindi' },
                { value: 'Portuguese', label: 'Portuguese' },
              ]}
            />

            <Textarea
              label="Special Constraints or Context (Optional)"
              placeholder="e.g. Include holiday 20% discount code 'SAVE20', mention free 14-day trial, avoid mention of competitors..."
              rows={4}
              value={formData.additional_context}
              onChange={(e) =>
                setFormData({ ...formData, additional_context: e.target.value })
              }
              helperText="Instructions passed into agent prompts for ad copy and video script generation."
            />
          </div>
        )}

        {/* Step 5: Review & Submit */}
        {currentStep === 5 && (
          <div className="space-y-6 animate-in fade-in duration-200">
            <div>
              <h2 className="text-xl font-bold text-white">Review Campaign Specs</h2>
              <p className="text-xs text-slate-400 mt-1">
                Confirm your configuration before initiating autonomous generation.
              </p>
            </div>

            {errors.submit && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs">
                {errors.submit}
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
                <span className="text-slate-500 font-semibold uppercase">Brand & Product</span>
                <div className="text-sm font-bold text-white">{formData.brand_name}</div>
                <div className="text-slate-300 font-medium">{formData.product_name}</div>
                <div className="text-slate-400 mt-1">{formData.product_description}</div>
              </div>

              <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
                <span className="text-slate-500 font-semibold uppercase">Strategy & Persona</span>
                <div className="flex items-center gap-2">
                  <span className="text-slate-400">Goal:</span>
                  <span className="font-semibold text-cyan-400 capitalize">
                    {formData.campaign_goal.replace('_', ' ')}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-slate-400">Tone:</span>
                  <span className="font-semibold text-indigo-400 capitalize">
                    {formData.tone}
                  </span>
                </div>
                <div className="text-slate-400 mt-1">
                  <strong>Audience:</strong> {formData.target_audience}
                </div>
              </div>

              <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2 md:col-span-2">
                <span className="text-slate-500 font-semibold uppercase">Active Channels</span>
                <div className="flex flex-wrap gap-2 mt-1">
                  {formData.platforms.map((p) => (
                    <span
                      key={p}
                      className="px-2.5 py-1 rounded-md bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 font-medium capitalize"
                    >
                      {p.replace('_', ' ')}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Bottom Navigation Buttons */}
        <div className="flex items-center justify-between pt-6 mt-6 border-t border-slate-800/80">
          {currentStep > 1 ? (
            <Button
              type="button"
              variant="outline"
              onClick={handleBack}
              leftIcon={<ArrowLeft className="w-4 h-4" />}
            >
              Back
            </Button>
          ) : (
            <div />
          )}

          {currentStep < steps.length ? (
            <Button
              type="button"
              variant="primary"
              onClick={handleNext}
              rightIcon={<ArrowRight className="w-4 h-4" />}
            >
              Continue
            </Button>
          ) : (
            <Button
              type="button"
              variant="primary"
              onClick={handleSubmit}
              isLoading={isSubmitting}
              leftIcon={<Sparkles className="w-4 h-4" />}
            >
              Launch Campaign
            </Button>
          )}
        </div>
      </Card>
    </div>
  );
}
