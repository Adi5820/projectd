"""
Campaign Understanding Agent for Agentic Ads Platform.

Analyzes raw campaign briefs, extracts high-impact strategic insights,
segments the target audience, defines competitive positioning, and maps out
cross-channel content strategies.
"""

from __future__ import annotations

import time
from typing import Any, Optional, Union

from pydantic import BaseModel, Field
import structlog

from backend.agents.base import BaseAgent


class TargetDemographics(BaseModel):
    """Granular demographic and psychographic audience profile."""

    age_range: str = Field(
        default="25-45",
        description="Target age bracket, e.g., '22-38 years old'",
    )
    interests: list[str] = Field(
        default_factory=list,
        description="Core interests, lifestyle traits, and cultural affinities",
    )
    pain_points: list[str] = Field(
        default_factory=list,
        description="Frustrations, challenges, and unfulfilled needs addressed by the product",
    )


class CampaignUnderstandingOutput(BaseModel):
    """Structured insights output from the Campaign Understanding Agent."""

    key_selling_points: list[str] = Field(
        description="Top unique value propositions, standout benefits, and core differentiators",
    )
    target_demographics: TargetDemographics = Field(
        description="Segmented demographics, lifestyle interests, and friction points",
    )
    competitive_positioning: str = Field(
        description="Strategic stance against direct competitors and category alternatives",
    )
    emotional_appeal: str = Field(
        description="Core emotional triggers, aspirations, and psychological drivers",
    )
    recommended_content_pillars: list[str] = Field(
        description="3 to 5 distinct thematic pillars for advertising assets",
    )
    platform_specific_strategy: dict[str, str] = Field(
        description="Tailored narrative and tactical distribution strategy per target platform",
    )


