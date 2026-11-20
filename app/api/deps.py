"""Dependencies injected into routes with `Depends(...)`.

Routes never build their own HTTP client or LLM client; they ask for one. That
keeps routes thin and lets tests substitute fakes via `app.dependency_overrides`.
"""

from typing import Annotated

import httpx
from fastapi import Depends, Request

from app.services.llm_service import Summarizer


def get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http_client  # type: ignore[no-any-return]


def get_summarizer(request: Request) -> Summarizer:
    return request.app.state.summarizer  # type: ignore[no-any-return]


HttpClient = Annotated[httpx.AsyncClient, Depends(get_http_client)]
SummarizerDep = Annotated[Summarizer, Depends(get_summarizer)]
