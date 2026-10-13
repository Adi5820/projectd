"""Asset management utilities for video and media rendering."""
import os
from pathlib import Path
from typing import Optional, Union

import structlog

from backend.config import settings

logger = structlog.get_logger(__name__)


def ensure_media_dirs() -> None:
    """Create all standard application media storage directories."""
    base_media = Path(settings.MEDIA_STORAGE_PATH)
    subdirs = ["posters", "videos", "thumbnails", "temp", "documents", "audio"]
    for subdir in subdirs:
        dir_path = base_media / subdir
        dir_path.mkdir(parents=True, exist_ok=True)
    logger.debug("media_directories_verified", base=str(base_media))


def get_background_music_path() -> Optional[str]:
    """Locate a bundled royalty-free background music audio track.
    
    Returns:
        Absolute path to an MP3/WAV background music file, or None if unavailable.
    """
    candidates = [
        Path(settings.BASE_DIR) / "backend" / "assets" / "audio" / "background.mp3",
        Path(settings.MEDIA_STORAGE_PATH) / "audio" / "background.mp3",
    ]

    for candidate in candidates:
        if candidate.is_file() and candidate.stat().st_size > 0:
            return str(candidate.resolve())

    # Check assets directory for any available audio file
    bundled_audio_dir = Path(settings.BASE_DIR) / "backend" / "assets" / "audio"
    if bundled_audio_dir.is_dir():
        for ext in ["*.mp3", "*.wav", "*.m4a"]:
            for audio_file in bundled_audio_dir.glob(ext):
                if audio_file.stat().st_size > 0:
                    return str(audio_file.resolve())

    return None


def save_scene_image(
    image_bytes: bytes,
    scene_id: Union[str, int],
    job_id: str,
) -> str:
    """Save an individual scene image frame to temporary storage.
    
    Args:
        image_bytes: Raw PNG/JPEG image data.
        scene_id: Scene index or identifier.
        job_id: Unique rendering job ID.

    Returns:
        Absolute path to the saved scene image.
    """
    ensure_media_dirs()
    temp_dir = Path(settings.MEDIA_STORAGE_PATH) / "temp"
    file_path = temp_dir / f"{job_id}_scene_{scene_id}.png"

    with open(file_path, "wb") as f:
        f.write(image_bytes)

    logger.debug("scene_image_saved", job_id=job_id, scene_id=scene_id, path=str(file_path))
    return str(file_path.resolve())


def cleanup_job_assets(job_id: str) -> None:
    """Remove temporary files associated with a specific rendering job.
    
    Args:
        job_id: Unique rendering job ID to clean up.
    """
    temp_dir = Path(settings.MEDIA_STORAGE_PATH) / "temp"
    if not temp_dir.is_dir():
        return

    cleaned_count = 0
    for file_path in temp_dir.glob(f"{job_id}*"):
        try:
            if file_path.is_file():
                file_path.unlink()
                cleaned_count += 1
        except Exception as e:
            logger.warning("cleanup_file_failed", file=str(file_path), error=str(e))

    logger.info("job_assets_cleaned", job_id=job_id, files_removed=cleaned_count)