class CampaignAgent(BaseAgent):
    """
    Senior Advertising Strategy Agent.

    Decodes campaign inputs into actionable creative blueprints, identifying
    leverage points, psychological triggers, and channel-specific tactics.
    """

    def __init__(self, llm_provider: Optional[Any] = None) -> None:
        """Initialize the Campaign Understanding Agent."""
        super().__init__(name="campaign_agent", llm_provider=llm_provider)

    def _build_system_prompt(self) -> str:
        """
        Build an expert-level advertising strategist system prompt.

        Returns:
            str: Comprehensive system instructions.
        """
        return (
            "You are an elite Chief Strategy Officer (CSO) and Senior Advertising Strategist with over "
            "15 years of award-winning experience at top-tier global agencies (Ogilvy, BBDO, Droga5, Wieden+Kennedy).\n\n"
            "Your superpower is deconstructing complex marketing briefs into crystal-clear, high-converting "
            "strategic frameworks. You understand consumer psychology, behavioral economics, competitive moats, "
            "and platform-native content behavior across Instagram, YouTube, Facebook, TikTok, Twitter/X, and LinkedIn.\n\n"
            "When analyzing a campaign:\n"
            "1. Extract sharp, defensible Key Selling Points (KSPs) focused on customer value rather than generic specs.\n"
            "2. Define vivid target demographics including tangible daily frustrations (pain points) and deep passions.\n"
            "3. Articulate an aggressive competitive positioning that carves out an uncontested market category.\n"
            "4. Uncover the underlying emotional appeal (e.g., status, relief, belonging, empowerment, peace of mind).\n"
            "5. Design 3-5 distinct, repeatable content pillars for advertising creative production.\n"
            "6. Formulate tailored platform-specific strategies acknowledging each platform's distinct UX and user mindset.\n\n"
            "Always be concrete, persuasive, and commercially focused. Avoid generic corporate buzzwords."
        )

    def _extract_campaign_payload(self, campaign_data: Any) -> dict[str, Any]:
        """
        Normalize campaign data from various types (dict, Pydantic model, or object).

        Args:
            campaign_data: Input data in arbitrary format.

        Returns:
            dict[str, Any]: Normalized dictionary of campaign parameters.
        """
        if isinstance(campaign_data, dict):
            return dict(campaign_data)

        if hasattr(campaign_data, "model_dump") and callable(campaign_data.model_dump):
            return campaign_data.model_dump()

        if hasattr(campaign_data, "dict") and callable(campaign_data.dict):
            return campaign_data.dict()

        if hasattr(campaign_data, "__dict__"):
            return {k: v for k, v in campaign_data.__dict__.items() if not k.startswith("_")}

        return {"raw_brief": str(campaign_data)}

    async def run(
        self,
        campaign_data: Union[dict[str, Any], Any],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Analyze the campaign brief and return structured strategic insights.

        Args:
            campaign_data: Campaign input data (e.g. CampaignCreate schema or dictionary).
            **kwargs: Extra runtime options.

        Returns:
            dict[str, Any]: Structured dictionary containing:
                - key_selling_points: list[str]
                - target_demographics: dict(age_range, interests, pain_points)
                - competitive_positioning: str
                - emotional_appeal: str
                - recommended_content_pillars: list[str]
                - platform_specific_strategy: dict[str, str]
                - execution_time_seconds: float
        """
        start_time = time.perf_counter()
        normalized_data = self._extract_campaign_payload(campaign_data)

        brand_name = normalized_data.get("brand_name") or normalized_data.get("brand", "Our Brand")
        product_name = normalized_data.get("product_name") or normalized_data.get("product", "Flagship Offering")
        brief = (
            normalized_data.get("campaign_brief")
            or normalized_data.get("description")
            or normalized_data.get("objective")
            or "Comprehensive modern marketing campaign"
        )
        target_audience = normalized_data.get("target_audience") or normalized_data.get("audience", "")
        tone = normalized_data.get("tone") or normalized_data.get("brand_voice", "Compelling, modern, authentic")
        platforms = normalized_data.get("platforms") or ["instagram", "youtube", "facebook", "twitter", "linkedin"]
        guidelines = normalized_data.get("guidelines") or normalized_data.get("brand_guidelines", "")

        self.logger.info(
            "analyzing_campaign",
            brand=brand_name,
            product=product_name,
            platforms=platforms,
        )

        user_prompt = (
            f"Analyze the following campaign brief and produce a structured strategic blueprint:\n\n"
            f"BRAND NAME: {brand_name}\n"
            f"PRODUCT / SERVICE: {product_name}\n"
            f"CAMPAIGN BRIEF & OBJECTIVE: {brief}\n"
            f"STATED AUDIENCE: {target_audience}\n"
            f"DESIRED TONE: {tone}\n"
            f"CHANNELS / PLATFORMS: {', '.join(platforms) if isinstance(platforms, list) else platforms}\n"
            f"ADDITIONAL GUIDELINES: {guidelines}\n\n"
            f"Provide a rigorous, actionable strategic analysis in the required JSON schema format."
        )

        try:
            structured_output = await self._call_llm_structured(
                prompt=user_prompt,
                response_model=CampaignUnderstandingOutput,
            )
            result_dict = structured_output.model_dump()
        except Exception as exc:
            self.logger.error("campaign_analysis_llm_failed", error=str(exc))
            # Graceful fallback to guarantee system resilience
            result_dict = self._generate_fallback_strategy(
                brand_name=brand_name,
                product_name=product_name,
                brief=brief,
                target_audience=target_audience,
                platforms=platforms if isinstance(platforms, list) else ["instagram", "facebook"],
            )

        elapsed = time.perf_counter() - start_time
        result_dict["execution_time_seconds"] = round(elapsed, 3)

        self.logger.info(
            "campaign_analysis_complete",
            ksp_count=len(result_dict.get("key_selling_points", [])),
            duration_seconds=result_dict["execution_time_seconds"],
        )

        return result_dict

    def _generate_fallback_strategy(
        self,
        brand_name: str,
        product_name: str,
        brief: str,
        target_audience: str,
        platforms: list[str],
    ) -> dict[str, Any]:
        """
        Generate heuristic fallback insights when the LLM service is unreachable.

        Args:
            brand_name: Brand name.
            product_name: Product or service.
            brief: Provided brief text.
            target_audience: Target audience string.
            platforms: List of platforms.

        Returns:
            dict[str, Any]: Safe, structured strategy dict.
        """
        self.logger.warning("using_fallback_strategy")

        platform_strats: dict[str, str] = {}
        for p in platforms:
            p_lower = str(p).lower()
            if "insta" in p_lower:
                platform_strats[p] = "Visually immersive carousel and short-form video highlighting lifestyle transformation."
            elif "you" in p_lower:
                platform_strats[p] = "High-retention hook in the first 5 seconds leading into problem-solution product demo."
            elif "link" in p_lower:
                platform_strats[p] = "Data-driven case study emphasizing efficiency, ROI, and executive decision-making."
            elif "twit" in p_lower or "x" in p_lower:
                platform_strats[p] = "Punchy value proposition with sharp visual card and timely conversational hook."
            else:
                platform_strats[p] = "Social proof, relatable testimonial framing, and clear action button."

        return {
            "key_selling_points": [
                f"Superior quality and innovation from {brand_name}",
                f"Engineered specifically for {target_audience or 'discerning modern customers'}",
                f"Solves core everyday challenges seamlessly with {product_name}",
            ],
            "target_demographics": {
                "age_range": "25-45",
                "interests": ["Innovation", "Productivity", "Modern lifestyle", "Quality essentials"],
                "pain_points": [
                    "Wasting time with low-grade alternatives",
                    "Difficulty finding reliable, high-performance solutions",
                    "Frustration with complicated or fragile products",
                ],
            },
            "competitive_positioning": (
                f"{brand_name} positions {product_name} as the premium yet accessible benchmark, "
                f"delivering tangible performance where legacy competitors cut corners."
            ),
            "emotional_appeal": "Empowerment, relief from friction, and confidence in making the smartest choice.",
            "recommended_content_pillars": [
                "Product In Action: Real World Problem Solving",
                "Behind the Craft: Quality and Reliability",
                "Customer Transformation & Social Proof",
                "Educational Value & Tips",
            ],
            "platform_specific_strategy": platform_strats,
        }
