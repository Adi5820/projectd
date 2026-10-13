"""
Base Agent Module for Agentic Ads Platform.

Defines the foundational BaseAgent class that all specialized advertising agents
inherit from. Provides standardized logging, lifecycle management, LLM interactions,
structured output validation, and execution timing.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any, Optional, Type, TypeVar

from pydantic import BaseModel
import structlog

T = TypeVar("T", bound=BaseModel)


class BaseAgent:
    """
    Base class for all AI agents in the Agentic Ads ecosystem.
    
    Provides core capabilities:
    - Structured logging via structlog with agent context
    - Flexible LLM interaction with fallback parsing
    - Pydantic v2 structured output enforcement
    - Execution timing and error isolation
    """

    def __init__(self, name: str, llm_provider: Optional[Any] = None) -> None:
        """
        Initialize the base agent.

        Args:
            name: Identifier for the agent (e.g., 'campaign_understanding_agent').
            llm_provider: Provider instance supporting LLM generation (e.g. GeminiProvider).
        """
        self.name = name
        self.llm = llm_provider
        self.logger = structlog.get_logger().bind(agent=name)

    async def run(self, **kwargs: Any) -> dict[str, Any]:
        """
        Execute the agent's main task. Must be overridden in subclasses.

        Args:
            **kwargs: Dynamic arguments required for agent execution.

        Returns:
            dict[str, Any]: Structured task results.

        Raises:
            NotImplementedError: If not implemented in subclass.
        """
        raise NotImplementedError("Subclasses must implement the 'run' method.")

    def _build_system_prompt(self) -> str:
        """
        Return the agent's system prompt. Must be overridden in subclasses.

        Returns:
            str: System prompt establishing role, tone, knowledge, and guidelines.

        Raises:
            NotImplementedError: If not implemented in subclass.
        """
        raise NotImplementedError("Subclasses must implement '_build_system_prompt'.")

    def _clean_json_response(self, text: str) -> str:
        """
        Strip markdown code fences and extraneous text from LLM JSON responses.

        Args:
            text: Raw string returned by LLM.

        Returns:
            str: Cleaned JSON string ready for parsing.
        """
        if not text:
            return "{}"

        text = text.strip()

        # Remove markdown code fences if present (```json ... ``` or ``` ...)
        json_fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if json_fence_match:
            return json_fence_match.group(1).strip()

        # If wrapped between brackets or braces
        start_brace = text.find("{")
        end_brace = text.rfind("}")
        if start_brace != -1 and end_brace != -1 and end_brace > start_brace:
            return text[start_brace : end_brace + 1].strip()

        start_bracket = text.find("[")
        end_bracket = text.rfind("]")
        if start_bracket != -1 and end_bracket != -1 and end_bracket > start_bracket:
            return text[start_bracket : end_bracket + 1].strip()

        return text

    async def _call_llm_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> T:
        """
        Invoke the LLM provider and parse the response into a validated Pydantic model.

        Supports providers that have native `generate_structured` methods, as well
        as providers with standard `generate` or `generate_content` methods.

        Args:
            prompt: User/task prompt for the model.
            response_model: Pydantic model class to validate output against.
            system_prompt: Optional custom system prompt, defaults to _build_system_prompt().
            **kwargs: Additional parameters forwarded to the LLM provider.

        Returns:
            T: An instance of response_model.

        Raises:
            RuntimeError: If LLM provider is not configured or parsing fails completely.
        """
        if self.llm is None:
            self.logger.error("llm_provider_missing", message="LLM provider is None")
            raise RuntimeError(f"Agent '{self.name}' has no LLM provider configured.")

        active_system_prompt = system_prompt or self._build_system_prompt()
        start_time = time.perf_counter()

        # 1. Try native generate_structured if available
        if hasattr(self.llm, "generate_structured") and callable(self.llm.generate_structured):
            try:
                result = await self.llm.generate_structured(
                    prompt=prompt,
                    response_model=response_model,
                    system_prompt=active_system_prompt,
                    **kwargs,
                )
                if isinstance(result, response_model):
                    return result
                if isinstance(result, dict):
                    return response_model.model_validate(result)
                if isinstance(result, str):
                    cleaned = self._clean_json_response(result)
                    return response_model.model_validate_json(cleaned)
            except Exception as exc:
                self.logger.warning(
                    "structured_llm_call_failed_fallback_to_raw",
                    error=str(exc),
                    model=response_model.__name__,
                )

        # 2. Schema-guided raw generation fallback
        schema_json = json.dumps(response_model.model_json_schema(), indent=2)
        enriched_prompt = (
            f"{prompt}\n\n"
            f"IMPORTANT: You MUST respond ONLY with a valid JSON object matching this schema:\n"
            f"{schema_json}\n"
            f"Do not include any explanation, conversational preamble, or commentary outside the JSON."
        )

        raw_response = await self._call_llm_text(
            prompt=enriched_prompt,
            system_prompt=active_system_prompt,
            **kwargs,
        )

        cleaned_json = self._clean_json_response(raw_response)
        try:
            return response_model.model_validate_json(cleaned_json)
        except Exception as parse_exc:
            self.logger.error(
                "pydantic_validation_failed",
                error=str(parse_exc),
                raw_response=raw_response[:500],
                model=response_model.__name__,
            )
            # Try parsing as dict and model_validate
            try:
                parsed_dict = json.loads(cleaned_json)
                return response_model.model_validate(parsed_dict)
            except Exception:
                raise RuntimeError(
                    f"Failed to parse LLM response into {response_model.__name__}: {parse_exc}"
                ) from parse_exc

    async def _call_llm_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """
        Execute raw text generation using the LLM provider.

        Args:
            prompt: Text prompt for generation.
            system_prompt: Optional system prompt.
            **kwargs: Extra parameters for LLM.

        Returns:
            str: Raw text output from LLM.
        """
        if self.llm is None:
            raise RuntimeError(f"Agent '{self.name}' has no LLM provider configured.")

        active_system_prompt = system_prompt or self._build_system_prompt()

        # Handle async vs sync providers
        if hasattr(self.llm, "generate") and callable(self.llm.generate):
            res = self.llm.generate(prompt=prompt, system_prompt=active_system_prompt, **kwargs)
            if hasattr(res, "__await__"):
                return await res
            return str(res)

        if hasattr(self.llm, "generate_text") and callable(self.llm.generate_text):
            res = self.llm.generate_text(prompt=prompt, system_prompt=active_system_prompt, **kwargs)
            if hasattr(res, "__await__"):
                return await res
            return str(res)

        if hasattr(self.llm, "generate_content") and callable(self.llm.generate_content):
            res = self.llm.generate_content(prompt=prompt, system_prompt=active_system_prompt, **kwargs)
            if hasattr(res, "__await__"):
                return await res
            return str(res)

        raise AttributeError(f"LLM provider {type(self.llm)} has no recognized generate method.")
