"""
Application configuration loaded from environment variables.

Uses pydantic-settings for validation, type coercion, and defaults.
Import ``settings`` from this module to access all configuration values.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration for the BLT-Hackerhouse backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- GitLab Webhook ---
    gitlab_webhook_secret: str = ""

    # --- GitLab Gap Detector ---
    gitlab_api_token: str = ""
    gitlab_tracked_project_ids: str = ""
    gitlab_poll_interval_seconds: int = 90
    gitlab_lookback_minutes: int = 30
    gitlab_per_page: int = 100
    gitlab_max_retries: int = 5
    gitlab_retry_base_delay: float = 1.0
    gitlab_retry_max_delay: float = 32.0

    # --- WebSocket ---
    websocket_auth_token: str = ""

    # --- BLT API ---
    blt_api_base_url: str = "https://api.owaspblt.org/v2"
    blt_api_key: str = ""
    blt_poll_interval_seconds: int = 60
    blt_per_page: int = 100
    blt_max_retries: int = 5
    blt_retry_base_delay: float = 1.0
    blt_retry_max_delay: float = 32.0

    # --- Database ---
    database_path: Path = Path("blt_hackerhouse.db")

    # --- Pipeline ---
    pipeline_poll_interval_ms: int = 50

    # --- Logging ---
    log_level: str = "INFO"


settings = Settings()
