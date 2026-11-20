from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe: the process is up. Used by Docker/Kubernetes."""
    return {"status": "ok"}


@router.get("/ready")
async def ready() -> dict[str, str]:
    """Readiness probe. Config is validated at startup, so reaching here means ready."""
    return {"status": "ready"}
