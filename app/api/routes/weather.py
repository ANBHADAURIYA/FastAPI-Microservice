from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import HttpClient
from app.core.config import Settings, get_settings
from app.schemas.error import ErrorResponse
from app.schemas.weather import WeatherResponse
from app.services.weather_service import get_weather

router = APIRouter(tags=["weather"])


@router.get(
    "/weather",
    response_model=WeatherResponse,
    responses={
        404: {"model": ErrorResponse, "description": "City not found"},
        502: {"model": ErrorResponse, "description": "Weather API failed"},
    },
)
async def weather(
    # Query(...) makes `city` required; min/max length are validated for us.
    city: Annotated[str, Query(min_length=1, max_length=100, description="City name")],
    client: HttpClient,
    settings: Annotated[Settings, Depends(get_settings)],
) -> WeatherResponse:
    """Return current weather for a city."""
    return await get_weather(client, settings, city.strip())
