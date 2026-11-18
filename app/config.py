"""Environment-driven configuration.

Secrets (database credentials, JWT signing key) are required from the environment;
only non-sensitive defaults live in source. See .env.example.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    database_url: str
    jwt_secret: str
    access_token_expire_minutes: int = 60


settings = Settings()  # type: ignore[call-arg]
