import html
import json
import os
from urllib.parse import urlsplit

import requests
import yaml

GITHUB_API_URL = "https://api.github.com"
ORG_NAME = "OWASP"
ADDITIONAL_PROJECTS = [
    {"name": "ASVS", "repo_url": "https://github.com/OWASP/ASVS"},
    {"name": "BLT", "repo_url": "https://git.owaspblt.org/BLT/BLT-Core"},
    {"name": "CycloneDX", "repo_url": "https://github.com/CycloneDX/cyclonedx-cli"},
    {
        "name": "Dependency-Track",
        "repo_url": "https://github.com/DependencyTrack/dependency-track",
    },
    {"name": "Juice Shop", "repo_url": "https://github.com/juice-shop/juice-shop"},
    {"name": "MAS", "repo_url": "https://github.com/OWASP/owasp-masvs"},
    {
        "name": "ModSecurity Core Rule Set",
        "repo_url": "https://github.com/coreruleset/coreruleset",
    },
    {"name": "OpenCRE", "repo_url": "https://github.com/OWASP/OpenCRE"},
    {"name": "SAMM", "repo_url": "https://github.com/OWASP/samm"},
    {"name": "Wrongsecrets", "repo_url": "https://github.com/OWASP/wrongsecrets"},
    {"name": "AMASS", "repo_url": "https://github.com/owasp-amass/amass"},
]


def get_owasp_repos():
    url = f"{GITHUB_API_URL}/orgs/{ORG_NAME}/repos?per_page=100"
    token = os.environ.get("GITHUB_TOKEN")
    headers = {"Authorization": f"token {token}"} if token else {}
    repos = []
    while url:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        repos.extend(response.json())
        url = response.links.get("next", {}).get("url")
    return repos


def check_funding_file(repo_url):
    repo_name = "/".join(repo_url.split("/")[-2:])
    funding_url = (
        f"https://raw.githubusercontent.com/{repo_name}/master/.github/FUNDING.yml"
    )
    response = requests.get(funding_url)
    print(f"Checking funding URL: {funding_url} - Status Code: {response.status_code}")
    if response.status_code == 200:
        return funding_url


def parse_funding_file(funding_url):
    response = requests.get(funding_url)
    if response.status_code == 200:
        funding_content = yaml.safe_load(response.text)
        funding_links = []
        for _, value in funding_content.items():
            if isinstance(value, list):
                funding_links.extend(value)
            else:
                funding_links.append(value)
        return ", ".join(funding_links)
    return ""


