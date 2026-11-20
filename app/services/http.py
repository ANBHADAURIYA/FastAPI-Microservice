"""Small helper for calling upstream JSON APIs safely."""

import logging
from typing import Any

import httpx

from app.core.errors import UpstreamError

logger = logging.getLogger(__name__)


async def get_json(
    client: httpx.AsyncClient,
    url: str,
    params: dict[str, Any] | None = None,
    *,
    ok_statuses: tuple[int, ...] = (200,),
    retries: int = 1,
) -> httpx.Response:
    """GET `url`, retrying once on network errors / 5xx (GETs are idempotent).

    Returns the response when its status is in `ok_statuses` (the caller can
    include e.g. 404 and interpret it). Anything else becomes UpstreamError (502).
    """
    last: str = ""
    for attempt in range(retries + 1):
        try:
            response = await client.get(url, params=params)
        except httpx.HTTPError as exc:  # timeouts, DNS, connection resets...
            last = f"{type(exc).__name__}"
            logger.warning("Upstream request failed (attempt %d): %s", attempt + 1, last)
            continue
        if response.status_code in ok_statuses:
            return response
        last = f"status {response.status_code}"
        logger.warning("Upstream returned %s (attempt %d)", last, attempt + 1)
        if response.status_code < 500:
            break  # 4xx will not fix itself by retrying
    raise UpstreamError(f"Upstream service failed ({last})")
