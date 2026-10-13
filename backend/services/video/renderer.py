"""Video assembly and rendering engine using MoviePy 2.x and Pillow."""
import io
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps
import structlog

from backend.config import settings
from backend.services.image.compositor import _get_font, _wrap_text
from backend.services.video.assets import get_background_music_path
from backend.services.video.script_generator import VideoScript

logger = structlog.get_logger(__name__)

# MoviePy 2.x vs 1.x unified imports
try:
    from moviepy import (
        AudioFileClip,
        CompositeAudioClip,
        CompositeVideoClip,
        ImageClip,
        VideoFileClip,
        concatenate_videoclips,
    )
    MOVIEPY_V2 = True
except ImportError:
    try:
        from moviepy.editor import (
            AudioFileClip,
            CompositeAudioClip,
            CompositeVideoClip,
            ImageClip,
            VideoFileClip,
            concatenate_videoclips,
        )
        MOVIEPY_V2 = False
    except ImportError:
        AudioFileClip = None
        CompositeAudioClip = None
        CompositeVideoClip = None
        ImageClip = None
        VideoFileClip = None
        concatenate_videoclips = None
        MOVIEPY_V2 = False

ASPECT_RATIO_RESOLUTIONS = {
    "9:16": (1080, 1920),
    "16:9": (1920, 1080),
    "1:1": (1080, 1080),
}


class VideoRenderError(Exception):
    """Base exception for video rendering pipeline failures."""
    pass


def _check_ffmpeg_installed() -> bool:
    """Check if ffmpeg executable is available in PATH or imageio-ffmpeg."""
    if shutil.which("ffmpeg") is not None:
        return True
    try:
        import imageio_ffmpeg
        if imageio_ffmpeg.get_ffmpeg_exe():
            return True
    except Exception:
        pass
    return False


def _set_clip_duration(clip, duration: float):
    """Set clip duration supporting both MoviePy 1.x and 2.x."""
    if hasattr(clip, "with_duration"):
        return clip.with_duration(duration)
    return clip.set_duration(duration)


def _set_clip_audio(clip, audio):
    """Set clip audio supporting both MoviePy 1.x and 2.x."""
    if hasattr(clip, "with_audio"):
        return clip.with_audio(audio)
    return clip.set_audio(audio)


def _apply_volume(audio_clip, factor: float):
    """Scale audio volume supporting both MoviePy 1.x and 2.x."""
    if hasattr(audio_clip, "with_volume_scaled"):
        return audio_clip.with_volume_scaled(factor)
    elif hasattr(audio_clip, "volumex"):
        return audio_clip.volumex(factor)
    return audio_clip


def _render_caption_on_image(
    image_bytes: bytes,
    caption_text: str,
    target_size: Tuple[int, int],
) -> Image.Image:
    """Fit/crop image to target dimensions and overlay caption text using Pillow."""
    target_w, target_h = target_size
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    # High-quality fill crop to match aspect ratio exactly
    img = ImageOps.fit(img, (target_w, target_h), Image.Resampling.LANCZOS)
    img_rgba = img.convert("RGBA")

    if not caption_text.strip():
        return img_rgba.convert("RGB")

    overlay = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    scale = min(target_w, target_h) / 1080.0
    font_size = max(24, int(38 * scale))
    font = _get_font(font_size, bold=True)

    pad_x = int(60 * scale)
    max_w = target_w - (pad_x * 2)

    lines = _wrap_text(caption_text, font, max_w, draw)
    if lines:
        line_heights = []
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_heights.append(bbox[3] - bbox[1])

        total_text_h = sum(line_heights) + (len(lines) * int(12 * scale))
        card_pad_y = int(24 * scale)
        card_pad_x = int(32 * scale)

        # Position caption in the bottom 25% of the frame
        card_y0 = target_h - int(240 * scale) - total_text_h
        card_y1 = card_y0 + total_text_h + (card_pad_y * 2)

        draw.rounded_rectangle(
            [pad_x - card_pad_x, card_y0, target_w - pad_x + card_pad_x, card_y1],
            radius=int(16 * scale),
            fill=(0, 0, 0, 185),
        )

        cursor_y = card_y0 + card_pad_y
        for idx, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            lw = bbox[2] - bbox[0]
            # Center line horizontally
            lx = (target_w - lw) // 2
            draw.text((lx, cursor_y), line, font=font, fill="#FFFFFF")
            cursor_y += line_heights[idx] + int(12 * scale)

    composed = Image.alpha_composite(img_rgba, overlay)
    return composed.convert("RGB")


