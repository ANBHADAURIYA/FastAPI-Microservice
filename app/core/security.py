"""API-key authentication for protected endpoints."""

import hmac
from typing import Annotated

from fastapi import Depends
from fastapi.security import APIKeyHeader

from app.core.config import Settings, get_settings
from app.core.errors import UnauthorizedError

# auto_error=False lets us raise our own 401 (FastAPI would otherwise return 403).
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(
    api_key: Annotated[str | None, Depends(api_key_header)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> str:
    if not api_key:
        raise UnauthorizedError()
    # compare_digest takes constant time, so response timing can't be used to
    # guess a key one character at a time. Check every key (no early exit).
    matches = [hmac.compare_digest(api_key.encode(), k.encode()) for k in settings.valid_api_keys]
    if not any(matches):
        raise UnauthorizedError()
    return api_key
