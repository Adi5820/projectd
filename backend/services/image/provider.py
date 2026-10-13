"""Abstract base class for Image providers."""
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple


class ImageProvider(ABC):
    """Abstract interface defining required image generation capabilities."""

    @abstractmethod
    async def generate_image(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        style: Optional[str] = None,
    ) -> bytes:
        """Generate image and return raw bytes.
        
        Args:
            prompt: Text prompt describing the image to generate.
            width: Image width in pixels.
            height: Image height in pixels.
            style: Optional styling directive (e.g. photorealistic, cinematic).

        Returns:
            Raw image bytes (PNG or JPEG).
        """
        pass

    @abstractmethod
    def get_supported_sizes(self) -> List[Tuple[int, int]]:
        """Return list of supported (width, height) pixel dimensions."""
        pass
