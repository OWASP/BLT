import logging
from blt_mcp.server_base import mcp, _fetch

logger = logging.getLogger("blt-mcp.v2_resources")


@mcp.resource("blt://v2/auth/verify-email/{token}")
async def v2_verify_email(token: str) -> str:
    """Verify email with a token."""
    logger.info("Verifying email token")
    return await _fetch(
        f"/v2/auth/verify-email?token={token}", context="v2 verify email"
    )


@mcp.resource("blt://v2/bugs")
async def v2_list_bugs() -> str:
    """List bugs."""
    logger.info("Fetching v2 bugs list")
    return await _fetch("/v2/bugs", context="v2 bugs")


@mcp.resource("blt://v2/bugs/{id}")
async def v2_get_bug(id: str) -> str:
    """Get bug by ID."""
    logger.info(f"Fetching v2 bug: {id}")
    return await _fetch(f"/v2/bugs/{id}", context=f"v2 bug {id}")


@mcp.resource("blt://v2/bugs/search/{query}")
async def v2_search_bugs(query: str) -> str:
    """Search bugs by query."""
    logger.info(f"Searching v2 bugs with query: {query}")
    return await _fetch(f"/v2/bugs/search?q={query}", context=f"v2 bug search {query}")


@mcp.resource("blt://v2/users")
async def v2_list_users() -> str:
    """List users."""
    logger.info("Fetching v2 users list")
    return await _fetch("/v2/users", context="v2 users")


@mcp.resource("blt://v2/users/{id}")
async def v2_get_user(id: str) -> str:
    """Get user by ID."""
    logger.info(f"Fetching v2 user: {id}")
    return await _fetch(f"/v2/users/{id}", context=f"v2 user {id}")


@mcp.resource("blt://v2/users/{id}/profile")
async def v2_get_user_profile(id: str) -> str:
    """Get user profile by ID."""
    logger.info(f"Fetching v2 user profile: {id}")
    return await _fetch(f"/v2/users/{id}/profile", context=f"v2 user profile {id}")


@mcp.resource("blt://v2/users/{id}/bugs")
async def v2_get_user_bugs(id: str) -> str:
    """Get user's bugs by user ID."""
    logger.info(f"Fetching v2 user bugs: {id}")
    return await _fetch(f"/v2/users/{id}/bugs", context=f"v2 user bugs {id}")


@mcp.resource("blt://v2/users/{id}/domains")
async def v2_get_user_domains(id: str) -> str:
    """Get user's domains by user ID."""
    logger.info(f"Fetching v2 user domains: {id}")
    return await _fetch(f"/v2/users/{id}/domains", context=f"v2 user domains {id}")


@mcp.resource("blt://v2/users/{id}/followers")
async def v2_get_user_followers(id: str) -> str:
    """Get user's followers by user ID."""
    logger.info(f"Fetching v2 user followers: {id}")
    return await _fetch(f"/v2/users/{id}/followers", context=f"v2 user followers {id}")


@mcp.resource("blt://v2/users/{id}/following")
async def v2_get_user_following(id: str) -> str:
    """Get user's following users by user ID."""
    logger.info(f"Fetching v2 user following: {id}")
    return await _fetch(f"/v2/users/{id}/following", context=f"v2 user following {id}")


@mcp.resource("blt://v2/domains")
async def v2_list_domains() -> str:
    """List domains."""
    logger.info("Fetching v2 domains list")
    return await _fetch("/v2/domains", context="v2 domains")


@mcp.resource("blt://v2/domains/{id}")
async def v2_get_domain(id: str) -> str:
    """Get domain by ID."""
    logger.info(f"Fetching v2 domain: {id}")
    return await _fetch(f"/v2/domains/{id}", context=f"v2 domain {id}")


@mcp.resource("blt://v2/domains/{id}/tags")
async def v2_get_domain_tags(id: str) -> str:
    """Get domain tags by domain ID."""
    logger.info(f"Fetching v2 domain tags: {id}")
    return await _fetch(f"/v2/domains/{id}/tags", context=f"v2 domain tags {id}")


