import datetime
import html
import json
import os
import re
from urllib.parse import quote, urlsplit

import requests
import yaml

GITHUB_API_URL = "https://api.github.com"
ORG_NAME = "OWASP"
ADDITIONAL_PROJECTS = [
    {"name": "ASVS", "repo_url": "https://github.com/OWASP/ASVS"},
    {
        # The BLT monorepo is on git.owaspblt.org, not GitHub: its FUNDING.yml comes from the
        # forge's raw API and its contributors from the list the README generator keeps.
        "name": "BLT",
        "repo_url": "https://git.owaspblt.org/BLT",
        "raw_url": "https://git.owaspblt.org/api/repo/owasp-blt/BLT/raw?ref=main&path={}",
    },
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

# FUNDING.yml platforms (https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/displaying-a-sponsor-button-in-your-repository)
# and the page each handle points to. "custom" values are URLs.
PLATFORMS = {
    "github": ("GitHub Sponsors", "https://github.com/sponsors/{}"),
    "open_collective": ("Open Collective", "https://opencollective.com/{}"),
    "patreon": ("Patreon", "https://www.patreon.com/{}"),
    "ko_fi": ("Ko-fi", "https://ko-fi.com/{}"),
    "liberapay": ("Liberapay", "https://liberapay.com/{}"),
    "buy_me_a_coffee": ("Buy Me a Coffee", "https://www.buymeacoffee.com/{}"),
    "polar": ("Polar", "https://polar.sh/{}"),
    "thanks_dev": ("thanks.dev", "https://thanks.dev/{}"),
    "tidelift": ("Tidelift", "https://tidelift.com/funding/github/{}"),
    "community_bridge": ("LFX Mentorship", "https://funding.communitybridge.org/projects/{}"),
    "lfx_crowdfunding": ("LFX Crowdfunding", "https://crowdfunding.lfx.linuxfoundation.org/projects/{}"),
    "issuehunt": ("IssueHunt", "https://issuehunt.io/r/{}"),
    "otechie": ("Otechie", "https://otechie.com/{}"),
}
GITHUB_LOGIN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
CONTRIBUTORS_CHECKED = 12  # top contributors per repository checked for GitHub Sponsors
CONTRIBUTORS_SHOWN = 8


def github_headers():
    token = os.environ.get("GITHUB_TOKEN")
    return {"Authorization": f"token {token}"} if token else {}


def get_owasp_repos():
    url = f"{GITHUB_API_URL}/orgs/{ORG_NAME}/repos?per_page=100"
    repos = []
    while url:
        response = requests.get(url, headers=github_headers())
        response.raise_for_status()
        repos.extend(response.json())
        url = response.links.get("next", {}).get("url")
    return repos


def github_repo(repo_url):
    """owner/name for a github.com repository URL, else None."""
    parts = urlsplit(repo_url)
    path = parts.path.strip("/").split("/")
    if parts.netloc.lower() != "github.com" or len(path) < 2:
        return None
    return f"{path[0]}/{path[1]}"


def raw_file_url(project, path):
    """Where to read a file of the project's repository, or None."""
    if project.get("raw_url"):
        return project["raw_url"].format(quote(path, safe=""))
    repo_name = github_repo(project["repo_url"])
    if repo_name:
        # HEAD is the default branch, whatever it is called.
        return f"https://raw.githubusercontent.com/{repo_name}/HEAD/{path}"
    return None


def check_funding_file(project):
    funding_url = raw_file_url(project, ".github/FUNDING.yml")
    if not funding_url:
        return None
    response = requests.get(funding_url)
    print(f"Checking funding URL: {funding_url} - Status Code: {response.status_code}")
    if response.status_code == 200:
        return funding_url


def is_owasp_foundation(link):
    """Links that fund the OWASP Foundation rather than the project: owasp.org/donate and the
    OWASP organization's own GitHub Sponsors page."""
    url = link["url"].lower()
    return url.startswith(("https://owasp.org/donate", "http://owasp.org/donate",
                           "https://www.owasp.org/donate")) or url == "https://github.com/sponsors/owasp"


def funding_links_from_yaml(content):
    """Turn a parsed FUNDING.yml into [{platform, label, handle, url, owasp}]. Values are
    third-party input: only http(s) URLs survive, and the page escapes everything."""
    links = []
    if not isinstance(content, dict):
        return links
    for platform, values in content.items():
        platform = str(platform).strip().lower()
        if values is None:
            continue
        for value in values if isinstance(values, list) else [values]:
            if value is None or str(value).strip() == "":
                continue
            value = str(value).strip()
            if platform == "custom":
                if "://" not in value and "." in value and " " not in value:
                    value = "https://" + value
                url = safe_href(value)
                label = urlsplit(url).netloc.removeprefix("www.") if url else value
                handle = ""
            elif platform in PLATFORMS:
                label, pattern = PLATFORMS[platform]
                url = safe_href(pattern.format(quote(value, safe="/-_.")))
                handle = value
            else:
                continue
            if not url:
                continue
            link = {"platform": platform, "label": label, "handle": handle, "url": url}
            link["owasp"] = is_owasp_foundation(link)
            links.append(link)
    return links


def parse_funding_file(funding_url):
    """(funding_details, funding_links): the raw values joined, as before, and the links."""
    response = requests.get(funding_url)
    if response.status_code != 200:
        return "", []
    try:
        content = yaml.safe_load(response.text)
    except yaml.YAMLError:
        return "", []
    if not isinstance(content, dict):
        return "", []
    values = []
    for value in content.values():
        values.extend(value if isinstance(value, list) else [value])
    details = ", ".join(str(v) for v in values if v is not None)
    return details, funding_links_from_yaml(content)


def get_forge_contributors(project):
    """Top contributors with a GitHub account, from the .forkmesh/contributors/contributors.json
    that the BLT monorepo's README generator keeps."""
    response = requests.get(raw_file_url(project, ".forkmesh/contributors/contributors.json"))
    if response.status_code != 200:
        print(f"Contributors of {project['name']}: status {response.status_code}")
        return []
    people = sorted(
        (p for p in (response.json() or {}).get("contributors") or [] if isinstance(p, dict)),
        key=lambda p: -(p.get("commits") or 0),
    )
    return [
        {"login": p["github"], "contributions": p.get("commits") or 0}
        for p in people
        if isinstance(p.get("github"), str) and GITHUB_LOGIN.match(p["github"])
    ][:CONTRIBUTORS_CHECKED * 4]  # one request for the whole list, and a monorepo has many people


def get_contributors(project):
    """Top human contributors of the project's repository, most commits first."""
    if project.get("raw_url"):
        return get_forge_contributors(project)
    repo_name = github_repo(project["repo_url"])
    if not repo_name:
        return []
    response = requests.get(
        f"{GITHUB_API_URL}/repos/{repo_name}/contributors",
        params={"per_page": CONTRIBUTORS_CHECKED + 5},
        headers=github_headers(),
    )
    if response.status_code != 200:
        print(f"Contributors of {repo_name}: status {response.status_code}")
        return []
    people = []
    for person in response.json():
        login = person.get("login") or ""
        if person.get("type") != "User" or login.endswith("[bot]") or not GITHUB_LOGIN.match(login):
            continue
        people.append({"login": login, "contributions": person.get("contributions", 0)})
    return people[:CONTRIBUTORS_CHECKED]


def sponsorable_logins(logins):
    """The subset of GitHub logins with GitHub Sponsors turned on. GraphQL when there is a token
    (one query per 50 logins); otherwise the public github.com/sponsors/<login> page, which
    redirects to the profile when there is no listing."""
    logins = sorted({login for login in logins if GITHUB_LOGIN.match(login)}, key=str.lower)
    found = set()
    if os.environ.get("GITHUB_TOKEN"):
        for start in range(0, len(logins), 50):
            chunk = logins[start:start + 50]
            fields = " ".join(
                f'u{i}: user(login: "{login}") {{ login hasSponsorsListing }}' for i, login in enumerate(chunk)
            )
            response = requests.post(
                f"{GITHUB_API_URL}/graphql", json={"query": f"{{ {fields} }}"}, headers=github_headers()
            )
            if response.status_code != 200:
                print(f"GraphQL sponsors check: status {response.status_code}")
                continue
            for user in ((response.json() or {}).get("data") or {}).values():
                if user and user.get("hasSponsorsListing"):
                    found.add(user["login"])
        return found
    for login in logins:
        response = requests.get(f"https://github.com/sponsors/{login}", allow_redirects=False)
        if response.status_code == 200:
            found.add(login)
    return found


def add_contributor_sponsors(project_links):
    """Give every project a contributor_sponsors list: its top contributors who take GitHub
    Sponsors, leaving out anyone its FUNDING.yml already lists."""
    contributors = {p["repo_url"]: get_contributors(p) for p in project_links}
    sponsorable = sponsorable_logins(c["login"] for people in contributors.values() for c in people)
    for project in project_links:
        listed = {
            link["handle"].lower() for link in project.get("funding_links", []) if link["platform"] == "github"
        }
        project["contributor_sponsors"] = [
            {
                "login": c["login"],
                "url": f"https://github.com/sponsors/{c['login']}",
                "contributions": c["contributions"],
            }
            for c in contributors[project["repo_url"]]
            if c["login"] in sponsorable and c["login"].lower() not in listed
        ][:CONTRIBUTORS_SHOWN]


PAGE_HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BLT Tomato - Fund OWASP Projects</title>
    <meta name="description" content="Every way to fund an OWASP project: the links each project publishes in its FUNDING.yml, and its contributors who take GitHub Sponsors.">
    <link rel="icon" type="image/svg+xml" href="/logo.svg">
    <script src="/theme-init.js"></script>
    <script src="https://owaspblt.org/_shared/blt-nav.js" defer></script>
    <style>
        /* Tokens follow the BLT design guide (design.owaspblt.org), as in blt-waypoint. */
        :root {
            --bg: #f9fafb; --surface: #ffffff; --surface-2: #f3f4f6;
            --border: #e5e7eb; --border-strong: #d1d5db;
            --text: #111827; --text-2: #374151; --muted: #6b7280; --faint: #9ca3af;
            --brand: #dc2626; --brand-hover: #b91c1c; --brand-text: #dc2626; --brand-soft: #fef2f2;
            --brand-ring: rgba(220, 38, 38, .28);
            --warn: #b45309; --warn-soft: #fffbeb; --warn-ring: #fcd34d;
            --shadow: 0 1px 2px rgba(17, 24, 39, .05);
            --shadow-lift: 0 6px 24px rgba(17, 24, 39, .08);
            --sans: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            color-scheme: light;
        }
        html.dark {
            --bg: #030712; --surface: #111827; --surface-2: #1f2937;
            --border: #1f2937; --border-strong: #374151;
            --text: #f9fafb; --text-2: #d1d5db; --muted: #9ca3af; --faint: #6b7280;
            --brand-text: #f87171; --brand-soft: rgba(220, 38, 38, .14); --brand-ring: rgba(248, 113, 113, .35);
            --warn: #fbbf24; --warn-soft: rgba(245, 158, 11, .10); --warn-ring: rgba(251, 191, 36, .35);
            --shadow: none; --shadow-lift: 0 6px 24px rgba(0, 0, 0, .45);
            color-scheme: dark;
        }
        *, *::before, *::after { box-sizing: border-box; }
        html { -webkit-text-size-adjust: 100%; overflow-x: clip; }
        body {
            margin: 0; min-height: 100vh; display: flex; flex-direction: column;
            background: var(--bg); color: var(--text); font: 14px/1.5 var(--sans);
            -webkit-font-smoothing: antialiased;
        }
        blt-nav:not(:defined) { display: block; min-height: 61px; }
        blt-nav:not(:defined) > * { display: none; }
        a { color: inherit; text-decoration: none; }
        :focus-visible { outline: 2px solid var(--brand-text); outline-offset: 2px; }
        .wrap { width: 100%; max-width: 1100px; margin: 0 auto; padding: 0 16px; }
        main.wrap { flex: 1; padding-top: 24px; padding-bottom: 40px; }

        .page-head { display: flex; align-items: center; gap: 16px; margin-bottom: 18px; }
        .page-head img { width: 56px; height: 56px; flex: none; }
        .page-head h1 { margin: 0; font-size: 24px; line-height: 30px; font-weight: 800; letter-spacing: -.02em; }
        .page-head p { margin: 4px 0 0; color: var(--muted); max-width: 70ch; }

        .notice {
            display: flex; gap: 12px; padding: 14px 16px; margin-bottom: 18px;
            border: 1px solid var(--warn-ring); border-radius: 16px; background: var(--warn-soft);
        }
        .notice .icon { color: var(--warn); font-size: 18px; line-height: 22px; flex: none; }
        .notice h2 { margin: 0 0 4px; font-size: 15px; line-height: 22px; }
        .notice p { margin: 0 0 6px; color: var(--text-2); }
        .notice p:last-child { margin-bottom: 0; }
        .notice a { color: var(--brand-text); text-decoration: underline; text-underline-offset: 2px; }

        .stats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; margin-bottom: 18px; }
        .stat { padding: 10px 14px; border: 1px solid var(--border); border-radius: 12px; background: var(--surface); box-shadow: var(--shadow); }
        .stat b { display: block; font-size: 20px; line-height: 26px; font-variant-numeric: tabular-nums; }
        .stat span { color: var(--muted); font-size: 12px; }

        .cards { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
        .card {
            min-width: 0; display: flex; flex-direction: column; gap: 12px; padding: 16px;
            border: 1px solid var(--border); border-radius: 16px; background: var(--surface); box-shadow: var(--shadow);
            transition: box-shadow .15s, border-color .15s;
        }
        .card:hover { border-color: var(--border-strong); box-shadow: var(--shadow-lift); }
        .card-head h3 { margin: 0; font-size: 16px; line-height: 22px; overflow-wrap: anywhere; }
        .card-head h3 a:hover { color: var(--brand-text); }
        .card-head .repo { display: block; color: var(--faint); font: 12px/18px var(--mono); overflow-wrap: anywhere; }
        .label { margin: 0 0 6px; color: var(--muted); font-size: 11px; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; }
        .links { display: flex; flex-wrap: wrap; gap: 6px; }
        .fund {
            display: inline-flex; align-items: center; gap: 6px; max-width: 100%; padding: 5px 11px;
            border-radius: 999px; background: var(--brand); color: #fff; font-weight: 600; font-size: 13px;
        }
        .fund:hover { background: var(--brand-hover); }
        .fund span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .fund small { font-weight: 400; opacity: .85; }
        .person {
            display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px 3px 3px;
            border: 1px solid var(--border); border-radius: 999px; background: var(--surface-2); font-size: 13px;
        }
        .person:hover { border-color: var(--brand-ring); color: var(--brand-text); }
        .person img { width: 22px; height: 22px; border-radius: 50%; background: var(--border); }
        .none { margin: 0; color: var(--muted); font-size: 13px; }
        .foundation { margin: auto 0 0; padding-top: 10px; border-top: 1px dashed var(--border); color: var(--faint); font-size: 12px; }
        .foundation a { text-decoration: underline; text-underline-offset: 2px; }
        .foundation a:hover { color: var(--text-2); }

        .foot { border-top: 1px solid var(--border); padding: 16px 0 20px; color: var(--muted); font-size: 12px; }
        .foot .wrap { display: flex; flex-wrap: wrap; gap: 6px 16px; justify-content: space-between; }
        .foot a { color: var(--brand-text); }
        .foot a:hover { text-decoration: underline; }

        @media (max-width: 720px) {
            .cards { grid-template-columns: minmax(0, 1fr); }
            .stats { grid-template-columns: minmax(0, 1fr); }
            .stat { display: flex; align-items: baseline; gap: 8px; }
            .page-head { align-items: flex-start; }
            .page-head img { width: 44px; height: 44px; }
            .page-head h1 { font-size: 20px; line-height: 26px; }
        }
    </style>
</head>
<body>
    <blt-nav project="blt-tomato" name="Tomato">
        <a href="https://git.owaspblt.org/BLT/BLT-Tomato" slot="actions">Source</a>
    </blt-nav>
    <main class="wrap">
        <div class="page-head">
            <img src="/logo.svg" alt="" width="56" height="56">
            <div>
                <h1>Fund OWASP projects</h1>
                <p>BLT Tomato is an OWASP BLT project that helps other OWASP projects. It lists every project that publishes a FUNDING.yml, with each way to support it: the project's own funding links, and the contributors who take GitHub Sponsors.</p>
            </div>
        </div>
        <aside class="notice" role="note">
            <span class="icon" aria-hidden="true">&#9888;</span>
            <div>
                <h2>OWASP no longer collects donations for individual projects</h2>
                <p>Many projects still list an owasp.org/donate link in their FUNDING.yml. Those links support the OWASP Foundation as a whole, not the project named in them. To fund a particular project, use the project's own links below or sponsor the people who build it on GitHub Sponsors.</p>
                <p>Maintainers: point your <a href="https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/displaying-a-sponsor-button-in-your-repository">FUNDING.yml</a> at your own GitHub Sponsors, Open Collective or other page, and this list picks it up within a week.</p>
            </div>
        </aside>
"""

PAGE_FOOT = """    </main>
    <footer class="foot">
        <div class="wrap">
            <span>Built from each project's .github/FUNDING.yml and its contributors on GitHub, refreshed weekly. Last built {built}.</span>
            <span><a href="/project_repos_links.json">JSON</a> &middot; <a href="https://git.owaspblt.org/BLT/BLT-Tomato">View this script</a></span>
        </div>
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


def render_project_item(project):
    """One card for a project. Names, URLs and FUNDING.yml values come from third-party repos,
    so every value is escaped and only http(s) URLs become links."""
    links = [link for link in project.get("funding_links") or [] if safe_href(link.get("url"))]
    direct = [link for link in links if not link.get("owasp")]
    foundation = [link for link in links if link.get("owasp")]
    people = [p for p in project.get("contributor_sponsors") or [] if GITHUB_LOGIN.match(str(p.get("login", "")))]

    repo_href = safe_href(project.get("repo_url"))
    name = esc(project.get("project_name"))
    name_html = f'<a href="{esc(repo_href)}">{name}</a>' if repo_href else name
    repo_path = esc(urlsplit(repo_href).path.strip("/")) if repo_href else ""

    out = [f'<li class="card">\n<div class="card-head"><h3>{name_html}</h3>']
    if repo_path:
        out.append(f'<span class="repo">{repo_path}</span>')
    out.append("</div>\n<div>\n<p class=\"label\">Fund the project</p>\n")
    if direct:
        out.append('<div class="links">')
        for link in direct:
            handle = f" <small>{esc(link['handle'])}</small>" if link.get("handle") else ""
            out.append(
                f'<a class="fund" href="{esc(link["url"])}" rel="noopener"><span>&#10084; {esc(link["label"])}{handle}</span></a>'
            )
        out.append("</div>\n")
    else:
        out.append('<p class="none">No funding link of its own yet.</p>\n')
    out.append("</div>\n")
    if people:
        out.append('<div>\n<p class="label">Sponsor its contributors</p>\n<div class="links">')
        for person in people:
            login = esc(person["login"])
            out.append(
                f'<a class="person" href="https://github.com/sponsors/{login}" rel="noopener"'
                f' title="{login} on GitHub Sponsors">'
                f'<img src="https://avatars.githubusercontent.com/{login}?s=44" alt="" width="22" height="22" loading="lazy">'
                f"{login}</a>"
            )
        out.append("</div>\n</div>\n")
    if foundation:
        parts = ", ".join(
            f'<a href="{esc(link["url"])}" rel="noopener">{"GitHub Sponsors" if link["platform"] == "github" else "owasp.org/donate"}</a>'
            for link in foundation
        )
        out.append(f'<p class="foundation">Also lists the OWASP Foundation ({parts}), which no longer earmarks gifts for this project.</p>\n')
    out.append("</li>\n")
    return "".join(out)


def render_index_html(project_links, built=None):
    built = built or datetime.date.today().isoformat()
    projects = sorted(project_links, key=lambda p: str(p.get("project_name", "")).lower())
    direct = sum(
        1 for p in projects if any(not link.get("owasp") for link in p.get("funding_links") or [])
    )
    people = {s.get("login") for p in projects for s in p.get("contributor_sponsors") or []}
    stats = (
        '        <section class="stats" aria-label="Totals">\n'
        f'            <div class="stat"><b>{len(projects)}</b><span>projects with a FUNDING.yml</span></div>\n'
        f'            <div class="stat"><b>{direct}</b><span>with a funding link of their own</span></div>\n'
        f'            <div class="stat"><b>{len(people)}</b><span>contributors on GitHub Sponsors</span></div>\n'
        "        </section>\n"
    )
    items = "".join(render_project_item(project) for project in projects)
    return (
        PAGE_HEAD + stats + '        <ul class="cards">\n' + items + "        </ul>\n"
        + PAGE_FOOT.replace("{built}", esc(built))
    )


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
        funding_url = check_funding_file(project)
        if funding_url:
            funding_details, funding_links = parse_funding_file(funding_url)
            project_links.append(
                {
                    "project_name": project_name,
                    "repo_url": repo_url,
                    **({"raw_url": project["raw_url"]} if project.get("raw_url") else {}),
                    "funding_url": funding_url,
                    "funding_details": funding_details,
                    "funding_links": funding_links,
                }
            )
            print(f"Added project: {project_name} with funding details: {funding_details}")

    add_contributor_sponsors(project_links)

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
