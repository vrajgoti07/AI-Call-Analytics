"""
AI Call Analytics — Core Configuration.

Loads all settings from environment variables with sensible defaults.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- Application ----
    app_name: str = "ai-call-analytics"
    app_env: str = "development"
    debug: bool = True

    # ---- Database ----
    database_url: str = "postgresql+asyncpg://postgres:changeme@localhost:5432/ai_call_analytics"

    # ---- Redis ----
    redis_url: str = "redis://localhost:6379/0"

    # ---- JWT ----
    jwt_secret: str = "change-this-to-a-random-secret-key"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60

    # ---- S3-Compatible Storage ----
    storage_endpoint: str = "http://localhost:9000"
    storage_access_key: str = ""
    storage_secret_key: str = ""
    storage_bucket: str = "call-recordings"
    storage_region: str = "us-east-1"

    # ---- AI / Models ----
    whisper_model_size: str = "base"
    device: str = "cpu"
    hf_home: str = "./models/huggingface"
    huggingface_token: str = ""  # Placeholder: supply real token after accepting terms (e.g. pyannote)

    # ---- Celery ----
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # ---- CORS ----
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse CORS origins string into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


# Singleton instance
settings = Settings()
