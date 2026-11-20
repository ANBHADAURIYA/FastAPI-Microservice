"""Application settings.

pydantic-settings reads values from environment variables (and a local `.env`
file during development) and validates them when the app starts. If a required
value is missing the app refuses to boot, which is far better than failing on
the first user request.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Comma-separated list of keys accepted by POST /summary.
    api_keys: str = Field(min_length=1)

    openweather_api_key: str = Field(min_length=1)
    openweather_base_url: str = "https://api.openweathermap.org/data/2.5/weather"
    joke_api_url: str = "https://official-joke-api.appspot.com/random_joke"

    anthropic_api_key: str = Field(min_length=1)
    llm_model: str = "claude-haiku-5-5"
    llm_max_output_tokens: int = 300

    max_text_length: int = 10_000
    upstream_timeout_seconds: float = 5.0
    summary_rate_limit: str = "10/minute"
    log_level: str = "INFO"

    @property
    def valid_api_keys(self) -> list[str]:
        return [k.strip() for k in self.api_keys.split(",") if k.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached so the environment is parsed once per process."""
    return Settings()