@mcp.resource("blt://v2/organizations")
async def v2_list_organizations() -> str:
    """List organizations."""
    logger.info("Fetching v2 organizations list")
    return await _fetch("/v2/organizations", context="v2 organizations")


@mcp.resource("blt://v2/organizations/{id}")
async def v2_get_organization(id: str) -> str:
    """Get organization by ID."""
    logger.info(f"Fetching v2 organization: {id}")
    return await _fetch(f"/v2/organizations/{id}", context=f"v2 organization {id}")


@mcp.resource("blt://v2/organizations/{id}/domains")
async def v2_get_organization_domains(id: str) -> str:
    """Get organization domains by organization ID."""
    logger.info(f"Fetching v2 organization domains: {id}")
    return await _fetch(
        f"/v2/organizations/{id}/domains", context=f"v2 organization domains {id}"
    )


@mcp.resource("blt://v2/organizations/{id}/bugs")
async def v2_get_organization_bugs(id: str) -> str:
    """Get organization bugs by organization ID."""
    logger.info(f"Fetching v2 organization bugs: {id}")
    return await _fetch(
        f"/v2/organizations/{id}/bugs", context=f"v2 organization bugs {id}"
    )


@mcp.resource("blt://v2/organizations/{id}/managers")
async def v2_get_organization_managers(id: str) -> str:
    """Get organization managers by organization ID."""
    logger.info(f"Fetching v2 organization managers: {id}")
    return await _fetch(
        f"/v2/organizations/{id}/managers", context=f"v2 organization managers {id}"
    )


@mcp.resource("blt://v2/organizations/{id}/tags")
async def v2_get_organization_tags(id: str) -> str:
    """Get organization tags by organization ID."""
    logger.info(f"Fetching v2 organization tags: {id}")
    return await _fetch(
        f"/v2/organizations/{id}/tags", context=f"v2 organization tags {id}"
    )


@mcp.resource("blt://v2/organizations/{id}/integrations")
async def v2_get_organization_integrations(id: str) -> str:
    """Get organization integrations by organization ID."""
    logger.info(f"Fetching v2 organization integrations: {id}")
    return await _fetch(
        f"/v2/organizations/{id}/integrations",
        context=f"v2 organization integrations {id}",
    )


@mcp.resource("blt://v2/organizations/{id}/stats")
async def v2_get_organization_stats(id: str) -> str:
    """Get organization statistics by organization ID."""
    logger.info(f"Fetching v2 organization stats: {id}")
    return await _fetch(
        f"/v2/organizations/{id}/stats", context=f"v2 organization stats {id}"
    )


@mcp.resource("blt://v2/jobs")
async def v2_list_jobs() -> str:
    """List jobs."""
    logger.info("Fetching v2 jobs list")
    return await _fetch("/v2/jobs", context="v2 jobs")


@mcp.resource("blt://v2/jobs/{id}")
async def v2_get_job(id: str) -> str:
    """Get job by ID."""
    logger.info(f"Fetching v2 job: {id}")
    return await _fetch(f"/v2/jobs/{id}", context=f"v2 job {id}")


@mcp.resource("blt://v2/jobs/stats")
async def v2_get_jobs_stats() -> str:
    """Get jobs statistics."""
    logger.info("Fetching v2 jobs stats")
    return await _fetch("/v2/jobs/stats", context="v2 jobs stats")


@mcp.resource("blt://v2/hackathons")
async def v2_list_hackathons() -> str:
    """List hackathons."""
    logger.info("Fetching v2 hackathons list")
    return await _fetch("/v2/hackathons", context="v2 hackathons")


@mcp.resource("blt://v2/hackathons/{slug}")
async def v2_get_hackathon(slug: str) -> str:
    """Get hackathon by slug."""
    logger.info(f"Fetching v2 hackathon: {slug}")
    return await _fetch(f"/v2/hackathons/{slug}", context=f"v2 hackathon {slug}")


@mcp.resource("blt://v2/hunts")
async def v2_list_hunts() -> str:
    """List hunts."""
    logger.info("Fetching v2 hunts list")
    return await _fetch("/v2/hunts", context="v2 hunts")


