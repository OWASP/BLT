#!/usr/bin/env python3
"""The live site of each project folder: the custom domain of the Worker it deploys.

Each folder's wrangler.toml (or, for a folder that deploys from a subfolder, the wrangler.toml in
the deploy directory listed in scripts/deploy/projects.tsv) names its Worker (``name = "..."``). Cloudflare's
``/accounts/<id>/workers/domains`` lists every custom domain with the Worker it serves, so with
CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID set the live URL comes from there. Without them,
or when the API call fails, the ``pattern`` of a ``custom_domain = true`` route in the folder's
wrangler.toml is used. A Worker with several domains prefers the one named after the folder
(``blt-pool`` -> ``pool.owaspblt.org``), then the shortest.
"""

import json
import os
import re
import urllib.request

API = "https://api.cloudflare.com/client/v4/accounts/{account}/workers/domains?per_page=500"
NAME = re.compile(r'^\s*name\s*=\s*"([^"]+)"', re.M)
PATTERN = re.compile(r'pattern\s*=\s*"([^"/*]+)"[^\n]*(?:\n[^\[\n]*)*?custom_domain\s*=\s*true', re.M)


def _read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return ""


def wrangler_path(root, folder):
    """<folder>/wrangler.toml, else the one in the folder's deploy directory
    (scripts/deploy/projects.tsv: blt-vanish deploys from blt-vanish/cloudflare_workers), else None."""
    path = os.path.join(root, folder, "wrangler.toml")
    if os.path.isfile(path):
        return path
    for line in _read(os.path.join(root, "scripts", "deploy", "projects.tsv")).splitlines():
        cols = line.split("\t")
        if len(cols) > 1 and cols[0] == folder and not line.startswith("#"):
            path = os.path.join(root, cols[1], "wrangler.toml")
            return path if os.path.isfile(path) else None
    return None


def worker_name(root, folder):
    """The top-level ``name`` of the folder's wrangler.toml, or None."""
    text = _read(wrangler_path(root, folder) or "")
    top = text.split("\n[", 1)[0]
    match = NAME.search(top)
    return match.group(1) if match else None


def wrangler_domains(root, folder):
    """Custom domains declared in the folder's wrangler.toml routes."""
    return PATTERN.findall(_read(wrangler_path(root, folder) or ""))


def cloudflare_domains(token=None, account=None, timeout=20):
    """{worker name: [hostname, ...]} from the Cloudflare API, or None when unavailable."""
    token = token or os.getenv("CLOUDFLARE_API_TOKEN")
    account = account or os.getenv("CLOUDFLARE_ACCOUNT_ID")
    if not token or not account:
        return None
    request = urllib.request.Request(API.format(account=account),
                                     headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError):
        return None
    if not data.get("success"):
        return None
    found = {}
    for row in data.get("result") or []:
        service, host = row.get("service"), row.get("hostname")
        if service and host:
            found.setdefault(service, []).append(host)
    return found


def pick(folder, hosts):
    """The domain to show for a folder: one named after it, else the shortest."""
    hosts = sorted({h.strip().lower() for h in hosts if h and h.strip()}, key=lambda h: (len(h), h))
    if not hosts:
        return None
    short = folder[4:] if folder.startswith("blt-") else folder
    for host in hosts:
        if host.split(".")[0] in (short, folder):
            return host
    return hosts[0]


def live_urls(root, folders, domains=None):
    """{folder: "https://<host>/" or None} for the given folders."""
    urls = {}
    for folder in folders:
        hosts = []
        service = worker_name(root, folder)
        if domains is not None and service:
            hosts = domains.get(service) or []
        if not hosts:
            hosts = wrangler_domains(root, folder)
        host = pick(folder, hosts)
        urls[folder] = f"https://{host}/" if host else None
    return urls
