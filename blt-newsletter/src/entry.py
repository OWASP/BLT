from js import Request, Response, URL
from workers import WorkerEntrypoint


ROUTES = {
    "/": "index.html",
    "/dashboard": "dashboard.html",
    "/login": "login.html",
    "/docs": "docs.html",
}

CANONICAL_REDIRECTS = {
    "/dashboard.html": "/dashboard",
    "/login.html": "/login",
    "/docs.html": "/docs",
}


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        url = URL.new(request.url)
        path = normalize_path(url.pathname)

        if path in CANONICAL_REDIRECTS:
            return Response.redirect(CANONICAL_REDIRECTS[path], 308)

        asset_name = ROUTES.get(path)
        if asset_name is not None:
            return await self.serve_asset(request, "/" + asset_name)

        return await self.env.ASSETS.fetch(request)

    async def serve_asset(self, request, pathname):
        url = URL.new(request.url)
        url.pathname = pathname
        url.search = ""
        asset_request = Request.new(url.toString())

        return await self.env.ASSETS.fetch(asset_request)


def normalize_path(path):
    if path != "/" and path.endswith("/"):
        return path.rstrip("/")

    return path
