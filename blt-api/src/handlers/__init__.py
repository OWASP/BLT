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
from .jobs import handle_jobs
from .hackathons import handle_hackathons
from .health import handle_health
from .homepage import handle_blt_api_logo, handle_dashboard, handle_homepage
from .auth_page import handle_auth_page
from .auth import handle_api_keys, handle_signup, handle_signin, handle_verify_email, handle_verify_local
from .routes import make_routes_handler

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
    "handle_jobs",
    "handle_hackathons",
    "handle_health",
    "handle_blt_api_logo",
    "handle_dashboard",
    "handle_homepage",
    "handle_auth_page",
    "handle_signup",
    "handle_signin",
    "handle_verify_email",
    "handle_verify_local",
    "handle_api_keys",
    "make_routes_handler",
]
