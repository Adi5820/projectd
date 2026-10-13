"""Background job worker for executing AI generation tasks."""

import asyncio
from datetime import datetime
import os
from pathlib import Path
from typing import Any, Optional
from bson import ObjectId
import structlog

from backend.db.mongodb import get_database
from backend.db.repositories.ad_repo import AdRepository
from backend.db.repositories.campaign_repo import CampaignRepository
from backend.db.repositories.job_repo import JobRepository
from backend.jobs.manager import JobManager
from backend.models.ad_copy import AdCopyInDB, AdVariation
from backend.models.campaign import CampaignStatus
from backend.models.job import JobResult, JobStatus
from backend.models.poster import PosterInDB
from backend.models.video import VideoInDB, VideoScript as VideoScriptModel
from backend.services.storage.media import get_media_storage

logger = structlog.get_logger(__name__)


async def run_full_generation_job(campaign_id: str, job_id: str) -> None:
    """Execute full 5-stage generation pipeline in background task."""
    db = get_database()
    campaign_repo = CampaignRepository(db)
    job_repo = JobRepository(db)
    ad_repo = AdRepository(db)
    job_manager = JobManager(job_repo)
    media_storage = get_media_storage()

    logger.info("Starting background full generation job", campaign_id=campaign_id, job_id=job_id)
    await job_manager.start_job(job_id)
    await campaign_repo.update_status(campaign_id, CampaignStatus.GENERATING)

    try:
        from backend.api.dependencies import get_orchestrator
        orchestrator = get_orchestrator()

        campaign = await campaign_repo.get_by_id(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign with ID '{campaign_id}' not found")

        campaign_dict = campaign.model_dump()

        # Run multi-agent orchestrator pipeline
        pipeline_result = await orchestrator.run_full_pipeline(
            campaign_data=campaign_dict,
            job_id=job_id,
            job_manager=job_manager,
        )

        job_result = JobResult()

        # 1. Persist Ad Copy Variations
        ad_copy_data = pipeline_result.get("ad_copy", {})
        if isinstance(ad_copy_data, dict) and "variations" in ad_copy_data:
            variations = []
            for v in ad_copy_data.get("variations", []):
                if isinstance(v, dict):
                    variations.append(AdVariation(**v))
                elif hasattr(v, "model_dump"):
                    variations.append(AdVariation(**v.model_dump()))

            if variations:
                ad_doc = AdCopyInDB(
                    campaign_id=campaign_id,
                    variations=variations,
                    target_audience=campaign.target_audience,
                    tone=campaign.tone,
                    key_selling_points=pipeline_result.get("campaign_understanding", {}).get("key_selling_points", []),
                    created_at=datetime.utcnow(),
                )
                inserted_ad = await db.ad_copies.insert_one(ad_doc.model_dump(by_alias=True))
                job_result.ad_copy_id = str(inserted_ad.inserted_id)
                logger.info("Persisted ad copy variations to MongoDB", ad_id=job_result.ad_copy_id)

        # 2. Persist Poster
        poster_data = pipeline_result.get("poster", {})
        if isinstance(poster_data, dict) and "image_bytes" in poster_data:
            image_bytes = poster_data["image_bytes"]
            if isinstance(image_bytes, bytes) and len(image_bytes) > 0:
                saved_url = await media_storage.save(
                    data=image_bytes,
                    filename=f"poster_{campaign_id}.jpg",
                    content_type="image/jpeg",
                    category="posters",
                )

                poster_doc = {
                    "campaign_id": campaign_id,
                    "image_url": saved_url,
                    "prompt": poster_data.get("prompt_used", ""),
                    "aspect_ratio": poster_data.get("aspect_ratio", "1:1"),
                    "platform": campaign.platforms[0] if campaign.platforms else "instagram",
                    "width": poster_data.get("dimensions", {}).get("width", 1024),
                    "height": poster_data.get("dimensions", {}).get("height", 1024),
                    "model_used": poster_data.get("model_used", "FLUX.1-schnell"),
                    "created_at": datetime.utcnow(),
                }
                inserted_poster = await db.posters.insert_one(poster_doc)
                job_result.poster_id = str(inserted_poster.inserted_id)
                logger.info("Persisted poster to MongoDB", poster_id=job_result.poster_id, url=saved_url)

        # 3. Persist Video
        video_data = pipeline_result.get("video", {})
        if isinstance(video_data, dict):
            video_path = video_data.get("video_path")
            thumbnail_path = video_data.get("thumbnail_path")

            video_url = ""
            thumbnail_url = ""

            if video_path and os.path.exists(video_path) and os.path.getsize(video_path) > 0:
                with open(video_path, "rb") as vf:
                    video_bytes = vf.read()
                video_url = await media_storage.save(
                    data=video_bytes,
                    filename=f"ad_video_{campaign_id}.mp4",
                    content_type="video/mp4",
                    category="videos",
                )

            if thumbnail_path and os.path.exists(thumbnail_path) and os.path.getsize(thumbnail_path) > 0:
                with open(thumbnail_path, "rb") as tf:
                    thumb_bytes = tf.read()
                thumbnail_url = await media_storage.save(
                    data=thumb_bytes,
                    filename=f"thumb_{campaign_id}.jpg",
                    content_type="image/jpeg",
                    category="thumbnails",
                )

            if video_url:
                video_doc = {
                    "campaign_id": campaign_id,
                    "video_url": video_url,
                    "thumbnail_url": thumbnail_url,
                    "duration": video_data.get("duration_seconds", 15.0),
                    "platform": campaign.platforms[0] if campaign.platforms else "instagram",
                    "script": video_data.get("script", {}),
                    "created_at": datetime.utcnow(),
                }
                inserted_video = await db.videos.insert_one(video_doc)
                job_result.video_id = str(inserted_video.inserted_id)
                logger.info("Persisted video to MongoDB", video_id=job_result.video_id, url=video_url)

        # Mark campaign and job completed
        await campaign_repo.update_status(campaign_id, CampaignStatus.COMPLETED)
        await job_manager.complete_job(job_id, result=job_result)
        logger.info("Completed full generation background job successfully", job_id=job_id)

    except Exception as exc:
        logger.error("Full generation background job failed", job_id=job_id, error=str(exc))
        await campaign_repo.update_status(campaign_id, CampaignStatus.FAILED)
        await job_manager.fail_job(job_id, str(exc))


async def run_ad_copy_generation_job(
    campaign_id: str,
    job_id: str,
    platform: str = "instagram",
    num_variations: int = 3,
) -> None:
    """Execute targeted ad copy generation job in background."""
    db = get_database()
    campaign_repo = CampaignRepository(db)
    job_repo = JobRepository(db)
    job_manager = JobManager(job_repo)

    await job_manager.start_job(job_id)

    try:
        from backend.api.dependencies import get_orchestrator
        orchestrator = get_orchestrator()

        campaign = await campaign_repo.get_by_id(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign with ID '{campaign_id}' not found")

        copy_result = await orchestrator.run_copy_only(
            campaign_data=campaign.model_dump(),
            job_id=job_id,
            job_manager=job_manager,
            num_variations=num_variations,
        )

        ad_data = copy_result.get("ad_copy", {})
        variations = []
        for v in ad_data.get("variations", []):
            if isinstance(v, dict):
                variations.append(AdVariation(**v))
            elif hasattr(v, "model_dump"):
                variations.append(AdVariation(**v.model_dump()))

        ad_doc = AdCopyInDB(
            campaign_id=campaign_id,
            variations=variations,
            target_audience=campaign.target_audience,
            tone=campaign.tone,
            key_selling_points=copy_result.get("campaign_understanding", {}).get("key_selling_points", []),
            created_at=datetime.utcnow(),
        )
        inserted = await db.ad_copies.insert_one(ad_doc.model_dump(by_alias=True))
        job_res = JobResult(ad_copy_id=str(inserted.inserted_id))
        await job_manager.complete_job(job_id, result=job_res)

    except Exception as exc:
        logger.error("Ad copy generation job failed", job_id=job_id, error=str(exc))
        await job_manager.fail_job(job_id, str(exc))


async def run_poster_generation_job(
    campaign_id: str,
    job_id: str,
    aspect_ratio: str = "1:1",
    platform: str = "instagram",
) -> None:
    """Execute targeted poster generation job in background."""
    db = get_database()
    campaign_repo = CampaignRepository(db)
    job_repo = JobRepository(db)
    job_manager = JobManager(job_repo)
    media_storage = get_media_storage()

    await job_manager.start_job(job_id)

    try:
        from backend.api.dependencies import get_orchestrator
        orchestrator = get_orchestrator()

        campaign = await campaign_repo.get_by_id(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign with ID '{campaign_id}' not found")

        poster_res = await orchestrator.run_poster_only(
            campaign_data=campaign.model_dump(),
            poster_request={"aspect_ratio": aspect_ratio, "platform": platform},
            job_id=job_id,
            job_manager=job_manager,
        )

        poster_data = poster_res.get("poster", {})
        image_bytes = poster_data.get("image_bytes")

        if not image_bytes:
            raise ValueError("No image bytes returned from poster generator")

        saved_url = await media_storage.save(
            data=image_bytes,
            filename=f"poster_{campaign_id}_{aspect_ratio.replace(':', 'x')}.jpg",
            content_type="image/jpeg",
            category="posters",
        )

        poster_doc = {
            "campaign_id": campaign_id,
            "image_url": saved_url,
            "prompt": poster_data.get("prompt_used", ""),
            "aspect_ratio": aspect_ratio,
            "platform": platform,
            "width": poster_data.get("dimensions", {}).get("width", 1024),
            "height": poster_data.get("dimensions", {}).get("height", 1024),
            "model_used": poster_data.get("model_used", "FLUX.1-schnell"),
            "created_at": datetime.utcnow(),
        }
        inserted = await db.posters.insert_one(poster_doc)
        job_res = JobResult(poster_id=str(inserted.inserted_id))
        await job_manager.complete_job(job_id, result=job_res)

    except Exception as exc:
        logger.error("Poster generation job failed", job_id=job_id, error=str(exc))
        await job_manager.fail_job(job_id, str(exc))


async def run_video_generation_job(
    campaign_id: str,
    job_id: str,
    duration: int = 15,
    platform: str = "instagram",
) -> None:
    """Execute targeted video commercial generation job in background."""
    db = get_database()
    campaign_repo = CampaignRepository(db)
    job_repo = JobRepository(db)
    job_manager = JobManager(job_repo)
    media_storage = get_media_storage()

    await job_manager.start_job(job_id)

    try:
        from backend.api.dependencies import get_orchestrator
        orchestrator = get_orchestrator()

        campaign = await campaign_repo.get_by_id(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign with ID '{campaign_id}' not found")

        video_res = await orchestrator.run_video_only(
            campaign_data=campaign.model_dump(),
            video_request={"duration": duration, "platform": platform},
            job_id=job_id,
            job_manager=job_manager,
        )

        video_data = video_res.get("video", {})
        video_path = video_data.get("video_path")
        thumbnail_path = video_data.get("thumbnail_path")

        if not video_path or not os.path.exists(video_path):
            raise ValueError(f"Rendered video file not found at '{video_path}'")

        with open(video_path, "rb") as vf:
            video_bytes = vf.read()
        video_url = await media_storage.save(
            data=video_bytes,
            filename=f"video_{campaign_id}_{duration}s.mp4",
            content_type="video/mp4",
            category="videos",
        )

        thumbnail_url = ""
        if thumbnail_path and os.path.exists(thumbnail_path):
            with open(thumbnail_path, "rb") as tf:
                thumb_bytes = tf.read()
            thumbnail_url = await media_storage.save(
                data=thumb_bytes,
                filename=f"thumb_{campaign_id}.jpg",
                content_type="image/jpeg",
                category="thumbnails",
            )

        video_doc = {
            "campaign_id": campaign_id,
            "video_url": video_url,
            "thumbnail_url": thumbnail_url,
            "duration": float(duration),
            "platform": platform,
            "script": video_data.get("script", {}),
            "created_at": datetime.utcnow(),
        }
        inserted = await db.videos.insert_one(video_doc)
        job_res = JobResult(video_id=str(inserted.inserted_id))
        await job_manager.complete_job(job_id, result=job_res)

    except Exception as exc:
        logger.error("Video generation job failed", job_id=job_id, error=str(exc))
        await job_manager.fail_job(job_id, str(exc))