@mcp.resource("blt://v2/hunts/active")
async def v2_get_active_hunts() -> str:
    """Get active hunts."""
    logger.info("Fetching v2 active hunts")
    return await _fetch("/v2/hunts/active", context="v2 active hunts")


@mcp.resource("blt://v2/hunts/previous")
async def v2_get_previous_hunts() -> str:
    """Get previous hunts."""
    logger.info("Fetching v2 previous hunts")
    return await _fetch("/v2/hunts/previous", context="v2 previous hunts")


@mcp.resource("blt://v2/hunts/upcoming")
async def v2_get_upcoming_hunts() -> str:
    """Get upcoming hunts."""
    logger.info("Fetching v2 upcoming hunts")
    return await _fetch("/v2/hunts/upcoming", context="v2 upcoming hunts")


@mcp.resource("blt://v2/hunts/{id}")
async def v2_get_hunt(id: str) -> str:
    """Get hunt by ID."""
    logger.info(f"Fetching v2 hunt: {id}")
    return await _fetch(f"/v2/hunts/{id}", context=f"v2 hunt {id}")


@mcp.resource("blt://v2/projects")
async def v2_list_projects() -> str:
    """List projects."""
    logger.info("Fetching v2 projects list")
    return await _fetch("/v2/projects", context="v2 projects")


@mcp.resource("blt://v2/projects/{id}")
async def v2_get_project(id: str) -> str:
    """Get project by ID."""
    logger.info(f"Fetching v2 project: {id}")
    return await _fetch(f"/v2/projects/{id}", context=f"v2 project {id}")


@mcp.resource("blt://v2/projects/{id}/contributors")
async def v2_get_project_contributors(id: str) -> str:
    """Get project contributors by project ID."""
    logger.info(f"Fetching v2 project contributors: {id}")
    return await _fetch(
        f"/v2/projects/{id}/contributors", context=f"v2 project contributors {id}"
    )


@mcp.resource("blt://v2/repos")
async def v2_list_repos() -> str:
    """List repos."""
    logger.info("Fetching v2 repos list")
    return await _fetch("/v2/repos", context="v2 repos")


@mcp.resource("blt://v2/repos/{id}")
async def v2_get_repo(id: str) -> str:
    """Get repo by ID."""
    logger.info(f"Fetching v2 repo: {id}")
    return await _fetch(f"/v2/repos/{id}", context=f"v2 repo {id}")


@mcp.resource("blt://v2/leaderboard")
async def v2_get_global_leaderboard() -> str:
    """Get global leaderboard."""
    logger.info("Fetching v2 global leaderboard")
    return await _fetch("/v2/leaderboard", context="v2 global leaderboard")


@mcp.resource("blt://v2/leaderboard/monthly")
async def v2_get_monthly_leaderboard() -> str:
    """Get monthly leaderboard."""
    logger.info("Fetching v2 monthly leaderboard")
    return await _fetch("/v2/leaderboard/monthly", context="v2 monthly leaderboard")


@mcp.resource("blt://v2/leaderboard/organizations")
async def v2_get_organizations_leaderboard() -> str:
    """Get organizations leaderboard."""
    logger.info("Fetching v2 organizations leaderboard")
    return await _fetch(
        "/v2/leaderboard/organizations", context="v2 organizations leaderboard"
    )


@mcp.resource("blt://v2/stats")
async def v2_stats() -> str:
    """Get overall BLT stats."""
    logger.info("Fetching v2 stats")
    return await _fetch("/v2/stats", context="v2 stats")


@mcp.resource("blt://v2/contributors")
async def v2_list_contributors() -> str:
    """List contributors."""
    logger.info("Fetching v2 contributors list")
    return await _fetch("/v2/contributors", context="v2 contributors")


@mcp.resource("blt://v2/contributors/{id}")
async def v2_get_contributor(id: str) -> str:
    """Get contributor by ID."""
    logger.info(f"Fetching v2 contributor: {id}")
    return await _fetch(f"/v2/contributors/{id}", context=f"v2 contributor {id}")
