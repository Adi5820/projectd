"""FLUX.1 image provider implementation via Together AI."""
import asyncio
import base64
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx
import structlog
from together import Together

from backend.config import settings
from backend.services.image.provider import ImageProvider

logger = structlog.get_logger(__name__)

ASPECT_RATIO_PRESETS: Dict[str, Tuple[int, int]] = {
    "1:1": (1024, 1024),
    "4:5": (832, 1040),
    "9:16": (576, 1024),
    "16:9": (1024, 576),
}


def get_dimensions_from_aspect_ratio(aspect_ratio: str) -> Tuple[int, int]:
    """Convert aspect ratio string into (width, height) pixel dimensions.
    
    Args:
        aspect_ratio: Ratio string like '1:1', '4:5', '9:16', '16:9'.

    Returns:
        Tuple of (width, height). Defaults to (1024, 1024) if unrecognized.
    """
    clean_ratio = aspect_ratio.strip().lower()
    return ASPECT_RATIO_PRESETS.get(clean_ratio, (1024, 1024))


class FluxTogetherError(Exception):
    """Base exception for Together AI / FLUX image generation."""
    pass


class FluxTogetherProvider(ImageProvider):
    """FLUX.1 image generator utilizing Together AI SDK."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        """Initialize the Together AI client.
        
        Args:
            api_key: Together AI API key.
            model_name: FLUX model identifier.
        """
        self.api_key = api_key or settings.TOGETHER_API_KEY
        self.model_name = model_name or getattr(settings, "FLUX_MODEL", "black-forest-labs/FLUX.1-schnell")
        
        if not self.api_key:
            logger.warning("together_api_key_missing", message="TOGETHER_API_KEY is not configured.")
        
        self.client = Together(api_key=self.api_key)

    def get_supported_sizes(self) -> List[Tuple[int, int]]:
        """Return supported image dimensions."""
        return list(ASPECT_RATIO_PRESETS.values())

    def _sync_generate_call(self, prompt: str, width: int, height: int):
        """Synchronous wrapper for Together image API call."""
        # Schnell works best with 4 steps; dev works with 28 steps
        steps = 4 if "schnell" in self.model_name.lower() else 28
        return self.client.images.generate(
            prompt=prompt,
            model=self.model_name,
            width=width,
            height=height,
            steps=steps,
            n=1,
            response_format="url",
        )

    async def _download_image(self, url: str) -> bytes:
        """Download image bytes from remote URL."""
        async with httpx.AsyncClient(timeout=60.0) as http_client:
            response = await http_client.get(url)
            response.raise_for_status()
            return response.content

    async def generate_image(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        style: Optional[str] = None,
        **kwargs: Any,
    ) -> bytes:
        """Generate image with FLUX.1 via Together AI with retries and downloading."""
        if not self.api_key or self.api_key.startswith("dev_"):
            raise FluxTogetherError("TOGETHER_API_KEY is not configured or is a development placeholder.")

        final_prompt = prompt.strip()
        if style:
            final_prompt = f"{final_prompt}, {style} style, high quality advertising photography"

        max_retries = 3
        backoff_delay = 1.5

        for attempt in range(1, max_retries + 1):
            start_time = time.perf_counter()
            try:
                # Execute generation request with 60 second timeout
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self._sync_generate_call,
                        final_prompt,
                        width,
                        height,
                    ),
                    timeout=60.0,
                )

                if not response.data or len(response.data) == 0:
                    raise FluxTogetherError("No image data returned from Together AI API.")

                item = response.data[0]
                image_bytes: Optional[bytes] = None

                if hasattr(item, "url") and item.url:
                    logger.debug("downloading_together_image", url=item.url)
                    image_bytes = await self._download_image(item.url)
                elif hasattr(item, "b64_json") and item.b64_json:
                    image_bytes = base64.b64decode(item.b64_json)
                else:
                    raise FluxTogetherError("Invalid image response: missing both url and b64_json.")

                latency = time.perf_counter() - start_time
                logger.info(
                    "flux_image_generated_success",
                    model=self.model_name,
                    prompt=final_prompt[:80],
                    width=width,
                    height=height,
                    bytes_length=len(image_bytes),
                    latency=round(latency, 3),
                    attempt=attempt,
                )
                return image_bytes

            except asyncio.TimeoutError as e:
                latency = time.perf_counter() - start_time
                logger.warning(
                    "flux_generate_timeout",
                    attempt=attempt,
                    latency=round(latency, 3),
                    timeout=60.0,
                )
                if attempt == max_retries:
                    raise FluxTogetherError("Together AI image generation timed out after 60s.") from e
                await asyncio.sleep(backoff_delay)
                backoff_delay *= 2.0

            except Exception as e:
                latency = time.perf_counter() - start_time
                logger.error(
                    "flux_generate_error",
                    attempt=attempt,
                    latency=round(latency, 3),
                    error=str(e),
                )
                if attempt == max_retries:
                    raise FluxTogetherError(f"FLUX image generation failed after {max_retries} attempts: {e}") from e
                await asyncio.sleep(backoff_delay)
                backoff_delay *= 2.0

        raise FluxTogetherError("Unexpected termination in FLUX image generation.")
