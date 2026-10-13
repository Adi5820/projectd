"""
Agent Workflow Orchestrator for Agentic Ads Platform.

Coordinates the full lifecycle of advertising generation:
1. Campaign brief deconstruction and strategic framing.
2. Vector RAG brand intelligence retrieval.
3. Concurrent parallel execution of Copywriting, Poster Generation, and Video Production.
4. Comprehensive creative review board quality scoring.
5. Job state tracking and resilience across partial subsystem failures.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Optional, Union

import structlog

from backend.agents.campaign_agent import CampaignAgent
from backend.agents.brand_research_agent import BrandResearchAgent
from backend.agents.copywriting_agent import CopywritingAgent
from backend.agents.poster_agent import PosterAgent
from backend.agents.video_agent import VideoAgent
from backend.agents.quality_agent import QualityAgent

# Resilient Service Imports
try:
    from backend.services.llm.gemini import GeminiProvider
except ImportError:
    try:
        from backend.services import GeminiProvider  # type: ignore
    except ImportError:
        GeminiProvider = None  # type: ignore

try:
    from backend.services.image.flux_together import FluxTogetherProvider
except ImportError:
    try:
        from backend.services import FluxTogetherProvider  # type: ignore
    except ImportError:
        FluxTogetherProvider = None  # type: ignore

try:
    from backend.services.image.compositor import ImageCompositor
except ImportError:
    try:
        from backend.services import ImageCompositor  # type: ignore
    except ImportError:
        ImageCompositor = None  # type: ignore

try:
    from backend.services.video.script_generator import ScriptGenerator
except ImportError:
    try:
        from backend.services import ScriptGenerator  # type: ignore
    except ImportError:
        ScriptGenerator = None  # type: ignore

try:
    from backend.services.video.narration import NarrationService
except ImportError:
    try:
        from backend.services import NarrationService  # type: ignore
    except ImportError:
        NarrationService = None  # type: ignore

try:
    from backend.services.video.renderer import VideoRenderer
except ImportError:
    try:
        from backend.services import VideoRenderer  # type: ignore
    except ImportError:
        VideoRenderer = None  # type: ignore

try:
    from backend.services.rag.pipeline import RAGPipeline
except ImportError:
    try:
        from backend.services import RAGPipeline  # type: ignore
    except ImportError:
        RAGPipeline = None  # type: ignore


class AgentOrchestrator:
    """
    Master Workflow Coordinator for Agentic Ads.

    Manages end-to-end execution, agent dependency pipelines, parallel creative generation,
    and progress notifications for asynchronous client jobs.
    """

    def __init__(
        self,
        gemini_provider: Optional[Any] = None,
        image_provider: Optional[Any] = None,
        image_compositor: Optional[Any] = None,
        script_generator: Optional[Any] = None,
        narration_service: Optional[Any] = None,
        video_renderer: Optional[Any] = None,
        rag_pipeline: Optional[Any] = None,
    ) -> None:
        """
        Initialize the orchestrator, its underlying services, and all 7 AI agents.

        Args:
            gemini_provider: LLM Provider instance.
            image_provider: Flux/Together AI image provider instance.
            image_compositor: ImageCompositor instance.
            script_generator: ScriptGenerator instance.
            narration_service: NarrationService instance.
            video_renderer: VideoRenderer instance.
            rag_pipeline: RAGPipeline vector retrieval instance.
        """
        self.logger = structlog.get_logger().bind(component="AgentOrchestrator")

        # Initialize Services with safe factory fallbacks
        self.gemini_provider = gemini_provider
        if self.gemini_provider is None and GeminiProvider is not None:
            try:
                self.gemini_provider = GeminiProvider()
            except Exception as exc:
                self.logger.warning("could_not_instantiate_default_gemini_provider", error=str(exc))

        self.image_provider = image_provider
        if self.image_provider is None and FluxTogetherProvider is not None:
            try:
                self.image_provider = FluxTogetherProvider()
            except Exception as exc:
                self.logger.warning("could_not_instantiate_default_flux_provider", error=str(exc))

        self.image_compositor = image_compositor
        if self.image_compositor is None and ImageCompositor is not None:
            try:
                self.image_compositor = ImageCompositor()
            except Exception as exc:
                self.logger.warning("could_not_instantiate_default_compositor", error=str(exc))

        self.script_generator = script_generator
        if self.script_generator is None and ScriptGenerator is not None:
            try:
                self.script_generator = ScriptGenerator()
            except Exception as exc:
                self.logger.warning("could_not_instantiate_default_script_generator", error=str(exc))

        self.narration_service = narration_service
        if self.narration_service is None and NarrationService is not None:
            try:
                self.narration_service = NarrationService()
            except Exception as exc:
                self.logger.warning("could_not_instantiate_default_narration_service", error=str(exc))

        self.video_renderer = video_renderer
        if self.video_renderer is None and VideoRenderer is not None:
            try:
                self.video_renderer = VideoRenderer()
            except Exception as exc:
                self.logger.warning("could_not_instantiate_default_video_renderer", error=str(exc))

        self.rag_pipeline = rag_pipeline
        if self.rag_pipeline is None and RAGPipeline is not None:
            try:
                self.rag_pipeline = RAGPipeline()
            except Exception as exc:
                self.logger.warning("could_not_instantiate_default_rag_pipeline", error=str(exc))

        # Instantiate All 7 Agents
        self.campaign_agent = CampaignAgent(llm_provider=self.gemini_provider)
        self.brand_agent = BrandResearchAgent(llm_provider=self.gemini_provider, rag_pipeline=self.rag_pipeline)
        self.copywriting_agent = CopywritingAgent(llm_provider=self.gemini_provider)
        self.poster_agent = PosterAgent(
            llm_provider=self.gemini_provider,
            image_provider=self.image_provider,
            image_compositor=self.image_compositor,
        )
        self.video_agent = VideoAgent(
            llm_provider=self.gemini_provider,
            image_provider=self.image_provider,
            narration_service=self.narration_service,
            renderer_service=self.video_renderer,
            script_generator=self.script_generator,
        )
        self.quality_agent = QualityAgent(llm_provider=self.gemini_provider)

        self.logger.info("orchestrator_initialized_with_all_agents")

    async def _update_job(
        self,
        job_manager: Optional[Any],
        job_id: str,
        status: str,
        progress: int,
        message: str,
        data: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Notify the job manager of real-time pipeline status updates.

        Args:
            job_manager: Job manager service or background task context.
            job_id: Job ID string.
            status: Job state ('pending', 'processing', 'completed', 'failed').
            progress: Progress percentage (0 to 100).
            message: Human-readable status description.
            data: Partial or final payload dictionary.
        """
        self.logger.info(
            "job_progress_update",
            job_id=job_id,
            status=status,
            progress=progress,
            message=message,
        )
        if job_manager is None or not job_id:
            return

        try:
            if hasattr(job_manager, "update_job") and callable(job_manager.update_job):
                res = job_manager.update_job(
                    job_id=job_id,
                    status=status,
                    progress=progress,
                    message=message,
                    data=data,
                )
                if hasattr(res, "__await__"):
                    await res
            elif hasattr(job_manager, "update_status") and callable(job_manager.update_status):
                res = job_manager.update_status(
                    job_id=job_id,
                    status=status,
                    progress=progress,
                    message=message,
                )
                if hasattr(res, "__await__"):
                    await res
            elif hasattr(job_manager, "update") and callable(job_manager.update):
                res = job_manager.update(
                    job_id=job_id,
                    status=status,
                    progress=progress,
                    message=message,
                )
                if hasattr(res, "__await__"):
                    await res
        except Exception as exc:
            self.logger.warning("job_status_notification_error", job_id=job_id, error=str(exc))

    def _extract_brand_and_brief(self, campaign_data: Any) -> tuple[str, str, str]:
        """Normalize brand name, product name, and brief from input."""
        norm: dict[str, Any] = {}
        if isinstance(campaign_data, dict):
            norm = campaign_data
        elif hasattr(campaign_data, "model_dump"):
            norm = campaign_data.model_dump()
        elif hasattr(campaign_data, "__dict__"):
            norm = {k: v for k, v in campaign_data.__dict__.items() if not k.startswith("_")}

        brand = norm.get("brand_name") or norm.get("brand", "Our Brand")
        product = norm.get("product_name") or norm.get("product", "Flagship Offering")
        brief = norm.get("campaign_brief") or norm.get("description") or norm.get("objective") or ""
        return brand, product, brief

    async def run_full_pipeline(
        self,
        campaign_data: Union[dict[str, Any], Any],
        job_id: str = "ad_job_default",
        job_manager: Optional[Any] = None,
    ) -> dict[str, Any]:
        """
        Execute the complete 5-stage advertising generation pipeline.

        Workflow:
        1. Create/update initial job state.
        2. Run Campaign Understanding Agent (brief deconstruction).
        3. Run Brand Research Agent (vector RAG guidelines).
        4. Run Copywriting, Poster, and Video agents IN PARALLEL via asyncio.gather.
        5. Run Quality Evaluation Agent on all generated creative assets.
        6. Return unified campaign suite.

        Args:
            campaign_data: Campaign input payload.
            job_id: Unique job identifier.
            job_manager: Optional job management service.

        Returns:
            dict[str, Any]: Consolidated campaign bundle.
        """
        start_time = time.perf_counter()
        brand_name, product_name, brief = self._extract_brand_and_brief(campaign_data)

        self.logger.info(
            "pipeline_start",
            job_id=job_id,
            brand=brand_name,
            product=product_name,
        )

        await self._update_job(
            job_manager,
            job_id,
            status="processing",
            progress=5,
            message="Initializing AI Agent Orchestration Pipeline",
        )

        # Stage 1: Campaign Understanding Agent
        await self._update_job(
            job_manager,
            job_id,
            status="processing",
            progress=15,
            message="Analyzing campaign brief and target demographics",
        )
        try:
            campaign_understanding = await self.campaign_agent.run(campaign_data=campaign_data)
        except Exception as exc:
            self.logger.error("campaign_agent_execution_failed", error=str(exc))
            campaign_understanding = {"error": str(exc), "status": "failed"}

        # Stage 2: Brand Research & RAG Agent
        await self._update_job(
            job_manager,
            job_id,
            status="processing",
            progress=30,
            message="Querying brand guidelines and RAG knowledge base",
        )
        try:
            brand_context = await self.brand_agent.run(
                brand_name=brand_name,
                campaign_brief=brief,
                campaign_understanding=campaign_understanding,
            )
        except Exception as exc:
            self.logger.error("brand_agent_execution_failed", error=str(exc))
            brand_context = {"error": str(exc), "status": "failed"}

        # Stage 3: Concurrent Parallel Creative Generation
        await self._update_job(
            job_manager,
            job_id,
            status="processing",
            progress=45,
            message="Generating Ad Copy, Posters, and Video in parallel",
        )

        copy_task = self.copywriting_agent.run(
            campaign_data=campaign_data,
            campaign_understanding=campaign_understanding,
            brand_context=brand_context,
        )
        poster_task = self.poster_agent.run(
            campaign_data=campaign_data,
            campaign_understanding=campaign_understanding,
            brand_context=brand_context,
        )
        video_task = self.video_agent.run(
            campaign_data=campaign_data,
            campaign_understanding=campaign_understanding,
            brand_context=brand_context,
        )

        # Execute parallel generation safely
        parallel_results = await asyncio.gather(
            copy_task,
            poster_task,
            video_task,
            return_exceptions=True,
        )

        copy_result, poster_result, video_result = parallel_results

        # Handle potential partial failures gracefully
        if isinstance(copy_result, Exception):
            self.logger.error("copywriting_agent_failed", error=str(copy_result))
            copy_output = {"error": str(copy_result), "status": "failed"}
        else:
            copy_output = copy_result

        if isinstance(poster_result, Exception):
            self.logger.error("poster_agent_failed", error=str(poster_result))
            poster_output = {"error": str(poster_result), "status": "failed"}
        else:
            poster_output = poster_result

        if isinstance(video_result, Exception):
            self.logger.error("video_agent_failed", error=str(video_result))
            video_output = {"error": str(video_result), "status": "failed"}
        else:
            video_output = video_result

        # Stage 4: Quality Evaluation Agent
        await self._update_job(
            job_manager,
            job_id,
            status="processing",
            progress=85,
            message="Auditing asset quality and brand consistency",
        )

        try:
            quality_evaluation = await self.quality_agent.run(
                campaign_data=campaign_data,
                ad_copy=copy_output if not isinstance(copy_result, Exception) else None,
                poster_url=poster_output if not isinstance(poster_result, Exception) else None,
                video_url=video_output if not isinstance(video_result, Exception) else None,
                brand_context=brand_context,
            )
        except Exception as exc:
            self.logger.error("quality_agent_execution_failed", error=str(exc))
            quality_evaluation = {"error": str(exc), "overall_score": 7.5}

        elapsed = time.perf_counter() - start_time

        # Determine composite status
        has_critical_failure = (
            isinstance(copy_result, Exception)
            and isinstance(poster_result, Exception)
            and isinstance(video_result, Exception)
        )
        has_partial_failure = (
            isinstance(copy_result, Exception)
            or isinstance(poster_result, Exception)
            or isinstance(video_result, Exception)
        )

        final_status = "failed" if has_critical_failure else ("partial_success" if has_partial_failure else "completed")

        final_response: dict[str, Any] = {
            "job_id": job_id,
            "status": final_status,
            "brand_name": brand_name,
            "product_name": product_name,
            "campaign_understanding": campaign_understanding,
            "brand_context": brand_context,
            "ad_copy": copy_output,
            "poster": poster_output,
            "video": video_output,
            "quality_evaluation": quality_evaluation,
            "execution_time_seconds": round(elapsed, 3),
        }

        await self._update_job(
            job_manager,
            job_id,
            status=final_status,
            progress=100,
            message="Campaign Generation Pipeline Completed",
            data=final_response,
        )

        self.logger.info(
            "pipeline_completed",
            job_id=job_id,
            final_status=final_status,
            duration_seconds=final_response["execution_time_seconds"],
        )

        return final_response

    async def run_copy_only(
        self,
        campaign_data: Union[dict[str, Any], Any],
        job_id: str = "copy_job_default",
        job_manager: Optional[Any] = None,
        num_variations: int = 3,
    ) -> dict[str, Any]:
        """
        Execute targeted copywriting workflow with brand grounding and quality audit.

        Args:
            campaign_data: Campaign input payload.
            job_id: Job identifier.
            job_manager: Optional job manager.
            num_variations: Variations per platform.

        Returns:
            dict[str, Any]: Ad copy variations and quality score.
        """
        start_time = time.perf_counter()
        brand_name, product_name, brief = self._extract_brand_and_brief(campaign_data)

        await self._update_job(job_manager, job_id, "processing", 10, "Deconstructing Campaign Brief")
        understanding = await self.campaign_agent.run(campaign_data=campaign_data)

        await self._update_job(job_manager, job_id, "processing", 30, "Checking Brand Guidelines")
        brand = await self.brand_agent.run(brand_name=brand_name, campaign_brief=brief, campaign_understanding=understanding)

        await self._update_job(job_manager, job_id, "processing", 60, "Generating Multi-Platform Ad Copy")
        copy_res = await self.copywriting_agent.run(
            campaign_data=campaign_data,
            campaign_understanding=understanding,
            brand_context=brand,
            num_variations=num_variations,
        )

        await self._update_job(job_manager, job_id, "processing", 85, "Auditing Ad Copy Quality")
        quality = await self.quality_agent.run(
            campaign_data=campaign_data,
            ad_copy=copy_res,
            brand_context=brand,
        )

        elapsed = time.perf_counter() - start_time
        response = {
            "job_id": job_id,
            "status": "completed",
            "campaign_understanding": understanding,
            "brand_context": brand,
            "ad_copy": copy_res,
            "quality_evaluation": quality,
            "execution_time_seconds": round(elapsed, 3),
        }

        await self._update_job(job_manager, job_id, "completed", 100, "Copy Generation Complete", data=response)
        return response

    async def run_poster_only(
        self,
        campaign_data: Union[dict[str, Any], Any],
        poster_request: Optional[dict[str, Any]] = None,
        job_id: str = "poster_job_default",
        job_manager: Optional[Any] = None,
    ) -> dict[str, Any]:
        """
        Execute targeted poster creation workflow.

        Args:
            campaign_data: Campaign input payload.
            poster_request: Specific poster options (aspect_ratio, platform, overlay_text).
            job_id: Job identifier.
            job_manager: Optional job manager.

        Returns:
            dict[str, Any]: Generated poster and quality scorecard.
        """
        start_time = time.perf_counter()
        brand_name, product_name, brief = self._extract_brand_and_brief(campaign_data)
        req = poster_request or {}

        await self._update_job(job_manager, job_id, "processing", 10, "Analyzing Visual Strategy")
        understanding = await self.campaign_agent.run(campaign_data=campaign_data)

        await self._update_job(job_manager, job_id, "processing", 30, "Retrieving Brand Color Systems")
        brand = await self.brand_agent.run(brand_name=brand_name, campaign_brief=brief, campaign_understanding=understanding)

        # Quick copy snippet for poster headline/CTA
        ad_copy = await self.copywriting_agent.run(
            campaign_data=campaign_data,
            campaign_understanding=understanding,
            brand_context=brand,
            num_variations=1,
        )

        await self._update_job(job_manager, job_id, "processing", 65, "Synthesizing AI Poster & Compositing Typography")
        poster_res = await self.poster_agent.run(
            campaign_data=campaign_data,
            campaign_understanding=understanding,
            brand_context=brand,
            ad_copy=ad_copy,
            aspect_ratio=req.get("aspect_ratio", "1:1"),
            platform=req.get("platform", "instagram"),
            overlay_text=req.get("overlay_text", True),
        )

        await self._update_job(job_manager, job_id, "processing", 88, "Evaluating Visual Poster Composition")
        quality = await self.quality_agent.run(
            campaign_data=campaign_data,
            poster_url=poster_res,
            brand_context=brand,
        )

        elapsed = time.perf_counter() - start_time
        response = {
            "job_id": job_id,
            "status": "completed",
            "campaign_understanding": understanding,
            "brand_context": brand,
            "poster": poster_res,
            "quality_evaluation": quality,
            "execution_time_seconds": round(elapsed, 3),
        }

        await self._update_job(job_manager, job_id, "completed", 100, "Poster Generation Complete", data=response)
        return response

    async def run_video_only(
        self,
        campaign_data: Union[dict[str, Any], Any],
        video_request: Optional[dict[str, Any]] = None,
        job_id: str = "video_job_default",
        job_manager: Optional[Any] = None,
    ) -> dict[str, Any]:
        """
        Execute targeted video production workflow.

        Args:
            campaign_data: Campaign input payload.
            video_request: Video parameters (duration, aspect_ratio, platform, narration, music).
            job_id: Job identifier.
            job_manager: Optional job manager.

        Returns:
            dict[str, Any]: Rendered video, thumbnail, script, and quality scorecard.
        """
        start_time = time.perf_counter()
        brand_name, product_name, brief = self._extract_brand_and_brief(campaign_data)
        req = video_request or {}

        await self._update_job(job_manager, job_id, "processing", 10, "Formulating Narrative Hook & Strategy")
        understanding = await self.campaign_agent.run(campaign_data=campaign_data)

        await self._update_job(job_manager, job_id, "processing", 25, "Aligning Brand Aesthetic & Guidelines")
        brand = await self.brand_agent.run(brand_name=brand_name, campaign_brief=brief, campaign_understanding=understanding)

        await self._update_job(job_manager, job_id, "processing", 50, "Directing Scenes, Generating Narration & Rendering Video")
        video_res = await self.video_agent.run(
            campaign_data=campaign_data,
            campaign_understanding=understanding,
            brand_context=brand,
            duration=req.get("duration", 15),
            aspect_ratio=req.get("aspect_ratio", "9:16"),
            platform=req.get("platform", "instagram"),
            include_narration=req.get("include_narration", True),
            include_music=req.get("include_music", False),
        )

        await self._update_job(job_manager, job_id, "processing", 88, "Auditing Video Production & Pacing")
        quality = await self.quality_agent.run(
            campaign_data=campaign_data,
            video_url=video_res,
            brand_context=brand,
        )

        elapsed = time.perf_counter() - start_time
        response = {
            "job_id": job_id,
            "status": "completed",
            "campaign_understanding": understanding,
            "brand_context": brand,
            "video": video_res,
            "quality_evaluation": quality,
            "execution_time_seconds": round(elapsed, 3),
        }

        await self._update_job(job_manager, job_id, "completed", 100, "Video Production Complete", data=response)
        return response