def _apply_ken_burns(clip, duration: float, zoom_in: bool = True):
    """Apply slow, cinematic Ken Burns zoom effect to an image clip."""
    try:
        if zoom_in:
            zoom_func = lambda t: 1.0 + 0.05 * (t / max(0.1, duration))
        else:
            zoom_func = lambda t: 1.05 - 0.05 * (t / max(0.1, duration))

        if hasattr(clip, "resized"):
            return clip.resized(zoom_func)
        elif hasattr(clip, "resize"):
            return clip.resize(zoom_func)
        return clip
    except Exception as e:
        logger.debug("ken_burns_skipped", error=str(e))
        return clip


def generate_thumbnail(video_path: str, output_path: str) -> str:
    """Extract a representative thumbnail frame from rendered video.
    
    Args:
        video_path: Path to MP4 source video.
        output_path: Path to target JPEG thumbnail.

    Returns:
        Absolute string path to created thumbnail.
    """
    if ImageClip is None:
        raise VideoRenderError("MoviePy library is not available.")

    clip = None
    try:
        clip = VideoFileClip(video_path)
        timestamp = min(1.0, max(0.1, clip.duration / 2))
        frame = clip.get_frame(timestamp)
        thumbnail_img = Image.fromarray(frame)
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        thumbnail_img.save(output_path, format="JPEG", quality=85)
        return str(Path(output_path).resolve())
    except Exception as e:
        raise VideoRenderError(f"Failed to generate thumbnail: {e}") from e
    finally:
        if clip:
            try:
                clip.close()
            except Exception:
                pass


def render_video(
    script: VideoScript,
    scene_images: List[bytes],
    narration_path: Optional[str] = None,
    output_path: str = "output.mp4",
    aspect_ratio: str = "9:16",
    include_music: bool = True,
) -> str:
    """Render a complete MP4 commercial video from script, images, and audio.
    
    Args:
        script: Validated VideoScript model.
        scene_images: List of raw image bytes for each scene in script.
        narration_path: Optional path to narration voice MP3.
        output_path: Target MP4 output path.
        aspect_ratio: Resolution aspect ratio ("9:16", "16:9", or "1:1").
        include_music: Whether to blend background music.

    Returns:
        Absolute path to rendered video MP4.
    """
    if ImageClip is None:
        raise VideoRenderError("MoviePy library is not installed or importable.")

    if not _check_ffmpeg_installed():
        raise VideoRenderError(
            "FFmpeg executable not detected. Ensure ffmpeg is installed and available in PATH."
        )

    if not scene_images:
        raise VideoRenderError("No scene images provided for video rendering.")

    target_resolution = ASPECT_RATIO_RESOLUTIONS.get(aspect_ratio, (1080, 1920))
    dest_path = Path(output_path).resolve()
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    temp_files: List[str] = []
    clips = []
    final_video = None
    audio_clips = []

    try:
        logger.info(
            "render_video_start",
            scenes_count=len(script.scenes),
            images_count=len(scene_images),
            aspect_ratio=aspect_ratio,
            output_path=str(dest_path),
        )

        # 1. Build video clips for each scene
        for i, scene in enumerate(script.scenes):
            img_bytes = scene_images[i % len(scene_images)]
            duration = max(1.0, float(scene.duration_seconds))

            # Compose caption onto image frame using Pillow
            annotated_img = _render_caption_on_image(
                image_bytes=img_bytes,
                caption_text=scene.narration_text,
                target_size=target_resolution,
            )

            # Save frame to temp file for MoviePy ImageClip
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
                annotated_img.save(tf.name, format="PNG")
                temp_frame_path = tf.name
                temp_files.append(temp_frame_path)

            clip = ImageClip(temp_frame_path)
            clip = _set_clip_duration(clip, duration)

            # Ken Burns alternating zoom in / zoom out
            zoom_in = (i % 2 == 0)
            clip = _apply_ken_burns(clip, duration, zoom_in=zoom_in)

            # Crossfade transition if supported
            if hasattr(clip, "crossfadein") and i > 0:
                clip = clip.crossfadein(0.4)

            clips.append(clip)

        # Concatenate scenes
        try:
            final_video = concatenate_videoclips(clips, method="compose")
        except Exception:
            final_video = concatenate_videoclips(clips)

        total_video_duration = final_video.duration

        # 2. Audio assembly
        # Narration audio
        if narration_path and os.path.exists(narration_path):
            narration_clip = AudioFileClip(narration_path)
            # Clip or pad narration to match video duration
            if narration_clip.duration > total_video_duration:
                narration_clip = _set_clip_duration(narration_clip, total_video_duration)
            audio_clips.append(narration_clip)

        # Background music
        if include_music:
            bgm_path = get_background_music_path()
            if bgm_path and os.path.exists(bgm_path):
                bgm_clip = AudioFileClip(bgm_path)
                bgm_clip = _apply_volume(bgm_clip, 0.15)  # 15% volume behind speech
                # Loop or trim music to total duration
                if hasattr(bgm_clip, "loop"):
                    bgm_clip = bgm_clip.loop(duration=total_video_duration)
                else:
                    bgm_clip = _set_clip_duration(bgm_clip, total_video_duration)
                audio_clips.append(bgm_clip)

        # Attach combined audio
        if audio_clips:
            if len(audio_clips) == 1:
                combined_audio = audio_clips[0]
            else:
                combined_audio = CompositeAudioClip(audio_clips)
            final_video = _set_clip_audio(final_video, combined_audio)

        # 3. Write video file
        fps = getattr(settings, "DEFAULT_VIDEO_FPS", 30)
        has_audio = bool(audio_clips) and getattr(final_video, "audio", None) is not None
        write_kwargs = {
            "fps": fps,
            "codec": "libx264",
            "preset": "medium",
            "threads": 4,
            "logger": None,
        }
        if has_audio:
            write_kwargs["audio_codec"] = "aac"
        else:
            write_kwargs["audio"] = False

        final_video.write_videofile(
            str(dest_path),
            **write_kwargs,
        )

        logger.info(
            "render_video_completed",
            output_path=str(dest_path),
            file_size=os.path.getsize(dest_path),
            duration=total_video_duration,
        )
        return str(dest_path)

    except Exception as e:
        logger.error("render_video_failed", error=str(e))
        raise VideoRenderError(f"MoviePy rendering failed: {e}") from e

    finally:
        # Clean up moviepy resources and temporary frame files
        if final_video:
            try:
                final_video.close()
            except Exception:
                pass
        for c in clips:
            try:
                c.close()
            except Exception:
                pass
        for a in audio_clips:
            try:
                a.close()
            except Exception:
                pass
        for tmp_file in temp_files:
            try:
                if os.path.exists(tmp_file):
                    os.remove(tmp_file)
            except Exception:
                pass


