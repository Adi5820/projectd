"""
Brand Research & RAG Agent for Agentic Ads Platform.

Queries the ChromaDB/Vector RAG pipeline for existing brand guidelines, visual identity
systems, past campaign assets, and voice rules. If no pre-indexed documents exist,
it leverages generative LLM brand intelligence to construct a cohesive brand framework.
"""

from __future__ import annotations

import time
from typing import Any, Optional

from pydantic import BaseModel, Field
import structlog

from backend.agents.base import BaseAgent


class BrandContextOutput(BaseModel):
    """Structured brand research and guidelines output."""

    brand_guidelines: str = Field(
        description="Comprehensive visual and editorial guidelines, styling requirements, and rules",
    )
    brand_voice: str = Field(
        description="Detailed brand tone of voice, cadence, and personality traits",
    )
    brand_colors: list[str] = Field(
        default_factory=list,
        description="Primary, secondary, and accent color palette as hex codes or color names",
    )
    previous_campaigns: str = Field(
        description="Historical campaign narrative, past messaging arcs, or benchmark precedents",
    )
    relevant_context: str = Field(
        description="Consolidated factual context assembled from brand documents or strategic intelligence",
    )
    context_sources: list[str] = Field(
        default_factory=list,
        description="Names of documents, knowledge bases, or generative modules used",
    )


