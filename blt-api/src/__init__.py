"""
BLT API - Full-featured API for OWASP BLT running on Cloudflare Workers

This module provides a complete REST API that interfaces with all aspects
of the OWASP BLT (Bug Logging Tool) project.
"""

from .router import Router
from .handlers import (
    handle_issues,
    handle_users,
    handle_domains,
    handle_organizations,
    handle_projects,
    handle_hunts,
    handle_stats,
    handle_leaderboard,
    handle_contributors,
    handle_repos,
    handle_health,
)

__all__ = [
    "Router",
    "handle_issues",
    "handle_users",
    "handle_domains",
    "handle_organizations",
    "handle_projects",
    "handle_hunts",
    "handle_stats",
    "handle_leaderboard",
    "handle_contributors",
    "handle_repos",
    "handle_health",
]

__version__ = "1.0.0"
