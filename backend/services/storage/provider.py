"""Abstract base class for storage providers."""
from abc import ABC, abstractmethod


class StorageProvider(ABC):
    """Abstract interface defining file storage and retrieval operations."""

    @abstractmethod
    async def save(self, data: bytes, filename: str, content_type: str) -> str:
        """Save raw data and return the accessible media URL.
        
        Args:
            data: Raw file bytes.
            filename: Original or requested filename.
            content_type: MIME content type (e.g., 'image/png', 'video/mp4').

        Returns:
            Relative or absolute accessible URL path.
        """
        pass

    @abstractmethod
    async def delete(self, url: str) -> bool:
        """Delete file resource identified by URL.
        
        Args:
            url: Stored file URL.

        Returns:
            True if file existed and was removed, False otherwise.
        """
        pass
