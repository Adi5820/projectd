"""
Poster Generation Agent for Agentic Ads Platform.

Orchestrates the complete poster creation workflow:
1. Advanced prompt engineering for commercial ad imagery.
2. AI image generation via Flux/Together AI or Gemini image providers.
3. Clean typography and graphic overlay composition via ImageCompositor.
"""

from __future__ import annotations

import io
import time
from typing import Any, Optional, Tuple, Union

from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel, Field
import structlog

from backend.agents.base import BaseAgent


ASPECT_RATIOS: dict[str, Tuple[int, int]] = {
    "1:1": (1024, 1024),
    "9:16": (768, 1344),
    "16:9": (1344, 768),
    "4:5": (864, 1080),
    "3:4": (768, 1024),
    "4:3": (1024, 768),
    "2:3": (768, 1152),
}


class PosterPromptBlueprint(BaseModel):
    """Engineered prompt specification for image generation."""

    positive_prompt: str = Field(
        description="Detailed cinematic, commercial photography prompt with lighting and style cues",
    )
    negative_prompt: str = Field(
        default="text, typography, words, letters, watermark, low quality, blurry, deformed, distorted, artifacts",
        description="Negative prompt preventing in-image text and degradation",
    )
    visual_mood: str = Field(
        description="Visual aesthetic description (e.g. 'Sleek dark mode luxury with neon accents')",
    )


