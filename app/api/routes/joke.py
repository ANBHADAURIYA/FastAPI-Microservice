from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import HttpClient
from app.core.config import Settings, get_settings
from app.schemas.error import ErrorResponse
from app.schemas.joke import JokeResponse
from app.services.joke_service import get_random_joke

router = APIRouter(tags=["joke"])


@router.get(
    "/joke",
    response_model=JokeResponse,
    responses={502: {"model": ErrorResponse, "description": "Joke API failed"}},
)
async def joke(
    client: HttpClient, settings: Annotated[Settings, Depends(get_settings)]
) -> JokeResponse:
    """Return a random joke and its category."""
    return await get_random_joke(client, settings)