class VideoRenderer:
    """Service wrapper for MoviePy video timeline assembly."""

    def __init__(self) -> None:
        pass

    async def render_video(
        self,
        scenes: Optional[List[Any]] = None,
        image_paths: Optional[List[str]] = None,
        audio_paths: Optional[List[Optional[str]]] = None,
        output_path: str = "output.mp4",
        include_music: bool = False,
        script: Optional[Any] = None,
        scene_images: Optional[List[bytes]] = None,
        narration_path: Optional[str] = None,
        aspect_ratio: str = "9:16",
        **kwargs: Any,
    ) -> str:
        """Render video supporting both VideoAgent and service-level signatures."""
        dest_path = Path(output_path).resolve()
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Case 1: Called with image_paths and scenes from VideoAgent
        if image_paths and scenes:
            try:
                import moviepy as mp

                clips = []
                for idx, img_path in enumerate(image_paths):
                    dur = 4.0
                    if idx < len(scenes):
                        scene_obj = scenes[idx]
                        dur = getattr(scene_obj, "duration_seconds", 4.0)
                        if isinstance(scene_obj, dict):
                            dur = scene_obj.get("duration_seconds", 4.0)

                    clip = mp.ImageClip(img_path)
                    clip = clip.with_duration(dur) if hasattr(clip, "with_duration") else clip.set_duration(dur)

                    # Attach audio if available
                    if audio_paths and idx < len(audio_paths) and audio_paths[idx] and os.path.exists(audio_paths[idx]):
                        try:
                            audio_clip = mp.AudioFileClip(audio_paths[idx])
                            clip = clip.with_audio(audio_clip) if hasattr(clip, "with_audio") else clip.set_audio(audio_clip)
                        except Exception:
                            pass
                    clips.append(clip)

                if clips:
                    try:
                        concat = mp.concatenate_videoclips(clips, method="compose")
                    except Exception:
                        concat = mp.concatenate_videoclips(clips)

                    has_audio = (audio_paths and any(audio_paths)) and getattr(concat, "audio", None) is not None
                    write_kwargs = {
                        "fps": 24,
                        "codec": "libx264",
                        "logger": None,
                    }
                    if has_audio:
                        write_kwargs["audio_codec"] = "aac"
                    else:
                        write_kwargs["audio"] = False

                    concat.write_videofile(
                        str(dest_path),
                        **write_kwargs,
                    )
                    concat.close()
                    for c in clips:
                        c.close()

                    if dest_path.is_file() and dest_path.stat().st_size > 0:
                        return str(dest_path)
            except Exception as e:
                logger.warning("moviepy_class_render_failed", error=str(e))

        # Case 2: Called with script and scene_images bytes
        if script and scene_images:
            return render_video(
                script=script,
                scene_images=scene_images,
                narration_path=narration_path,
                output_path=str(dest_path),
                aspect_ratio=aspect_ratio,
                include_music=include_music,
            )

        return str(dest_path)

