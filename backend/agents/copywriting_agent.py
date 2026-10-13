"""
Advertisement Copywriting Agent for Agentic Ads Platform.

Generates high-converting, platform-optimized ad copy variations
tailored for Instagram, YouTube, Facebook, Twitter/X, and LinkedIn,
leveraging brand guidelines, strategic selling points, and audience psychology.
"""

from __future__ import annotations

import time
from typing import Any, Optional, Union

from pydantic import BaseModel, Field
import structlog

from backend.agents.base import BaseAgent


class AdVariation(BaseModel):
    """Structured advertising copy variation."""

    headline: str = Field(
        description="High-impact, attention-grabbing headline designed to stop scrolling",
    )
    description: str = Field(
        description="Persuasive body copy detailing value proposition, benefits, and proof",
    )
    caption: str = Field(
        description="Platform-native social caption formatted with spacing and tone",
    )
    hashtags: list[str] = Field(
        default_factory=list,
        description="Curated list of hashtags (platform-calibrated quantity and style)",
    )
    call_to_action: str = Field(
        description="Unambiguous, urgent Call To Action (e.g., 'Claim Your 20% Off', 'Shop Now')",
    )
    slogan: str = Field(
        description="Memorable campaign slogan or tagline encapsulating the core brand promise",
    )


class PlatformCopyResult(BaseModel):
    """Container for copy variations tailored to a specific platform."""

    platform: str = Field(
        description="Target social media or ad network channel",
    )
    tone_analysis: str = Field(
        description="Diagnostic breakdown of tone modulation, voice nuance, and psychological hooks",
    )
    variations: list[AdVariation] = Field(
        description="List of distinct creative variations (angles: direct-response, emotional, social proof)",
    )