class PosterAgent(BaseAgent):
    """
    Poster Generation Agent.

    Designs visual advertising posters by pairing high-fidelity AI diffusion models
    with precision layout composition.
    """

    def __init__(
        self,
        llm_provider: Optional[Any] = None,
        image_provider: Optional[Any] = None,
        image_compositor: Optional[Any] = None,
    ) -> None:
        """
        Initialize the Poster Agent.

        Args:
            llm_provider: Language model provider for prompt engineering.
            image_provider: Diffusion image generation service (e.g. FluxTogetherProvider).
            image_compositor: Image compositor service for text overlays.
        """
        super().__init__(name="poster_agent", llm_provider=llm_provider)
        self.image_provider = image_provider
        self.image_compositor = image_compositor

    def _build_system_prompt(self) -> str:
        """
        Build an expert commercial visual art director system prompt.

        Returns:
            str: System prompt instructions.
        """
        return (
            "You are a legendary Commercial Art Director and CGI Visual Designer specializing in high-end "
            "product photography and advertising poster visual direction.\n\n"
            "Your role is to design prompt blueprints for cutting-edge text-to-image models (Flux.1, Midjourney, SDXL).\n"
            "CRITICAL RULES FOR IMAGE PROMPT CREATION:\n"
            "1. NEVER request text, letters, slogans, or logos inside the positive prompt! (Text is overlaid cleanly in post-production).\n"
            "2. Focus entirely on visual composition, lighting (e.g. soft rim lighting, volumetric rays, high-key studio light), "
            "materials/textures (matte metal, sleek glass, marble, organic wood), camera angles (hero shot, 45-degree isometric, eye-level), "
            "and color harmony matching brand colors.\n"
            "3. Use professional photography descriptors: 'commercial product showcase, 85mm lens, f/1.8, bokeh background, award-winning advertising visual, 8k resolution, ultra-detailed'.\n"
            "4. Leave negative space or clean zones suitable for typography placement."
        )

    def _get_dimensions(self, aspect_ratio: str) -> Tuple[int, int]:
        """
        Resolve aspect ratio string into pixel dimensions.

        Args:
            aspect_ratio: Ratio string like '1:1', '9:16', '16:9'.

        Returns:
            Tuple[int, int]: (width, height)
        """
        clean_ratio = aspect_ratio.strip().lower()
        if clean_ratio in ASPECT_RATIOS:
            return ASPECT_RATIOS[clean_ratio]

        # Invert or normalize e.g. "9x16"
        clean_ratio = clean_ratio.replace("x", ":")
        if clean_ratio in ASPECT_RATIOS:
            return ASPECT_RATIOS[clean_ratio]

        return ASPECT_RATIOS["1:1"]

    async def _engineer_image_prompt(
        self,
        brand_name: str,
        product_name: str,
        brief: str,
        campaign_understanding: dict[str, Any],
        brand_context: dict[str, Any],
        platform: str,
        aspect_ratio: str,
    ) -> PosterPromptBlueprint:
        """
        Synthesize a commercial photography prompt using LLM or structured rules.

        Args:
            brand_name: Brand name.
            product_name: Product name.
            brief: Campaign brief.
            campaign_understanding: Strategy dictionary.
            brand_context: Brand context dictionary.
            platform: Target platform.
            aspect_ratio: Target aspect ratio.

        Returns:
            PosterPromptBlueprint: Prompt blueprint.
        """
        colors = brand_context.get("brand_colors", ["#1E3A8A", "#FFFFFF"])
        color_str = ", ".join(colors[:3]) if isinstance(colors, list) else str(colors)
        pillars = campaign_understanding.get("recommended_content_pillars", ["Product showcase"])
        pillar_str = pillars[0] if pillars and isinstance(pillars, list) else "Hero product showcase"

        user_prompt = (
            f"Craft an elite commercial photography image prompt for an advertising poster:\n\n"
            f"BRAND: {brand_name}\n"
            f"PRODUCT: {product_name}\n"
            f"BRIEF: {brief}\n"
            f"BRAND COLOR ACCENTS: {color_str}\n"
            f"CORE THEME / PILLAR: {pillar_str}\n"
            f"PLATFORM: {platform}\n"
            f"ASPECT RATIO: {aspect_ratio}\n\n"
            f"Output a positive_prompt (NO text/words in image, focus on photorealism, studio lighting, materials, "
            f"composition and background), negative_prompt, and visual_mood."
        )

        try:
            return await self._call_llm_structured(
                prompt=user_prompt,
                response_model=PosterPromptBlueprint,
            )
        except Exception as exc:
            self.logger.warning("prompt_engineering_llm_failed_fallback", error=str(exc))
            # Fallback high quality prompt
            positive = (
                f"Commercial studio product photography of {product_name} by {brand_name}. "
                f"Sleek professional advertisement poster composition, subtle {color_str} ambient color accents, "
                f"hero product placement on modern minimalist pedestal, soft cinematic rim lighting, "
                f"subtle depth of field, 8k resolution, hyperrealistic, award-winning advertising visual."
            )
            return PosterPromptBlueprint(
                positive_prompt=positive,
                negative_prompt="text, typography, watermark, logo, words, letters, blurry, distorted, low quality",
                visual_mood="Modern minimalist commercial studio lighting with brand color accents",
            )

    async def _generate_base_image(
        self,
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        provider: Optional[Any] = None,
    ) -> Tuple[bytes, str, str]:
        """
        Generate raw background visual using the image provider or Pillow fallback.

        Args:
            prompt: Positive generation prompt.
            negative_prompt: Negative prompt.
            width: Image width.
            height: Image height.
            provider: Image provider instance.

        Returns:
            Tuple[bytes, str, str]: (image_bytes, provider_name, model_name).
        """
        active_provider = provider or self.image_provider

        if active_provider is not None:
            # 1. Attempt generate_image
            try:
                if hasattr(active_provider, "generate_image") and callable(active_provider.generate_image):
                    res = active_provider.generate_image(
                        prompt=prompt,
                        width=width,
                        height=height,
                        negative_prompt=negative_prompt,
                    )
                    raw_bytes = await res if hasattr(res, "__await__") else res
                    if isinstance(raw_bytes, bytes) and len(raw_bytes) > 0:
                        provider_name = getattr(active_provider, "provider_name", "FluxTogetherProvider")
                        model_name = getattr(active_provider, "model_name", "black-forest-labs/FLUX.1-schnell")
                        return raw_bytes, provider_name, model_name

                # 2. Attempt generate
                if hasattr(active_provider, "generate") and callable(active_provider.generate):
                    res = active_provider.generate(
                        prompt=prompt,
                        width=width,
                        height=height,
                    )
                    raw_bytes = await res if hasattr(res, "__await__") else res
                    if isinstance(raw_bytes, bytes) and len(raw_bytes) > 0:
                        return raw_bytes, "ImageProvider", "DefaultModel"
            except Exception as exc:
                self.logger.error("image_provider_call_failed", error=str(exc))

        # 3. Fallback: Generate procedural high-res poster canvas with Pillow
        self.logger.warning("using_procedural_pillow_canvas")
        fallback_bytes = self._create_procedural_poster_canvas(width, height)
        return fallback_bytes, "PillowProceduralProvider", "CanvasRendererV1"

    def _create_procedural_poster_canvas(self, width: int, height: int) -> bytes:
        """
        Procedurally render an elegant, high-contrast gradient canvas as an emergency fallback.

        Args:
            width: Target width.
            height: Target height.

        Returns:
            bytes: PNG image byte stream.
        """
        img = Image.new("RGBA", (width, height), (15, 23, 42, 255))
        draw = ImageDraw.Draw(img)

        # Draw deep cinematic gradient background
        for y in range(height):
            ratio = y / max(height - 1, 1)
            r = int(15 * (1 - ratio) + 30 * ratio)
            g = int(23 * (1 - ratio) + 58 * ratio)
            b = int(42 * (1 - ratio) + 138 * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

        # Draw aesthetic geometric focus element / spotlight
        cx, cy = width // 2, int(height * 0.45)
        radius = min(width, height) // 3
        draw.ellipse(
            [(cx - radius, cy - radius), (cx + radius, cy + radius)],
            outline=(59, 130, 246, 120),
            width=3,
        )

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    async def _overlay_text(
        self,
        image_bytes: bytes,
        headline: str,
        cta: str,
        slogan: str,
        compositor: Optional[Any] = None,
    ) -> bytes:
        """
        Apply typography overlays to the base image.

        Args:
            image_bytes: Base image bytes.
            headline: Ad headline.
            cta: Call to action button text.
            slogan: Slogan/tagline.
            compositor: Optional compositor service override.

        Returns:
            bytes: Final composited image bytes.
        """
        active_compositor = compositor or self.image_compositor

        if active_compositor is not None:
            try:
                if hasattr(active_compositor, "compose") and callable(active_compositor.compose):
                    res = active_compositor.compose(
                        image_bytes=image_bytes,
                        headline=headline,
                        cta=cta,
                        slogan=slogan,
                    )
                    return await res if hasattr(res, "__await__") else res

                if hasattr(active_compositor, "add_text_overlay") and callable(active_compositor.add_text_overlay):
                    res = active_compositor.add_text_overlay(
                        image_bytes=image_bytes,
                        headline=headline,
                        cta=cta,
                    )
                    return await res if hasattr(res, "__await__") else res
            except Exception as exc:
                self.logger.warning("compositor_service_failed_fallback_to_pillow", error=str(exc))

        # Pillow in-process text compositor fallback
        try:
            pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
            width, height = pil_img.size
            draw = ImageDraw.Draw(pil_img)

            # Draw bottom gradient overlay for text readability
            overlay_h = int(height * 0.35)
            overlay = Image.new("RGBA", (width, overlay_h), (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            for y in range(overlay_h):
                alpha = int(220 * (y / overlay_h))
                overlay_draw.line([(0, y), (width, y)], fill=(0, 0, 0, alpha))
            pil_img.paste(overlay, (0, height - overlay_h), overlay)

            # Draw headline
            font_size = max(24, int(width * 0.045))
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
                font_cta = ImageFont.truetype("arial.ttf", max(18, int(font_size * 0.75)))
            except Exception:
                font = ImageFont.load_default()
                font_cta = ImageFont.load_default()

            text_y = height - overlay_h + int(overlay_h * 0.2)
            if headline:
                draw.text(
                    (int(width * 0.08), text_y),
                    headline[:60],
                    font=font,
                    fill=(255, 255, 255, 255),
                )

            # Draw CTA button box
            if cta:
                cta_y = text_y + font_size + 20
                cta_w = int(len(cta) * font_size * 0.5) + 30
                cta_h = int(font_size * 1.2)
                draw.rectangle(
                    [(int(width * 0.08), cta_y), (int(width * 0.08) + cta_w, cta_y + cta_h)],
                    fill=(37, 99, 235, 230),
                )
                draw.text(
                    (int(width * 0.08) + 15, cta_y + int(cta_h * 0.15)),
                    cta,
                    font=font_cta,
                    fill=(255, 255, 255, 255),
                )

            out_buf = io.BytesIO()
            pil_img.convert("RGB").save(out_buf, format="JPEG", quality=95)
            return out_buf.getvalue()
        except Exception as exc:
            self.logger.error("pillow_overlay_failed_returning_raw", error=str(exc))
            return image_bytes

    async def run(
        self,
        campaign_data: Union[dict[str, Any], Any],
        campaign_understanding: Optional[dict[str, Any]] = None,
        brand_context: Optional[dict[str, Any]] = None,
        ad_copy: Optional[dict[str, Any]] = None,
        aspect_ratio: str = "1:1",
        platform: str = "instagram",
        overlay_text: bool = True,
        image_provider: Optional[Any] = None,
        image_compositor: Optional[Any] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Execute poster generation workflow.

        Args:
            campaign_data: Input campaign payload.
            campaign_understanding: Insights from Campaign Understanding Agent.
            brand_context: Insights from Brand Research Agent.
            ad_copy: Copy variations from Copywriting Agent.
            aspect_ratio: Target aspect ratio ('1:1', '9:16', '16:9', etc.).
            platform: Target platform ('instagram', 'facebook', etc.).
            overlay_text: Whether to apply text overlays.
            image_provider: Image provider override.
            image_compositor: Compositor override.
            **kwargs: Extra parameters.

        Returns:
            dict[str, Any]:
                - image_bytes: bytes
                - prompt_used: str
                - provider: str
                - model_used: str
                - aspect_ratio: str
                - dimensions: dict(width, height)
                - execution_time_seconds: float
        """
        start_time = time.perf_counter()

        # Normalize inputs
        norm_data: dict[str, Any] = {}
        if isinstance(campaign_data, dict):
            norm_data = campaign_data
        elif hasattr(campaign_data, "model_dump"):
            norm_data = campaign_data.model_dump()
        elif hasattr(campaign_data, "__dict__"):
            norm_data = {k: v for k, v in campaign_data.__dict__.items() if not k.startswith("_")}

        brand_name = norm_data.get("brand_name") or norm_data.get("brand", "Brand")
        product_name = norm_data.get("product_name") or norm_data.get("product", "Product")
        brief = norm_data.get("campaign_brief") or norm_data.get("description", "")

        understanding = campaign_understanding or {}
        brand = brand_context or {}

        # Extract headline, slogan, and cta from ad_copy if available
        headline = f"Discover {product_name}"
        cta = "Shop Now"
        slogan = f"{brand_name} Quality"

        if ad_copy and isinstance(ad_copy, dict):
            variations = ad_copy.get("variations", [])
            if variations and isinstance(variations, list) and len(variations) > 0:
                first_var = variations[0]
                if isinstance(first_var, dict):
                    headline = first_var.get("headline", headline)
                    cta = first_var.get("call_to_action", cta)
                    slogan = first_var.get("slogan", slogan)
                elif hasattr(first_var, "headline"):
                    headline = getattr(first_var, "headline", headline)
                    cta = getattr(first_var, "call_to_action", cta)
                    slogan = getattr(first_var, "slogan", slogan)

        width, height = self._get_dimensions(aspect_ratio)
        self.logger.info(
            "generating_poster",
            brand=brand_name,
            product=product_name,
            platform=platform,
            aspect_ratio=aspect_ratio,
            dimensions=(width, height),
        )

        # 1. Engineer prompt
        blueprint = await self._engineer_image_prompt(
            brand_name=brand_name,
            product_name=product_name,
            brief=brief,
            campaign_understanding=understanding,
            brand_context=brand,
            platform=platform,
            aspect_ratio=aspect_ratio,
        )

        # 2. Generate base visual
        base_image_bytes, provider_name, model_name = await self._generate_base_image(
            prompt=blueprint.positive_prompt,
            negative_prompt=blueprint.negative_prompt,
            width=width,
            height=height,
            provider=image_provider,
        )

        # 3. Post-process with typography overlay if requested
        final_image_bytes = base_image_bytes
        if overlay_text:
            final_image_bytes = await self._overlay_text(
                image_bytes=base_image_bytes,
                headline=headline,
                cta=cta,
                slogan=slogan,
                compositor=image_compositor,
            )

        elapsed = time.perf_counter() - start_time

        result = {
            "image_bytes": final_image_bytes,
            "prompt_used": blueprint.positive_prompt,
            "provider": provider_name,
            "model_used": model_name,
            "aspect_ratio": aspect_ratio,
            "dimensions": {"width": width, "height": height},
            "headline_used": headline,
            "cta_used": cta,
            "execution_time_seconds": round(elapsed, 3),
        }

        self.logger.info(
            "poster_generation_completed",
            provider=provider_name,
            bytes_size=len(final_image_bytes),
            duration_seconds=result["execution_time_seconds"],
        )

        return result
