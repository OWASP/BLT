"""
Request handlers for the BLT API.

This module contains all the handler functions that process
incoming API requests and return appropriate responses.
"""

from .bugs import handle_bugs
from .users import handle_users
from .domains import handle_domains
from .organizations import handle_organizations
from .projects import handle_projects
from .hunts import handle_hunts
from .stats import handle_stats
from .leaderboard import handle_leaderboard
from .contributors import handle_contributors
from .repos import handle_repos
from .health import handle_health
from .homepage import handle_homepage
from .auth import handle_signup, handle_signin, handle_verify_email

__all__ = [
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
    "handle_homepage",
    "handle_signup",
    "handle_signin",
    "handle_verify_email",
]
