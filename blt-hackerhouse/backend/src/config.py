"""
Application configuration loaded from environment variables.

Uses pydantic-settings for validation, type coercion, and defaults.
In Workers, Wrangler injects vars/secrets into process environment.
"""

import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration for the BLT-Hackerhouse backend."""

    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env" if os.environ.get("CI") else None,
    )

    # --- GitLab ---
    gitlab_webhook_secret: str = ""
    gitlab_api_token: str = ""
    gitlab_tracked_project_ids: str = ""
    gitlab_poll_interval_seconds: int = 90
    gitlab_lookback_minutes: int = 30

    # --- WebSocket ---
    websocket_auth_token: str = ""

    # --- BLT API ---
    blt_api_base_url: str = "https://api.owaspblt.org/v2"
    blt_api_key: str = ""
    blt_poll_interval_seconds: int = 60

    # --- Logging ---
    log_level: str = "INFO"


settings = Settings()