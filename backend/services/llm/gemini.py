"""Google Gemini LLM provider implementation."""
import asyncio
import json
import re
import time
from typing import Any, Optional, Type, TypeVar

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from pydantic import BaseModel, ValidationError
import structlog

from backend.config import settings
from backend.services.llm.provider import LLMProvider

logger = structlog.get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class GeminiLLMError(Exception):
    """Base exception for Gemini provider errors."""
    pass


class GeminiRateLimitError(GeminiLLMError):
    """Raised when Gemini API rate limit or quota is exhausted."""
    pass


class GeminiMalformedResponseError(GeminiLLMError):
    """Raised when Gemini returns unparseable or schema-incompatible JSON."""
    pass


class GeminiProvider(LLMProvider):
    """Google Gemini LLM Provider using the google-generativeai SDK."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        """Initialize the Gemini client.
        
        Args:
            api_key: Gemini API key. Defaults to settings.GEMINI_API_KEY.
            model_name: Model identifier. Defaults to settings.GEMINI_MODEL.
        """
        self.api_key = api_key or getattr(settings, "effective_gemini_key", getattr(settings, "GEMINI_API_KEY", getattr(settings, "GOOGLE_API_KEY", "")))
        self.model_name = model_name or getattr(settings, "GEMINI_MODEL", "gemini-2.0-flash")
        
        if self.api_key and not self.api_key.startswith("dev_"):
            try:
                genai.configure(api_key=self.api_key)
            except Exception as e:
                logger.warning("gemini_configure_failed", error=str(e))
        else:
            logger.warning("gemini_api_key_missing_or_placeholder", message="Real GEMINI_API_KEY is not configured; fallback heuristics will be active.")

    def _get_model(
        self,
        system_instruction: Optional[str] = None,
        generation_config: Optional[genai.GenerationConfig] = None,
    ) -> genai.GenerativeModel:
        """Create a GenerativeModel instance."""
        return genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system_instruction,
            generation_config=generation_config,
        )

    def _sync_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Synchronous wrapper for text generation."""
        generation_config = genai.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        model = self._get_model(
            system_instruction=system_prompt,
            generation_config=generation_config,
        )
        response = model.generate_content(prompt)
        if not response or not response.text:
            raise GeminiMalformedResponseError("Gemini returned an empty response.")
        return response.text

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> str:
        """Generate text completion with retry and backoff."""
        if not self.api_key or self.api_key.startswith("dev_"):
            raise GeminiLLMError("Gemini API key is not configured or is a development placeholder.")

        max_retries = 3
        backoff_delay = 1.0

        for attempt in range(1, max_retries + 1):
            start_time = time.perf_counter()
            try:
                result = await asyncio.to_thread(
                    self._sync_generate,
                    prompt,
                    system_prompt,
                    temperature,
                    max_tokens,
                )
                latency = time.perf_counter() - start_time
                logger.info(
                    "gemini_generate_success",
                    model=self.model_name,
                    prompt_length=len(prompt),
                    response_length=len(result),
                    latency=round(latency, 4),
                    attempt=attempt,
                )
                return result

            except (google_exceptions.ResourceExhausted, google_exceptions.TooManyRequests) as e:
                latency = time.perf_counter() - start_time
                logger.warning(
                    "gemini_rate_limited",
                    attempt=attempt,
                    latency=round(latency, 4),
                    error=str(e),
                )
                if attempt == max_retries:
                    raise GeminiRateLimitError(f"Gemini quota/rate limit exceeded: {e}") from e
                await asyncio.sleep(backoff_delay)
                backoff_delay *= 2.0

            except Exception as e:
                latency = time.perf_counter() - start_time
                logger.error(
                    "gemini_generate_failed",
                    attempt=attempt,
                    latency=round(latency, 4),
                    error=str(e),
                )
                if attempt == max_retries:
                    raise GeminiLLMError(f"Gemini generate failed after {max_retries} attempts: {e}") from e
                await asyncio.sleep(backoff_delay)
                backoff_delay *= 2.0

        raise GeminiLLMError("Unexpected termination of generate loop.")

    def _sync_generate_structured(
        self,
        prompt: str,
        response_schema: Type[T],
        system_prompt: Optional[str] = None,
    ) -> T:
        """Synchronous structured output generation."""
        try:
            generation_config = genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=response_schema,
                temperature=0.2,
            )
            model = self._get_model(
                system_instruction=system_prompt,
                generation_config=generation_config,
            )
            response = model.generate_content(prompt)
        except Exception:
            # Fallback if SDK or model rejects response_schema argument
            generation_config = genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.2,
            )
            schema_json = json.dumps(response_schema.model_json_schema())
            augmented_prompt = (
                f"{prompt}\n\nYou MUST respond with valid JSON matching this schema:\n{schema_json}"
            )
            model = self._get_model(
                system_instruction=system_prompt,
                generation_config=generation_config,
            )
            response = model.generate_content(augmented_prompt)

        raw_text = (response.text or "").strip()
        if not raw_text:
            raise GeminiMalformedResponseError("Empty structured response received from Gemini.")

        # Clean markdown codeblocks if returned
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE).strip()

        try:
            return response_schema.model_validate_json(cleaned)
        except (ValidationError, json.JSONDecodeError) as err:
            raise GeminiMalformedResponseError(
                f"Failed to validate JSON against schema {response_schema.__name__}: {err}. Response text: {raw_text[:200]}"
            ) from err

    async def generate_structured(
        self,
        prompt: str,
        response_schema: Optional[Type[T]] = None,
        system_prompt: Optional[str] = None,
        response_model: Optional[Type[T]] = None,
        **kwargs: Any,
    ) -> T:
        """Generate structured output matching a Pydantic schema with retries."""
        target_schema = response_schema or response_model
        if target_schema is None:
            raise ValueError("Either response_schema or response_model must be specified.")

        if not self.api_key or self.api_key.startswith("dev_"):
            raise GeminiLLMError("Gemini API key is not configured or is a development placeholder.")

        max_retries = 3
        backoff_delay = 1.0

        for attempt in range(1, max_retries + 1):
            start_time = time.perf_counter()
            try:
                result = await asyncio.to_thread(
                    self._sync_generate_structured,
                    prompt,
                    target_schema,
                    system_prompt,
                )
                latency = time.perf_counter() - start_time
                logger.info(
                    "gemini_structured_success",
                    model=self.model_name,
                    prompt_length=len(prompt),
                    schema=target_schema.__name__,
                    latency=round(latency, 4),
                    attempt=attempt,
                )
                return result

            except (google_exceptions.ResourceExhausted, google_exceptions.TooManyRequests) as e:
                latency = time.perf_counter() - start_time
                logger.warning(
                    "gemini_structured_rate_limited",
                    attempt=attempt,
                    latency=round(latency, 4),
                    error=str(e),
                )
                if attempt == max_retries:
                    raise GeminiRateLimitError(f"Gemini quota/rate limit exceeded: {e}") from e
                await asyncio.sleep(backoff_delay)
                backoff_delay *= 2.0

            except GeminiMalformedResponseError as e:
                latency = time.perf_counter() - start_time
                logger.warning(
                    "gemini_structured_malformed",
                    attempt=attempt,
                    latency=round(latency, 4),
                    error=str(e),
                )
                if attempt == max_retries:
                    raise
                await asyncio.sleep(backoff_delay)
                backoff_delay *= 1.5

            except Exception as e:
                latency = time.perf_counter() - start_time
                logger.error(
                    "gemini_structured_failed",
                    attempt=attempt,
                    latency=round(latency, 4),
                    error=str(e),
                )
                if attempt == max_retries:
                    raise GeminiLLMError(f"Structured generation failed after {max_retries} attempts: {e}") from e
                await asyncio.sleep(backoff_delay)
                backoff_delay *= 2.0

        raise GeminiLLMError("Unexpected termination of generate_structured loop.")
