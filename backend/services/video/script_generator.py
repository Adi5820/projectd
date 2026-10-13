"""AI-powered video script generation for social media and advertising."""
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
import structlog

from backend.services.llm.gemini import GeminiProvider
from backend.services.llm.provider import LLMProvider

logger = structlog.get_logger(__name__)


class Scene(BaseModel):
    """Individual scene specification within a video ad."""
    scene_number: int = Field(..., description="Order index of the scene starting at 1")
    description: str = Field(..., description="Visual scene action and composition description")
    narration_text: str = Field(..., description="Voiceover spoken script for this scene")
    duration_seconds: float = Field(..., description="Duration of this scene in seconds")
    image_prompt: str = Field(..., description="Detailed text prompt for AI image generation of scene visual")


class VideoScript(BaseModel):
    """Complete video script structure."""
    title: str = Field(..., description="Catchy title of the video ad")
    platform: str = Field(..., description="Target platform (e.g., instagram_reels, tiktok, youtube_shorts)")
    total_duration_seconds: float = Field(..., description="Total target duration of the video")
    aspect_ratio: str = Field(..., description="Target aspect ratio: 9:16, 16:9, or 1:1")
    scenes: List[Scene] = Field(..., description="Ordered list of scenes (3 to 5 scenes)")
    background_music_mood: str = Field(..., description="Suggested mood or tempo for background audio")
    call_to_action: str = Field(..., description="Final call to action message")


PLATFORM_ASPECT_RATIOS = {
    "tiktok": "9:16",
    "instagram_reels": "9:16",
    "youtube_shorts": "9:16",
    "instagram_story": "9:16",
    "instagram_feed": "1:1",
    "facebook_feed": "1:1",
    "youtube_standard": "16:9",
    "linkedin": "16:9",
}


def _determine_target_scenes(duration_seconds: int) -> int:
    """Determine optimal scene count based on total duration."""
    if duration_seconds <= 15:
        return 3
    elif duration_seconds <= 30:
        return 4
    else:
        return 5


async def generate_video_script(
    campaign_data: Dict[str, Any],
    ad_copy: Union[Dict[str, Any], str],
    duration_seconds: int = 15,
    platform: str = "instagram_reels",
    llm_provider: Optional[LLMProvider] = None,
) -> VideoScript:
    """Generate a high-converting, platform-tailored video advertisement script.
    
    Args:
        campaign_data: Campaign goals, brand info, target audience, product details.
        ad_copy: Approved copy, hooks, or messaging points.
        duration_seconds: Desired total duration in seconds (15, 30, or 60).
        platform: Social platform (tiktok, instagram_reels, youtube_shorts, etc.).
        llm_provider: Optional custom LLM provider; defaults to GeminiProvider.

    Returns:
        Validated VideoScript object.
    """
    provider = llm_provider or GeminiProvider()
    num_scenes = _determine_target_scenes(duration_seconds)
    aspect_ratio = PLATFORM_ASPECT_RATIOS.get(platform.lower(), "9:16")

    system_prompt = (
        "You are an award-winning creative video ad director and viral copywriter. "
        "Your task is to write high-converting video ad scripts tailored to specific social platforms. "
        "Adhere to best practices:\n"
        "- Hook the viewer within the first 2 seconds.\n"
        "- Maintain brisk, punchy narration that sounds natural when spoken aloud.\n"
        "- Image prompts should describe clean, photorealistic, cinematic commercial imagery WITHOUT visible text.\n"
        "- Ensure scene durations sum precisely to the target total duration."
    )

    prompt = f"""
Create a compelling video ad script with exactly {num_scenes} scenes.

TARGET PARAMETERS:
- Target Platform: {platform}
- Aspect Ratio: {aspect_ratio}
- Total Duration: {duration_seconds} seconds
- Target Scene Count: {num_scenes} scenes

CAMPAIGN DATA:
{campaign_data}

APPROVED AD COPY & MESSAGING:
{ad_copy}

REQUIREMENTS:
1. Scene 1: An irresistible thumb-stopping visual hook.
2. Middle Scenes: Problem demonstration, product revelation, and value proposition.
3. Final Scene: Emotional payoff and powerful Call-to-Action.
4. Total duration of all scenes combined must equal {duration_seconds} seconds.
5. Provide detailed, photographic image generation prompts for each scene (no text inside images).
6. Set aspect_ratio to '{aspect_ratio}'.
"""

    logger.info(
        "generating_video_script",
        platform=platform,
        duration_seconds=duration_seconds,
        num_scenes=num_scenes,
    )

    script = await provider.generate_structured(
        prompt=prompt,
        response_schema=VideoScript,
        system_prompt=system_prompt,
    )

    # Normalize total duration and scene durations to match exactly
    script.total_duration_seconds = float(duration_seconds)
    script.aspect_ratio = aspect_ratio
    script.platform = platform

    if script.scenes:
        current_sum = sum(s.duration_seconds for s in script.scenes)
        if abs(current_sum - duration_seconds) > 0.05 and current_sum > 0:
            scale_factor = duration_seconds / current_sum
            for s in script.scenes:
                s.duration_seconds = round(s.duration_seconds * scale_factor, 2)
            # Adjust rounding difference on final scene
            diff = duration_seconds - sum(s.duration_seconds for s in script.scenes)
            script.scenes[-1].duration_seconds = round(script.scenes[-1].duration_seconds + diff, 2)

    logger.info(
        "video_script_generated_success",
        title=script.title,
        scenes_count=len(script.scenes),
        total_duration=script.total_duration_seconds,
    )
    return script


class ScriptGenerator:
    """Service wrapper for AI video script generation."""

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self.llm_provider = llm_provider

    async def generate(
        self,
        campaign_data: Dict[str, Any],
        ad_copy: Union[Dict[str, Any], str],
        duration_seconds: int = 15,
        platform: str = "instagram_reels",
        llm_provider: Optional[LLMProvider] = None,
    ) -> VideoScript:
        return await generate_video_script(
            campaign_data=campaign_data,
            ad_copy=ad_copy,
            duration_seconds=duration_seconds,
            platform=platform,
            llm_provider=llm_provider or self.llm_provider,
        )

