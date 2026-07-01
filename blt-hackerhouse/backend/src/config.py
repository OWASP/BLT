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

    # --- GitLab ---
    gitlab_webhook_secret: str = ""
    gitlab_api_token: str = ""

    # --- BLT API ---
    blt_api_base_url: str = "https://api.owaspblt.org/v2"
    blt_api_key: str = ""

    # --- Database ---
    database_path: Path = Path("blt_hackerhouse.db")

    # --- Polling ---
    poll_interval_seconds: int = 60

    # --- Logging ---
    log_level: str = "INFO"


settings = Settings()
