from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from slowapi.middleware import SlowAPIMiddleware

from app.api.routes import health, joke, summary, weather
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import RequestIdMiddleware, configure_logging
from app.core.ratelimit import limiter
from app.services.llm_service import AnthropicSummarizer


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup/shutdown. Resources created here are shared by all requests.

    One pooled AsyncClient reuses TCP/TLS connections, which is much faster
    than opening a new connection for every request.
    """
    settings = get_settings()  # fails fast here if env vars are missing
    configure_logging(settings.log_level)
    app.state.http_client = httpx.AsyncClient(timeout=settings.upstream_timeout_seconds)
    app.state.summarizer = AnthropicSummarizer(settings)
    yield
    await app.state.http_client.aclose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="FastAPI Microservice",
        description="Weather and joke wrappers plus an authenticated LLM summary endpoint.",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(RequestIdMiddleware)  # added last = outermost
    register_exception_handlers(app)
    for module in (health, weather, joke, summary):
        app.include_router(module.router)
    return app


app = create_app()