class CopywritingAgent(BaseAgent):
    """
    Advertisement Copywriting Agent.

    Crafts platform-native ad variations embodying different psychological angles:
    1. Pain-Point & Agitation Solution
    2. Aspirational Transformation & Social Proof
    3. Direct-Response Offer & Feature Showcase
    """

    def __init__(self, llm_provider: Optional[Any] = None) -> None:
        """Initialize the Copywriting Agent."""
        super().__init__(name="copywriting_agent", llm_provider=llm_provider)

    def _build_system_prompt(self) -> str:
        """
        Build a world-class advertising copywriter system prompt.

        Returns:
            str: Comprehensive copywriting instructions.
        """
        return (
            "You are a legendary Direct-Response Advertising Copywriter and Creative Director, "
            "combining the psychological acumen of David Ogilvy, Eugene Schwartz, and Gary Halbert "
            "with the algorithm-mastery of top contemporary social growth marketers.\n\n"
            "Your copy produces massive click-through rates, viral social engagement, and high-ROI conversions. "
            "You never write boring, generic, or passive copy. Every word is deliberate, punchy, and active.\n\n"
            "PLATFORM OPTIMIZATION PROTOCOLS:\n"
            "1. INSTAGRAM:\n"
            "   - Hook in the very first line (before the '...more' truncation).\n"
            "   - Emojis used strategically as visual bullet points.\n"
            "   - 10-15 targeted, relevant hashtags combining niche tags and broad category tags.\n"
            "   - Visual lifestyle storytelling, aspirational tone.\n\n"
            "2. YOUTUBE:\n"
            "   - High-CTR, curiosity-inducing headlines under 70 characters.\n"
            "   - Keyword-dense, SEO-rich descriptions optimized for YouTube search.\n"
            "   - Structured timestamp-friendly outlines and pinned-comment-ready CTAs.\n\n"
            "3. FACEBOOK:\n"
            "   - Community and conversation-focused copy.\n"
            "   - Story-driven formats that prompt shares and comments ('Drop a comment if...').\n"
            "   - Emotional hooks, relatable everyday dilemmas, and strong social proof.\n\n"
            "4. TWITTER / X:\n"
            "   - Extreme brevity and punchiness; fit within 280 characters for primary copy.\n"
            "   - Bold statements, counter-intuitive insights, high-contrast framing.\n"
            "   - Strict limit of 1 to 3 impactful hashtags.\n\n"
            "5. LINKEDIN:\n"
            "   - Professional, authoritative B2B tone.\n"
            "   - High emphasis on business ROI, productivity gains, industry leadership, and career growth.\n"
            "   - Clean line breaks for skim-reading, minimal emojis, 3-5 industry hashtags.\n\n"
            "Always output creative variations that explore distinctly different angles rather than minor rewording."
        )

    def _normalize_campaign_input(self, campaign_data: Any) -> dict[str, Any]:
        """Normalize arbitrary campaign data into a dictionary."""
        if isinstance(campaign_data, dict):
            return dict(campaign_data)
        if hasattr(campaign_data, "model_dump") and callable(campaign_data.model_dump):
            return campaign_data.model_dump()
        if hasattr(campaign_data, "dict") and callable(campaign_data.dict):
            return campaign_data.dict()
        if hasattr(campaign_data, "__dict__"):
            return {k: v for k, v in campaign_data.__dict__.items() if not k.startswith("_")}
        return {"raw": str(campaign_data)}

    async def _generate_platform_copy(
        self,
        platform: str,
        brand_name: str,
        product_name: str,
        brief: str,
        campaign_understanding: dict[str, Any],
        brand_context: dict[str, Any],
        num_variations: int,
    ) -> PlatformCopyResult:
        """
        Generate copy variations for a single specified platform.

        Args:
            platform: Platform name (instagram, youtube, facebook, twitter, linkedin).
            brand_name: Brand name.
            product_name: Product name.
            brief: Campaign brief.
            campaign_understanding: Strategy dictionary.
            brand_context: Brand guidelines dictionary.
            num_variations: Number of variations to create.

        Returns:
            PlatformCopyResult: Structured copy result for the platform.
        """
        ksps = campaign_understanding.get("key_selling_points", [])
        positioning = campaign_understanding.get("competitive_positioning", "")
        emotional_appeal = campaign_understanding.get("emotional_appeal", "")
        plat_strategy = campaign_understanding.get("platform_specific_strategy", {}).get(platform, "")

        brand_voice = brand_context.get("brand_voice", "Confident, modern, compelling")
        brand_guidelines = brand_context.get("brand_guidelines", "")

        user_prompt = (
            f"Generate {num_variations} distinct, top-performing ad copy variations for platform '{platform.upper()}':\n\n"
            f"BRAND: {brand_name}\n"
            f"PRODUCT: {product_name}\n"
            f"BRIEF / OBJECTIVE: {brief}\n"
            f"BRAND VOICE: {brand_voice}\n"
            f"BRAND GUIDELINES: {brand_guidelines[:300]}\n"
            f"COMPETITIVE POSITIONING: {positioning}\n"
            f"EMOTIONAL APPEAL: {emotional_appeal}\n"
            f"KEY SELLING POINTS: {ksps}\n"
            f"PLATFORM STRATEGY: {plat_strategy}\n\n"
            f"Requirements:\n"
            f"- Generate exactly {num_variations} variations.\n"
            f"- Variation 1: Direct-response benefit hook & problem-solution.\n"
            f"- Variation 2: Emotional transformation & lifestyle aspiration.\n"
            f"- Variation 3: Social proof, authority, or compelling urgency.\n"
            f"- Provide tone_analysis explaining how voice and structure were tuned for {platform}.\n"
            f"- Strict compliance with platform rules (hashtags count, character limits, formatting)."
        )

        try:
            return await self._call_llm_structured(
                prompt=user_prompt,
                response_model=PlatformCopyResult,
            )
        except Exception as exc:
            self.logger.warning(
                "platform_copy_generation_failed_using_fallback",
                platform=platform,
                error=str(exc),
            )
            return self._build_fallback_platform_copy(
                platform=platform,
                brand_name=brand_name,
                product_name=product_name,
                brief=brief,
                num_variations=num_variations,
            )

    def _build_fallback_platform_copy(
        self,
        platform: str,
        brand_name: str,
        product_name: str,
        brief: str,
        num_variations: int = 3,
    ) -> PlatformCopyResult:
        """
        Generate high-quality heuristic copy variations if LLM call fails.

        Args:
            platform: Platform name.
            brand_name: Brand name.
            product_name: Product name.
            brief: Brief.
            num_variations: Number of variations.

        Returns:
            PlatformCopyResult: High quality fallback.
        """
        plat_lower = platform.lower()
        if "insta" in plat_lower:
            hashtags = [f"#{brand_name.replace(' ', '')}", f"#{product_name.replace(' ', '')}", "#Innovation", "#MustHave", "#DailyEssential", "#UpgradeYourLife"]
            variations = [
                AdVariation(
                    headline=f"Say Goodbye to Mediocrity. Meet {product_name}.",
                    description=f"Designed for those who refuse to settle. Experience unmatched quality with {brand_name}.",
                    caption=f"✨ Ready to transform your routine? {product_name} is finally here. Tap the link to elevate your standards today.",
                    hashtags=hashtags,
                    call_to_action="Shop Now & Save 15%",
                    slogan=f"{brand_name}: Redefining Excellence",
                ),
                AdVariation(
                    headline=f"The Upgrade You've Been Waiting For ✨",
                    description=f"Join thousands of satisfied customers who made the switch to {product_name}.",
                    caption=f"Once you try {product_name}, there's no going back. See what the buzz is all about! 👇",
                    hashtags=hashtags,
                    call_to_action="Get Yours Today",
                    slogan="Smarter Living, Effortless Quality",
                ),
                AdVariation(
                    headline=f"Engineered for Real Performance.",
                    description=f"Stop struggling with outdated alternatives. Discover how {brand_name} delivers real results.",
                    caption=f"Built with precision. Made for you. Explore {product_name} now. Link in bio! 🚀",
                    hashtags=hashtags,
                    call_to_action="Explore The Collection",
                    slogan="Precision That Speaks for Itself",
                ),
            ]
        elif "link" in plat_lower:
            hashtags = [f"#{brand_name.replace(' ', '')}", "#BusinessEfficiency", "#Leadership", "#Productivity"]
            variations = [
                AdVariation(
                    headline=f"How Modern Leaders Are Scaling Impact with {product_name}",
                    description=f"Efficiency isn't an accident—it's a deliberate choice. Learn how {brand_name} drives tangible ROI.",
                    caption=f"In today's fast-paced environment, marginal gains compound into massive advantages. Discover how {product_name} gives teams an unfair edge.",
                    hashtags=hashtags,
                    call_to_action="Request an Executive Demo",
                    slogan=f"{brand_name} | Driving Enterprise Excellence",
                ),
                AdVariation(
                    headline=f"Stop Wasting Resources on Outdated Systems",
                    description=f"Modernize your workflows and elevate quality benchmarks with {product_name}.",
                    caption=f"Category leaders don't compromise on tooling. Upgrade to {brand_name} and experience measurable gains.",
                    hashtags=hashtags,
                    call_to_action="Read the Case Study",
                    slogan="Smarter Infrastructure for Tomorrow",
                ),
                AdVariation(
                    headline=f"The Strategic Advantage: {product_name}",
                    description=f"Built for decision-makers who demand uncompromising performance.",
                    caption=f"Discover why forward-thinking organizations choose {brand_name} for mission-critical operations.",
                    hashtags=hashtags,
                    call_to_action="Download the Whitepaper",
                    slogan="Empowering the Next Generation of Industry",
                ),
            ]
        elif "twit" in plat_lower or "x" in plat_lower:
            hashtags = [f"#{brand_name.replace(' ', '')}", "#GameChanger"]
            variations = [
                AdVariation(
                    headline=f"{product_name} just raised the bar.",
                    description=f"Everything you wanted in one seamless package. From {brand_name}.",
                    caption=f"Most solutions complicate things. {product_name} makes them effortless. See for yourself: 👇",
                    hashtags=hashtags,
                    call_to_action="Learn More",
                    slogan="Simple. Powerful. Unstoppable.",
                ),
                AdVariation(
                    headline=f"The wait is officially over.",
                    description=f"Meet {product_name} by {brand_name}. Smarter, faster, better.",
                    caption=f"Ready for the upgrade you actually deserve? Link below.",
                    hashtags=hashtags,
                    call_to_action="Claim Your Offer",
                    slogan="Welcome to the Future.",
                ),
                AdVariation(
                    headline=f"Don't settle for less.",
                    description=f"Experience next-level craftsmanship with {product_name}.",
                    caption=f"The simplest way to upgrade your day. Get started now.",
                    hashtags=hashtags,
                    call_to_action="Get Started",
                    slogan="Better by Design.",
                ),
            ]
        else:
            hashtags = [f"#{brand_name.replace(' ', '')}", "#SpecialOffer", "#MustSee"]
            variations = [
                AdVariation(
                    headline=f"Experience the Difference with {product_name}",
                    description=f"Crafted by {brand_name} to deliver exceptional quality and reliability.",
                    caption=f"Thousands of happy users agree—{product_name} is the smart choice. Try it today risk-free!",
                    hashtags=hashtags,
                    call_to_action="Shop Now",
                    slogan=f"{brand_name}: Quality You Can Trust",
                ),
                AdVariation(
                    headline=f"Limited Time: Discover {product_name}",
                    description=f"Upgrade your lifestyle today. See why everyone is talking about {brand_name}.",
                    caption=f"Don't miss out on our newest release. Click below to secure yours today!",
                    hashtags=hashtags,
                    call_to_action="Order Now",
                    slogan="Excellence in Every Detail",
                ),
                AdVariation(
                    headline=f"Why Settle for Second Best?",
                    description=f"Choose {product_name} for unmatched performance and enduring quality.",
                    caption=f"Take the first step toward a better solution. Discover {brand_name} today.",
                    hashtags=hashtags,
                    call_to_action="Claim Your Discount",
                    slogan="The Standard of Modern Living",
                ),
            ]

        return PlatformCopyResult(
            platform=platform,
            tone_analysis=f"Optimized with punchy direct response hooks and calibrated hashtags for {platform}.",
            variations=variations[:num_variations],
        )

    async def run(
        self,
        campaign_data: Union[dict[str, Any], Any],
        campaign_understanding: Optional[dict[str, Any]] = None,
        brand_context: Optional[dict[str, Any]] = None,
        platforms: Optional[Union[str, list[str]]] = None,
        num_variations: int = 3,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Generate ad copy variations across designated platforms.

        Args:
            campaign_data: Input campaign payload.
            campaign_understanding: Insights from Campaign Understanding Agent.
            brand_context: Insights from Brand Research Agent.
            platforms: Single platform string or list of platforms. Defaults to campaign platforms.
            num_variations: Number of variations per platform (default 3).
            **kwargs: Extra arguments.

        Returns:
            dict[str, Any]: Structured dictionary containing:
                - variations: list[AdVariation] (for primary platform)
                - platform: str (primary platform)
                - tone_analysis: str
                - platform_variations: dict[platform, dict] (all requested platforms)
                - execution_time_seconds: float
        """
        start_time = time.perf_counter()
        normalized_data = self._normalize_campaign_input(campaign_data)

        brand_name = normalized_data.get("brand_name") or normalized_data.get("brand", "Our Brand")
        product_name = normalized_data.get("product_name") or normalized_data.get("product", "Flagship Offering")
        brief = (
            normalized_data.get("campaign_brief")
            or normalized_data.get("description")
            or normalized_data.get("objective")
            or "High impact marketing campaign"
        )

        understanding = campaign_understanding or {}
        brand = brand_context or {}

        # Resolve platforms list
        target_platforms: list[str] = []
        if isinstance(platforms, str):
            target_platforms = [platforms]
        elif isinstance(platforms, list) and platforms:
            target_platforms = [str(p) for p in platforms]
        elif "platform" in kwargs:
            target_platforms = [str(kwargs["platform"])]
        else:
            cand = normalized_data.get("platforms")
            if isinstance(cand, list) and cand:
                target_platforms = [str(p) for p in cand]
            elif isinstance(cand, str):
                target_platforms = [cand]
            else:
                target_platforms = ["instagram"]

        primary_platform = target_platforms[0].lower()
        self.logger.info(
            "generating_ad_copy",
            brand=brand_name,
            product=product_name,
            platforms=target_platforms,
            num_variations=num_variations,
        )

        platform_results: dict[str, dict[str, Any]] = {}
        for plat in target_platforms:
            plat_clean = plat.lower().strip()
            res = await self._generate_platform_copy(
                platform=plat_clean,
                brand_name=brand_name,
                product_name=product_name,
                brief=brief,
                campaign_understanding=understanding,
                brand_context=brand,
                num_variations=num_variations,
            )
            platform_results[plat_clean] = res.model_dump()

        primary_result = platform_results[primary_platform]
        elapsed = time.perf_counter() - start_time

        output_dict: dict[str, Any] = {
            "variations": primary_result["variations"],
            "platform": primary_platform,
            "tone_analysis": primary_result["tone_analysis"],
            "platform_variations": platform_results,
            "execution_time_seconds": round(elapsed, 3),
        }

        self.logger.info(
            "ad_copy_generation_completed",
            primary_platform=primary_platform,
            variation_count=len(output_dict["variations"]),
            total_platforms=len(platform_results),
            duration_seconds=output_dict["execution_time_seconds"],
        )

        return output_dict
