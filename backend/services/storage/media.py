"""Local filesystem storage implementation for application media assets."""
import os
from pathlib import Path
import re
from typing import Dict, Optional, Set
import uuid

import structlog

from backend.config import settings
from backend.services.storage.provider import StorageProvider

logger = structlog.get_logger(__name__)

ALLOWED_CATEGORIES: Set[str] = {"posters", "videos", "thumbnails", "documents"}

CATEGORY_EXTENSIONS: Dict[str, Set[str]] = {
    "posters": {".png", ".jpg", ".jpeg", ".webp"},
    "videos": {".mp4", ".webm", ".mov"},
    "thumbnails": {".png", ".jpg", ".jpeg", ".webp"},
    "documents": {".pdf", ".docx", ".txt", ".md"},
}

MAX_FILE_SIZES: Dict[str, int] = {
    "posters": 25 * 1024 * 1024,      # 25 MB
    "thumbnails": 10 * 1024 * 1024,   # 10 MB
    "videos": 100 * 1024 * 1024,      # 100 MB
    "documents": 25 * 1024 * 1024,    # 25 MB
}


class StorageValidationError(Exception):
    """Raised when file validation (size, extension, category) fails."""
    pass


class LocalMediaStorage(StorageProvider):
    """Local filesystem storage manager providing URL-based media operations."""

    def __init__(self, base_storage_path: Optional[str] = None):
        """Initialize the local media storage provider.
        
        Args:
            base_storage_path: Root storage directory. Defaults to settings.MEDIA_STORAGE_PATH.
        """
        self.base_path = Path(base_storage_path or settings.MEDIA_STORAGE_PATH).resolve()
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Create category subdirectories if they do not exist."""
        for category in ALLOWED_CATEGORIES:
            (self.base_path / category).mkdir(parents=True, exist_ok=True)
        (self.base_path / "temp").mkdir(parents=True, exist_ok=True)

    def _determine_category(self, filename: str, content_type: str) -> str:
        """Determine category based on MIME content type and filename."""
        ct = content_type.lower().strip()
        ext = Path(filename).suffix.lower()

        if "video" in ct or ext in CATEGORY_EXTENSIONS["videos"]:
            return "videos"
        if "pdf" in ct or "word" in ct or "document" in ct or ext in CATEGORY_EXTENSIONS["documents"]:
            return "documents"
        if "thumb" in filename.lower():
            return "thumbnails"
        if "image" in ct or ext in CATEGORY_EXTENSIONS["posters"]:
            return "posters"

        return "posters"

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename by removing potentially unsafe characters."""
        base_name = os.path.basename(filename)
        cleaned = re.sub(r"[^\w\.-]", "_", base_name)
        return cleaned or "file.bin"

    def get_full_path(self, url: str) -> Path:
        """Resolve a media URL to its absolute filesystem Path.
        
        Args:
            url: URL path such as '/media/posters/uuid_image.png'.

        Returns:
            Resolved Path object.

        Raises:
            StorageValidationError: If path traversal outside base directory is detected.
        """
        clean_url = url.strip()
        if clean_url.startswith("/media/"):
            rel_part = clean_url[len("/media/"):]
        elif clean_url.startswith("media/"):
            rel_part = clean_url[len("media/"):]
        else:
            rel_part = clean_url.lstrip("/")

        target_path = (self.base_path / rel_part).resolve()

        # Prevent directory traversal attacks
        if not str(target_path).startswith(str(self.base_path)):
            raise StorageValidationError(f"Invalid path traversal attempt for url: {url}")

        return target_path

    async def save(
        self,
        data: bytes,
        filename: str,
        content_type: str,
        category: Optional[str] = None,
    ) -> str:
        """Save file bytes into the corresponding media category folder.
        
        Args:
            data: Raw file payload.
            filename: Original filename.
            content_type: MIME type string.
            category: Optional explicit category override.

        Returns:
            URL string in format '/media/<category>/<uuid>_<filename>'.
        """
        target_category = category or self._determine_category(filename, content_type)
        if target_category not in ALLOWED_CATEGORIES:
            target_category = "posters"

        # Validate file size
        max_size = MAX_FILE_SIZES.get(target_category, 25 * 1024 * 1024)
        if len(data) > max_size:
            raise StorageValidationError(
                f"File size ({len(data)} bytes) exceeds maximum allowed {max_size} bytes for {target_category}."
            )

        sanitized = self._sanitize_filename(filename)
        unique_name = f"{uuid.uuid4().hex[:12]}_{sanitized}"

        category_dir = self.base_path / target_category
        category_dir.mkdir(parents=True, exist_ok=True)
        dest_file = category_dir / unique_name

        with open(dest_file, "wb") as f:
            f.write(data)

        url = f"/media/{target_category}/{unique_name}"
        logger.info(
            "media_file_saved",
            category=target_category,
            filename=unique_name,
            size_bytes=len(data),
            url=url,
        )
        return url

    async def delete(self, url: str) -> bool:
        """Delete file associated with the given URL.
        
        Args:
            url: Stored media URL.

        Returns:
            True if file existed and was deleted, False otherwise.
        """
        try:
            full_path = self.get_full_path(url)
            if full_path.is_file():
                full_path.unlink()
                logger.info("media_file_deleted", url=url, path=str(full_path))
                return True
            logger.warning("media_file_delete_not_found", url=url)
            return False
        except Exception as e:
            logger.error("media_file_delete_failed", url=url, error=str(e))
            return False


# Module-level instance and helpers
_default_storage: Optional[LocalMediaStorage] = None


def get_media_storage() -> LocalMediaStorage:
    """Get singleton LocalMediaStorage instance."""
    global _default_storage
    if _default_storage is None:
        _default_storage = LocalMediaStorage()
    return _default_storage


def get_full_path(url: str) -> Path:
    """Module-level helper to resolve a media URL to its local filesystem path."""
    return get_media_storage().get_full_path(url)

