"""Voice narration generation using Microsoft Edge-TTS neural voices."""
import os
from pathlib import Path
from typing import Any, Optional
import uuid

import edge_tts
import structlog

from backend.config import settings

logger = structlog.get_logger(__name__)


class NarrationError(Exception):
    """Base exception for voice narration generation errors."""
    pass


async def generate_narration(
    text: str,
    voice: Optional[str] = None,
    output_path: Optional[str] = None,
) -> str:
    """Generate high-quality voice narration MP3 from text using Edge-TTS.
    
    Args:
        text: Spoken text script to synthesize.
        voice: Microsoft Neural voice identifier (e.g., 'en-US-ChristopherNeural', 'en-US-JennyNeural').
               Defaults to settings.EDGE_TTS_VOICE.
        output_path: Optional destination file path. If None, saves to media/temp/<uuid>.mp3.

    Returns:
        Absolute string path to the created MP3 file.
    """
    clean_text = text.strip()
    if not clean_text:
        raise NarrationError("Cannot synthesize narration from empty text.")

    chosen_voice = voice or getattr(settings, "EDGE_TTS_VOICE", "en-US-ChristopherNeural")

    if output_path:
        dest_path = Path(output_path).resolve()
    else:
        temp_dir = Path(settings.MEDIA_STORAGE_PATH) / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        dest_path = temp_dir / f"narration_{uuid.uuid4().hex[:10]}.mp3"

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_str = str(dest_path)

    logger.info(
        "synthesizing_narration_start",
        voice=chosen_voice,
        char_count=len(clean_text),
        output_path=dest_str,
    )

    try:
        communicate = edge_tts.Communicate(text=clean_text, voice=chosen_voice)
        await communicate.save(dest_str)

        if not os.path.exists(dest_str) or os.path.getsize(dest_str) == 0:
            raise NarrationError(f"Narration file {dest_str} was not generated or is 0 bytes.")

        logger.info(
            "synthesizing_narration_success",
            voice=chosen_voice,
            file_size_bytes=os.path.getsize(dest_str),
            output_path=dest_str,
        )
        return dest_str

    except Exception as e:
        logger.error(
            "synthesizing_narration_failed",
            voice=chosen_voice,
            error=str(e),
            output_path=dest_str,
        )
        raise NarrationError(f"Edge-TTS narration generation failed: {e}") from e


class NarrationService:
    """Service wrapper for Edge-TTS neural voice synthesis."""

    def __init__(self, default_voice: Optional[str] = None):
        self.default_voice = default_voice or getattr(settings, "EDGE_TTS_VOICE", "en-US-AriaNeural")

    async def generate_narration(
        self,
        text: str,
        voice: Optional[str] = None,
        output_path: Optional[str] = None,
    ) -> str:
        return await generate_narration(text=text, voice=voice or self.default_voice, output_path=output_path)

    async def generate_audio(
        self,
        text: str,
        voice: Optional[str] = None,
        output_path: Optional[str] = None,
        output_file: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        dest = output_path or output_file
        return await self.generate_narration(text=text, voice=voice, output_path=dest)

    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        output_path: Optional[str] = None,
        output_file: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        dest = output_path or output_file
        return await self.generate_narration(text=text, voice=voice, output_path=dest)

