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

    # --- Forge (git.owaspblt.org): the main source ---
    forge_url: str = "https://git.owaspblt.org"
    forge_repo: str = "owasp-blt/BLT"
    forge_ref: str = "main"
    forge_bot_authors: str = "owasp-blt-actions,forkmesh"
    forge_backfill_days: int = 7
    forge_max_events: int = 300

    # --- GitLab webhook: optional external source ---
    gitlab_webhook_secret: str = ""

    # --- WebSocket ---
    websocket_auth_token: str = ""

    # --- BLT API ---
    blt_api_base_url: str = "https://api.owaspblt.org/v2"
    blt_api_key: str = ""

    # --- Logging ---
    log_level: str = "INFO"


settings = Settings()