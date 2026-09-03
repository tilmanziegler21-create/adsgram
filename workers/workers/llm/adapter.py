"""Universal OpenAI-compatible LLM adapter (DeepSeek default, OpenAI switchable)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from openai import OpenAI

from workers.core.config import settings

ProviderName = Literal["deepseek", "openai"]


@dataclass(frozen=True)
class LLMConfig:
    provider: ProviderName
    api_key: str
    base_url: str
    model: str


class LLMAdapterError(Exception):
    pass


def resolve_llm_config(provider: str | None = None) -> LLMConfig:
    name = (provider or settings.LLM_PROVIDER or "deepseek").strip().lower()
    if name == "deepseek":
        return LLMConfig(
            provider="deepseek",
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL.rstrip("/"),
            model=settings.DEEPSEEK_MODEL,
        )
    if name == "openai":
        return LLMConfig(
            provider="openai",
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL.rstrip("/"),
            model=settings.OPENAI_MODEL,
        )
    raise LLMAdapterError(f"Unsupported LLM_PROVIDER: {name!r}. Use 'deepseek' or 'openai'.")


class LLMAdapter:
    """Chat completions via OpenAI SDK; provider switched by config only."""

    def __init__(self, provider: str | None = None):
        self.config = resolve_llm_config(provider)
        if not self.config.api_key:
            raise LLMAdapterError(
                f"API key is empty for provider '{self.config.provider}'. "
                "Set DEEPSEEK_API_KEY or OPENAI_API_KEY in .env."
            )
        self._client = OpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
        )

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        response = self._client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        return (content or "").strip()


def get_llm_adapter(provider: str | None = None) -> LLMAdapter:
    return LLMAdapter(provider=provider)
