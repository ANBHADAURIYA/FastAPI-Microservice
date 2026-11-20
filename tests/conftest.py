import os
from collections.abc import Iterator

# Must be set before the app (and its cached Settings) is imported.
os.environ.update(
    API_KEYS="test-key-1,test-key-2",
    OPENWEATHER_API_KEY="owm-test",
    ANTHROPIC_API_KEY="anthropic-test",
    MAX_TEXT_LENGTH="100",
    SUMMARY_RATE_LIMIT="1000/minute",
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.api.deps import get_summarizer  # noqa: E402
from app.core.errors import LLMError  # noqa: E402
from app.main import app  # noqa: E402


class FakeSummarizer:
    def __init__(self) -> None:
        self.fail = False
        self.calls: list[str] = []

    async def summarize(self, text: str) -> str:
        self.calls.append(text)
        if self.fail:
            raise LLMError()
        return "A short summary."


@pytest.fixture
def fake_llm() -> FakeSummarizer:
    return FakeSummarizer()


@pytest.fixture
def client(fake_llm: FakeSummarizer) -> Iterator[TestClient]:
    app.dependency_overrides[get_summarizer] = lambda: fake_llm
    with TestClient(app) as c:  # context manager runs lifespan (creates http client)
        yield c
    app.dependency_overrides.clear()


AUTH = {"X-API-Key": "test-key-1"}
