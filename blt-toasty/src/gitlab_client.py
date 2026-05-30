"""GitLab API client module for Cloudflare Workers."""

import json

from js import fetch
from pyodide.ffi import to_js


async def call_gitlab_api(endpoint: str, method: str, env, body: dict = None) -> dict:
    """Executes a fetch request to the GitLab API.

    Args:
        endpoint: The GitLab API endpoint path (e.g., 'projects/1/issues').
        method: The HTTP method (e.g., 'GET', 'POST').
        env: The Cloudflare environment object containing secrets.
        body: Optional dictionary containing request body data.

    Returns:
        A dictionary containing the JSON parsed response.

    Raises:
        RuntimeError: If the HTTP response status code is not a 2xx success.
    """
    url = f"https://gitlab.com/api/v4/{endpoint}"

    headers = {
        "Authorization": f"Bearer {env.GITLAB_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    options = {
        "method": method,
        "headers": headers,
    }

    if body is not None:
        options["body"] = json.dumps(body)

    js_options = to_js(options)
    response = await fetch(url, js_options)

    if not response.ok:
        raise RuntimeError(f"GitLab API error: {response.status} {response.statusText}")

    response_json = await response.json()
    return response_json.to_py()
