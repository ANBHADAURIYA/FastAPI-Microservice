"""Rate limiting for the costly /summary endpoint (each call spends LLM money).

Limits are per API key (falling back to client IP). Storage is in-process
memory, so with N workers the effective limit is N x the configured value; use
a Redis storage URI in `Limiter(storage_uri=...)` for a shared limit.
"""

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def _key_func(request: Request) -> str:
    return request.headers.get("X-API-Key") or get_remote_address(request)


limiter = Limiter(key_func=_key_func)
