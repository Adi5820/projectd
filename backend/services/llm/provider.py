"""Abstract base class for LLM providers."""
from abc import ABC, abstractmethod
from typing import Optional, Type, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMProvider(ABC):
    """Abstract interface defining required LLM capabilities."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Generate text completion.
        
        Args:
            prompt: User prompt content.
            system_prompt: Optional system instruction prompt.
            temperature: Sampling temperature (0.0 to 1.0).
            max_tokens: Maximum response tokens to generate.

        Returns:
            The raw generated string response.
        """
        pass

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        response_schema: Type[T],
        system_prompt: Optional[str] = None,
    ) -> T:
        """Generate structured output matching a Pydantic schema.
        
        Args:
            prompt: User prompt content.
            response_schema: Pydantic model class defining desired structure.
            system_prompt: Optional system instruction prompt.

        Returns:
            An instantiated and validated Pydantic model instance.
        """
        pass
