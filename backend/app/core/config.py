"""
AI Call Analytics — Core Configuration & Environment Validation.

Centralized settings loaded from environment variables with strong validation,
environment separation (dev/test/prod), and security controls.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- Application & Environment ----
    app_name: str = "ai-call-analytics"
    app_env: Literal["development", "test", "production"] = "development"
    debug: bool = True
    log_level: str = "INFO"

    # ---- Networking & Ports ----
    backend_port: int = 8000
    frontend_port: int = 5173

    # ---- Database ----
    database_url: str = Field(
        default="postgresql://postgres:changeme@localhost:5432/ai_call_analytics",
        description="SQLAlchemy database connection URL",
    )
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30

    # ---- Redis ----
    redis_url: str = "redis://localhost:6379/0"

    # ---- Celery ----
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    celery_task_timeout: int = 3600  # 1 hour max per task
    celery_worker_concurrency: int = 2

    # ---- Security & JWT ----
    jwt_secret: str = "change-this-to-a-random-secret-key"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60

    # ---- CORS ----
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # ---- Upload & Audio Constraints ----
    max_upload_size: int = 52428800  # 50 MB
    max_audio_duration: float = 3600.0  # 1 hour in seconds
    allowed_audio_extensions: list[str] = [".wav", ".mp3", ".flac", ".ogg", ".m4a"]
    allowed_mime_types: list[str] = [
        "audio/wav",
        "audio/x-wav",
        "audio/mpeg",
        "audio/mp3",
        "audio/flac",
        "audio/ogg",
        "audio/x-m4a",
        "audio/mp4",
        "application/octet-stream",
    ]

    # ---- Storage Configuration ----
    storage_type: Literal["local", "s3"] = "local"
    storage_local_dir: str = "data/uploads"
    storage_endpoint: str = "http://localhost:9000"
    storage_access_key: str = ""
    storage_secret_key: str = ""
    storage_bucket: str = "call-recordings"
    storage_region: str = "us-east-1"

    # ---- AI / Model Configuration ----
    ai_model_paths: str = "./models"
    whisper_model: str = "base"
    whisper_model_size: str = "base"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    device: str = "cpu"

    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_device: str = "cpu"
    embedding_dimension: int = 384

    hf_home: str = "./models/huggingface"
    hf_token: str = ""
    huggingface_token: str = ""

    audio_output_dir: str = "data/processed"
    audio_sample_rate: int = 16000
    audio_channels: int = 1

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse CORS origins string into a list."""
        if not self.cors_origins:
            return []
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def sync_database_url(self) -> str:
        """Return synchronous psycopg2 / standard postgresql database URL."""
        return self.database_url.replace("postgresql+asyncpg://", "postgresql://")

    @property
    def resolved_redis_url(self) -> str:
        """
        Return resolved Redis URL, replacing docker service host 'redis' with 'localhost'
        if resolving outside a Docker network.
        """
        url = self.redis_url
        if "redis://redis:" in url or "@redis:" in url:
            try:
                import socket
                socket.gethostbyname("redis")
            except socket.gaierror:
                url = url.replace("redis://redis:", "redis://localhost:").replace("@redis:", "@localhost:")
        return url

    @property
    def resolved_celery_broker_url(self) -> str:
        """Return resolved Celery broker URL with localhost fallback."""
        url = self.celery_broker_url
        if "redis://redis:" in url:
            try:
                import socket
                socket.gethostbyname("redis")
            except socket.gaierror:
                url = url.replace("redis://redis:", "redis://localhost:")
        return url

    @property
    def resolved_celery_result_backend(self) -> str:
        """Return resolved Celery result backend URL with localhost fallback."""
        url = self.celery_result_backend
        if "redis://redis:" in url:
            try:
                import socket
                socket.gethostbyname("redis")
            except socket.gaierror:
                url = url.replace("redis://redis:", "redis://localhost:")
        return url


def validate_environment(cfg: Settings) -> None:
    """
    Validate critical environment configuration on startup.

    Raises:
        ValueError: If a required configuration item is missing or invalid in production.
    """
    if not cfg.database_url:
        raise ValueError("DATABASE_URL must be specified.")

    if cfg.app_env == "production":
        if "changeme" in cfg.database_url or "postgres:postgres" in cfg.database_url:
            raise ValueError("Production environment cannot use default database credentials.")
        if cfg.jwt_secret == "change-this-to-a-random-secret-key" or len(cfg.jwt_secret) < 32:
            raise ValueError("Production environment requires a secure, high-entropy JWT_SECRET (>= 32 chars).")
        if "*" in cfg.cors_origins:
            raise ValueError("Production environment cannot allow wildcard CORS origins ('*').")


# Singleton instance
settings = Settings()