class BrandResearchAgent(BaseAgent):
    """
    Brand Research & RAG Agent.

    Retrieves authoritative brand knowledge from vector stores and synthesizes
    actionable creative guardrails for downstream copywriting, poster, and video generation.
    """

    def __init__(
        self,
        llm_provider: Optional[Any] = None,
        rag_pipeline: Optional[Any] = None,
    ) -> None:
        """
        Initialize the Brand Research Agent.

        Args:
            llm_provider: Language model provider instance.
            rag_pipeline: Vector database RAG service instance (e.g., RAGPipeline).
        """
        super().__init__(name="brand_research_agent", llm_provider=llm_provider)
        self.rag_pipeline = rag_pipeline

    def _build_system_prompt(self) -> str:
        """
        Build an expert brand identity director system prompt.

        Returns:
            str: System prompt instructions.
        """
        return (
            "You are a world-class Brand Director and Corporate Identity Strategist with 20+ years of "
            "experience establishing iconic brand bibles for global Fortune 500s and breakout disruptive startups.\n\n"
            "Your mission is to formulate exact brand guidelines, tonal boundaries, visual color schemes, "
            "and historical context for advertising production teams.\n\n"
            "When analyzing brand data:\n"
            "1. Extract or infer the exact brand voice (e.g. 'Authoritative yet approachable', 'Irreverent and bold', "
            "'Quiet luxury and refined minimalism').\n"
            "2. Establish concrete brand colors as hex codes (e.g. ['#0F172A', '#3B82F6', '#10B981', '#FFFFFF']).\n"
            "3. Specify clear do's and don'ts for creative execution.\n"
            "4. Maintain strict continuity with any retrieved company documents or known industry positioning.\n"
            "Always return clean, production-ready brand directives."
        )

    async def _query_rag(
        self,
        brand_name: str,
        query: str,
        rag_service: Optional[Any] = None,
    ) -> tuple[str, list[str]]:
        """
        Query the RAG pipeline service for matching brand documents.

        Args:
            brand_name: The brand identifier.
            query: Semantic search query string.
            rag_service: RAG pipeline instance.

        Returns:
            tuple[str, list[str]]: (Assembled context string, list of source names).
        """
        service = rag_service or self.rag_pipeline
        if service is None:
            return "", []

        self.logger.info("querying_rag_pipeline", brand=brand_name, query_snippet=query[:80])

        try:
            results: Any = None
            # Check various common method signatures for RAG pipelines
            if hasattr(service, "query") and callable(service.query):
                res = service.query(query=query, brand_name=brand_name)
                results = await res if hasattr(res, "__await__") else res
            elif hasattr(service, "search") and callable(service.search):
                res = service.search(query, n_results=5)
                results = await res if hasattr(res, "__await__") else res
            elif hasattr(service, "retrieve") and callable(service.retrieve):
                res = service.retrieve(query=query, limit=5)
                results = await res if hasattr(res, "__await__") else res
            elif hasattr(service, "get_brand_context") and callable(service.get_brand_context):
                res = service.get_brand_context(brand_name)
                results = await res if hasattr(res, "__await__") else res

            if not results:
                return "", []

            context_snippets: list[str] = []
            sources: list[str] = []

            # Handle list of results
            if isinstance(results, list):
                for item in results:
                    if isinstance(item, dict):
                        text = item.get("content") or item.get("text") or item.get("document") or ""
                        source = item.get("source") or item.get("metadata", {}).get("source") or "brand_knowledge_base"
                        if text:
                            context_snippets.append(text)
                        if source and source not in sources:
                            sources.append(str(source))
                    elif isinstance(item, str):
                        context_snippets.append(item)
                    elif hasattr(item, "content"):
                        context_snippets.append(getattr(item, "content", ""))
                        src = getattr(item, "source", None)
                        if src and str(src) not in sources:
                            sources.append(str(src))

            # Handle ChromaDB style dictionary response {documents: [...], metadatas: [...]}
            elif isinstance(results, dict):
                docs = results.get("documents") or []
                metas = results.get("metadatas") or []
                if docs and isinstance(docs[0], list):
                    # Flatten ChromaDB nested lists
                    docs = [doc for sub in docs for doc in sub]
                if metas and isinstance(metas[0], list):
                    metas = [meta for sub in metas for meta in sub]

                for idx, doc in enumerate(docs):
                    context_snippets.append(str(doc))
                    source_name = "brand_document"
                    if idx < len(metas) and isinstance(metas[idx], dict):
                        source_name = metas[idx].get("source") or metas[idx].get("filename") or source_name
                    if source_name not in sources:
                        sources.append(str(source_name))

            assembled_context = "\n\n---\n\n".join(context_snippets)
            return assembled_context, sources

        except Exception as exc:
            self.logger.warning("rag_retrieval_failed", error=str(exc))
            return "", []

    async def run(
        self,
        brand_name: str,
        campaign_brief: str = "",
        campaign_understanding: Optional[dict[str, Any]] = None,
        rag_pipeline: Optional[Any] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Execute brand research and return cohesive brand context.

        Args:
            brand_name: Target brand name.
            campaign_brief: User campaign objective or raw brief.
            campaign_understanding: Output from Campaign Understanding Agent.
            rag_pipeline: Optional RAG pipeline override.
            **kwargs: Extra arguments.

        Returns:
            dict[str, Any]: Structured brand context.
        """
        start_time = time.perf_counter()
        self.logger.info("starting_brand_research", brand=brand_name)

        # 1. Search vector store for brand documents
        search_query = f"{brand_name} brand guidelines style voice palette colors mission {campaign_brief}"
        rag_context, rag_sources = await self._query_rag(
            brand_name=brand_name,
            query=search_query,
            rag_service=rag_pipeline,
        )

        has_rag_docs = bool(rag_context.strip())
        self.logger.info("rag_search_completed", has_docs=has_rag_docs, sources=rag_sources)

        # 2. Synthesize using LLM
        understanding_summary = ""
        if campaign_understanding:
            ksps = campaign_understanding.get("key_selling_points", [])
            pos = campaign_understanding.get("competitive_positioning", "")
            appeal = campaign_understanding.get("emotional_appeal", "")
            understanding_summary = (
                f"Positioning: {pos}\n"
                f"Emotional Appeal: {appeal}\n"
                f"Key Selling Points: {', '.join(ksps[:4]) if isinstance(ksps, list) else ksps}"
            )

        if has_rag_docs:
            prompt = (
                f"Synthesize verified brand guidelines for '{brand_name}' using the following retrieved documents:\n\n"
                f"--- RETRIEVED BRAND DOCUMENTS ---\n"
                f"{rag_context[:4000]}\n\n"
                f"--- CAMPAIGN CONTEXT ---\n"
                f"Brief: {campaign_brief}\n"
                f"{understanding_summary}\n\n"
                f"Extract and structure the exact brand guidelines, brand voice, official hex colors, "
                f"and historical campaign references based on these documents."
            )
        else:
            prompt = (
                f"No indexed documents were found for brand '{brand_name}'. Conduct a strategic brand analysis "
                f"to establish definitive brand guidelines for our campaign production.\n\n"
                f"BRAND: {brand_name}\n"
                f"BRIEF: {campaign_brief}\n"
                f"{understanding_summary}\n\n"
                f"Formulate cohesive brand guidelines, defining a sophisticated brand voice, an optimal hex color palette "
                f"(3-5 hex colors matching the brand's industry and aura), precedent campaign angles, and core guardrails."
            )

        try:
            result = await self._call_llm_structured(
                prompt=prompt,
                response_model=BrandContextOutput,
            )
            result_dict = result.model_dump()
            # Ensure context sources reflect RAG or generative synthesis
            if has_rag_docs:
                result_dict["context_sources"] = rag_sources
                result_dict["relevant_context"] = rag_context[:2000]
            else:
                result_dict["context_sources"] = ["Generative Brand Knowledge Base (LLM Analysis)"]
                result_dict["relevant_context"] = (
                    f"Generated strategic brand guidelines for {brand_name} based on category conventions and campaign brief."
                )
        except Exception as exc:
            self.logger.error("brand_synthesis_llm_failed", error=str(exc))
            result_dict = self._generate_fallback_brand_context(
                brand_name=brand_name,
                brief=campaign_brief,
                rag_context=rag_context,
                rag_sources=rag_sources,
            )

        elapsed = time.perf_counter() - start_time
        result_dict["execution_time_seconds"] = round(elapsed, 3)

        self.logger.info(
            "brand_research_completed",
            brand=brand_name,
            color_count=len(result_dict.get("brand_colors", [])),
            duration_seconds=result_dict["execution_time_seconds"],
        )

        return result_dict

    def _generate_fallback_brand_context(
        self,
        brand_name: str,
        brief: str,
        rag_context: str,
        rag_sources: list[str],
    ) -> dict[str, Any]:
        """
        Generate robust fallback brand context when LLM generation is unavailable.

        Args:
            brand_name: Target brand.
            brief: Campaign brief.
            rag_context: Retrieved context if any.
            rag_sources: Retrieved sources if any.

        Returns:
            dict[str, Any]: Fallback brand context.
        """
        return {
            "brand_guidelines": (
                f"Brand Guidelines for {brand_name}:\n"
                "- Clean, modern, high-contrast visual design.\n"
                "- Emphasis on clarity, premium craftsmanship, and tangible user value.\n"
                "- Typography: Modern sans-serif headline paired with readable geometric body copy.\n"
                "- Maintain a unified visual layout with balanced negative space."
            ),
            "brand_voice": "Confident, innovative, aspirational, and customer-centric.",
            "brand_colors": ["#1E3A8A", "#3B82F6", "#06B6D4", "#F8FAFC", "#0F172A"],
            "previous_campaigns": f"Established precedents emphasizing modern problem-solving and quality for {brand_name}.",
            "relevant_context": rag_context if rag_context else f"Standard strategic brand baseline for {brand_name}.",
            "context_sources": rag_sources if rag_sources else ["Default Brand Baseline"],
        }
