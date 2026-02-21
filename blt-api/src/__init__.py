"""
BLT API - Full-featured API for OWASP BLT running on Cloudflare Workers

This module provides a complete REST API that interfaces with all aspects
of the OWASP BLT (Bug Logging Tool) project.
"""

from .router import Router
from .handlers import (
    handle_bugs,
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
    handle_signup,
    handle_signin,
    handle_verify_email
)

__all__ = [
    "Router",
    "handle_bugs",
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
    "handle_signup",
    "handle_signin",
    "handle_verify_email"
]

__version__ = "1.0.0"