PAGE_HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BLT Tomato - OWASP Projects Seeking Funding</title>
    <script src="/theme-init.js"></script>
    <script src="https://owaspblt.org/_shared/blt-nav.js" defer></script>
    <style>
        :root {
            --bg: #f9fafb; --surface: #ffffff; --border: #e5e7eb;
            --text: #111827; --muted: #4b5563; --accent: #dc2626; --accent-text: #dc2626;
        }
        html.dark {
            --bg: #030712; --surface: #111827; --border: #1f2937;
            --text: #f3f4f6; --muted: #9ca3af; --accent: #dc2626; --accent-text: #f87171;
            color-scheme: dark;
        }
        body {
            font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: var(--bg);
            color: var(--text);
        }
        a { color: var(--accent-text); }
        blt-nav:not(:defined) { display: block; min-height: 61px; }
        blt-nav:not(:defined) > * { display: none; }
        main h1 {
            font-size: 24px;
            margin: 12px 0 8px;
        }
        main {
            padding: 20px;
            max-width: 1100px;
            margin: 0 auto;
        }
        ul {
            list-style-type: none;
            padding: 0;
        }
        li {
            background-color: var(--surface);
            border: 1px solid var(--border);
            margin: 10px 0;
            padding: 12px 16px;
            border-radius: 16px;
            overflow-wrap: anywhere;
        }
        li span { color: var(--muted); }
        .heart-icon {
            color: var(--accent);
            margin-left: 10px;
            text-decoration: none;
        }
        .donate-button {
            display: inline-block;
            padding: 5px 10px;
            background-color: var(--accent);
            color: white;
            border-radius: 8px;
            text-decoration: none;
        }
        .donate-button:hover { background-color: #b91c1c; }
        footer {
            text-align: center;
            padding: 20px;
            background-color: var(--surface);
            border-top: 1px solid var(--border);
            color: var(--muted);
        }
        footer a {
            color: var(--accent-text);
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <blt-nav project="blt-tomato" name="Tomato">
        <a href="https://git.owaspblt.org/BLT/BLT-Tomato" slot="actions">Source</a>
    </blt-nav>
    <main>
        <h1>BLT Tomato - this is an OWASP BLT project created to help other OWASP projects.</h1>
        <p>The following OWASP projects are seeking funding and have a funding.yml file:</p>
        <ul>
"""

PAGE_FOOT = """
        </ul>
    </main>
    <footer>
        <p><a href="https://git.owaspblt.org/BLT/BLT-Tomato">View this script</a></p>
    </footer>
</body>
</html>
"""


def esc(value):
    """HTML-escape any value for text or a double/single-quoted attribute."""
    return html.escape("" if value is None else str(value), quote=True)


def safe_href(value):
    """Return the URL if it is an absolute http(s) URL, else None (no javascript:, data:, etc.)."""
    if not isinstance(value, str):
        return None
    url = value.strip()
    if any(ord(c) < 0x20 or c.isspace() for c in url):
        return None
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    if parts.scheme.lower() not in ("http", "https") or not parts.netloc:
        return None
    return url


def render_project_item(index, project):
    """One <li> for a project. Names, URLs and FUNDING.yml values come from third-party repos,
    so every value is escaped and only http(s) URLs become links."""
    funding_links_html = ""
    for link in str(project.get("funding_details") or "").split(", "):
        href = safe_href(link)
        if not href:
            continue
        if "https://owasp.org/donate/" in href:
            funding_links_html += f'<a href="{esc(href)}" class="donate-button">Donate</a> '
        else:
            funding_links_html += f'<a href="{esc(href)}" class="heart-icon">&#10084;</a> '
    repo_href = safe_href(project.get("repo_url"))
    name = esc(project.get("project_name"))
    name_html = f'<a href="{esc(repo_href)}">{name}</a>' if repo_href else name
    return (
        f"<li>{index}. {name_html} {funding_links_html}"
        f'<span>{esc(project.get("funding_details"))}</span></li>\n'
    )


def render_index_html(project_links):
    items = "".join(
        render_project_item(index, project)
        for index, project in enumerate(
            sorted(project_links, key=lambda p: str(p.get("project_name", ""))), start=1
        )
    )
    return PAGE_HEAD + items + PAGE_FOOT


def main():
    # Fetch OWASP repos
    owasp_repos = get_owasp_repos()
    owasp_repos_data = [
        {"name": repo["name"], "repo_url": repo["html_url"]} for repo in owasp_repos
    ]

    # Combine OWASP repos and additional projects
    data = owasp_repos_data + ADDITIONAL_PROJECTS

    # Remove duplicates based on the 'repo_url' key
    unique_data = {project["repo_url"]: project for project in data}.values()

    project_links = []

    for project in unique_data:
        project_name = project["name"]
        repo_url = project["repo_url"]

        if project_name.startswith("www-"):
            print(f"Skipping repository: {project_name}")
            continue

        print("project name", project_name)
        funding_url = check_funding_file(repo_url)
        if funding_url:
            funding_details = parse_funding_file(funding_url)
            project_links.append(
                {
                    "project_name": project_name,
                    "repo_url": repo_url,
                    "funding_url": funding_url,
                    "funding_details": funding_details,
                }
            )
            print(f"Added project: {project_name} with funding details: {funding_details}")

    # Write the JSON output file
    OUTPUT_DIR = os.environ.get("OUTPUT_DIR", ".")
    output_file = os.path.join(OUTPUT_DIR, "project_repos_links.json")
    with open(output_file, "w") as f:
        json.dump(project_links, f, indent=2)

    print(f"Output written to '{output_file}'")

    html_content = render_index_html(project_links)

    with open(os.path.join(OUTPUT_DIR, "index.html"), "w") as f:
        f.write(html_content)

    print("index.html file has been created.")


if __name__ == "__main__":
    main()
