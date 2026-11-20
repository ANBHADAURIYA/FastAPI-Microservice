from types import SimpleNamespace
from typing import Any

import anthropic
import httpx
import pytest

from app.core.config import get_settings
from app.core.errors import LLMError
from app.services.llm_service import AnthropicSummarizer


def _summarizer(create: Any) -> AnthropicSummarizer:
    s = AnthropicSummarizer(get_settings())
    s._client = SimpleNamespace(messages=SimpleNamespace(create=create))  # type: ignore[assignment]
    return s


async def test_summarize_joins_text_blocks_and_wraps_input() -> None:
    seen: dict[str, Any] = {}

    async def create(**kwargs: Any) -> Any:
        seen.update(kwargs)
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=" Short. ")])

    assert await _summarizer(create).summarize("long text") == "Short."
    assert seen["messages"][0]["content"] == "<text>\nlong text\n</text>"
    assert seen["max_tokens"] == 300


async def test_api_error_becomes_llm_error() -> None:
    async def create(**kwargs: Any) -> Any:
        request = httpx.Request("POST", "https://x")
        raise anthropic.APIConnectionError(request=request)  # type: ignore[arg-type]

    with pytest.raises(LLMError):
        await _summarizer(create).summarize("text")


async def test_empty_completion_becomes_llm_error() -> None:
    async def create(**kwargs: Any) -> Any:
        return SimpleNamespace(content=[])

    with pytest.raises(LLMError):
        await _summarizer(create).summarize("text")
