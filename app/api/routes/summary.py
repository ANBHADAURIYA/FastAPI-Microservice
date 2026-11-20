from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.deps import SummarizerDep
from app.core.config import Settings, get_settings
from app.core.errors import InvalidTextError
from app.core.ratelimit import limiter
from app.core.security import require_api_key
from app.schemas.error import ErrorResponse
from app.schemas.summary import SummaryRequest, SummaryResponse

router = APIRouter(tags=["summary"])


@router.post(
    "/summary",
    response_model=SummaryResponse,
    # Auth is a dependency: it runs before the handler body, so an
    # unauthenticated caller never reaches the LLM (and never costs money).
    dependencies=[Depends(require_api_key)],
    responses={
        400: {"model": ErrorResponse, "description": "Text empty or too long"},
        401: {"model": ErrorResponse, "description": "Missing or invalid API key"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        502: {"model": ErrorResponse, "description": "LLM provider failed"},
    },
)
# slowapi needs the `request` argument and reads the limit lazily from settings.
@limiter.limit(lambda: get_settings().summary_rate_limit)
async def summary(
    request: Request,
    body: SummaryRequest,
    summarizer: SummarizerDep,
    settings: Annotated[Settings, Depends(get_settings)],
) -> SummaryResponse:
    """Summarise text into 2-3 sentences using an LLM. Requires `X-API-Key`."""
    text = body.text.strip()
    if not text:
        raise InvalidTextError("text must not be empty")
    if len(text) > settings.max_text_length:
        raise InvalidTextError(
            f"text exceeds maximum length of {settings.max_text_length} characters"
        )
    return SummaryResponse(summary=await summarizer.summarize(text))
