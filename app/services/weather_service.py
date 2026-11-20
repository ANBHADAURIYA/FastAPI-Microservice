import httpx

from app.core.config import Settings
from app.core.errors import CityNotFoundError, UpstreamError
from app.schemas.weather import WeatherResponse
from app.services.http import get_json


async def get_weather(client: httpx.AsyncClient, settings: Settings, city: str) -> WeatherResponse:
    response = await get_json(
        client,
        settings.openweather_base_url,
        params={"q": city, "units": "metric", "appid": settings.openweather_api_key},
        ok_statuses=(200, 404),  # 404 is a *meaningful* answer: unknown city
    )
    if response.status_code == 404:
        raise CityNotFoundError(f"City '{city}' not found")

    try:
        data = response.json()
        return WeatherResponse(
            city=data["name"],
            temperature=data["main"]["temp"],
            condition=data["weather"][0]["main"],
            humidity=data["main"]["humidity"],
        )
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        # Upstream answered 200 but not in the shape we expect.
        raise UpstreamError("Weather service returned an unexpected response") from exc
