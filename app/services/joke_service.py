import httpx

from app.core.config import Settings
from app.core.errors import UpstreamError
from app.schemas.joke import JokeResponse
from app.services.http import get_json


async def get_random_joke(client: httpx.AsyncClient, settings: Settings) -> JokeResponse:
    response = await get_json(client, settings.joke_api_url)
    try:
        data = response.json()
        return JokeResponse(joke=f"{data['setup']} {data['punchline']}", category=data["type"])
    except (ValueError, KeyError, TypeError) as exc:
        raise UpstreamError("Joke service returned an unexpected response") from exc
