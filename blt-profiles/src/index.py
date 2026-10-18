import json
import re

from workers import Response, WorkerEntrypoint


# Profile submissions are issues on git.owaspblt.org, committed by
# .forkmesh/blt-profiles--add-profile.yml (scripts/actions/add-profile.mjs).
RESERVED_PATHS = {
    "api",
    "favicon.ico",
    "index.html",
    "profile.html",
    "profiles",
    "robots.txt",
    "webhooks",
}


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        path = _path_from_url(request.url)

        if path == "/api/health":
            return _json({"ok": True, "service": "blt-profiles"})

        if request.method in ("GET", "HEAD") and _maybe_profile_page(path):
            return await self.env.ASSETS.fetch("https://assets.local/profile.html")

        return await self.env.ASSETS.fetch(request)


def _maybe_profile_page(path):
    parts = [part for part in path.split("/") if part]
    if len(parts) != 1:
        return False
    slug = parts[0]
    if slug in RESERVED_PATHS:
        return False
    return re.match(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{1,38}$", slug) is not None


def _path_from_url(url):
    match = re.match(r"^https?://[^/]+([^?#]*)", str(url))
    return match.group(1) or "/" if match else "/"


def _json(data, status=200):
    return Response(
        json.dumps(data, indent=2),
        status=status,
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
