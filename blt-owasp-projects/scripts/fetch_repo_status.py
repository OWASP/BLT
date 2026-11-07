"""repo_status.json: every OWASP project from owasp.github.io's projects.json, with its GitHub repo's
stats, top contributors and recent activity. Run daily by scripts/refresh-kv.sh (about 7 GitHub
requests per repository, so it needs a token: GITHUB_TOKEN or ACCESS_TOKEN)."""

import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import requests

# Bots are left out of the contributor lists with the same rules as the BLT README wall.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'readme'))
from contributors import is_bot  # noqa: E402

OUTPUT_DIR = os.environ.get('OUTPUT_DIR', 'public')
OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'repo_status.json')
API = 'https://api.github.com'
TOP_CONTRIBUTORS = 5
ACTIVITY_PAGES = 3  # commits in the last 90 days: at most 300 are read; more is reported as 300+

projects_url = 'https://raw.githubusercontent.com/OWASP/owasp.github.io/main/_data/projects.json'
response = requests.get(projects_url, timeout=60)
response.raise_for_status()
projects = response.json()
access_token = os.environ.get('ACCESS_TOKEN') or os.environ.get('GITHUB_TOKEN')
http = requests.Session()
http.headers['Accept'] = 'application/vnd.github+json'
if access_token:
    http.headers['Authorization'] = f'token {access_token}'

now = datetime.now(timezone.utc)
since_30 = now - timedelta(days=30)
since_90 = now - timedelta(days=90)


def get(path, **params):
    return http.get(f'{API}/{path}', params=params, timeout=60)


def last_page(resp):
    """The page number of rel="last" in a Link header (with per_page=1, the item count)."""
    match = re.search(r'[?&]page=(\d+)[^>]*>; rel="last"', resp.headers.get('Link', ''))
    return int(match.group(1)) if match else None


def count(path, **params):
    """Number of items in a list endpoint, from one per_page=1 request; None when it fails."""
    resp = get(path, per_page=1, **params)
    if resp.status_code != 200:
        return None
    return last_page(resp) or len(resp.json())


def human(login, kind):
    return kind != 'Bot' and not is_bot(login or '', login or '')


def top_contributors(repo_name):
    resp = get(f'repos/{repo_name}/contributors', per_page=30)
    if resp.status_code != 200 or not resp.content:  # 204: empty repository
        return None, []
    people = resp.json()
    total = len(people) if last_page(resp) is None else count(f'repos/{repo_name}/contributors')
    top = [{
        'login': p['login'],
        'avatar_url': p.get('avatar_url'),
        'html_url': p.get('html_url'),
        'contributions': p.get('contributions', 0),
    } for p in people if human(p.get('login'), p.get('type'))][:TOP_CONTRIBUTORS]
    return total, top


def activity(repo_name):
    """Commits and distinct human authors over the last 30 and 90 days, and the latest commit date."""
    commits, capped = [], False
    for page in range(1, ACTIVITY_PAGES + 1):
        resp = get(f'repos/{repo_name}/commits', since=since_90.isoformat(), per_page=100, page=page)
        if resp.status_code != 200:
            break
        batch = resp.json()
        commits += batch
        if len(batch) < 100:
            break
        capped = page == ACTIVITY_PAGES
    if commits:
        last_commit = commits[0]['commit']['committer']['date']
    else:  # nothing in 90 days: one more request for the latest commit
        resp = get(f'repos/{repo_name}/commits', per_page=1)
        last_commit = resp.json()[0]['commit']['committer']['date'] if resp.status_code == 200 and resp.json() else None
    stats = {'last_commit': last_commit, 'activity_capped': capped}
    for days, since in ((30, since_30), (90, since_90)):
        recent = [c for c in commits if c['commit']['committer']['date'] >= since.strftime('%Y-%m-%dT%H:%M:%SZ')]
        authors = set()
        for c in recent:
            user = c.get('author') or {}
            name = user.get('login') or c['commit']['author'].get('name') or ''
            email = c['commit']['author'].get('email') or ''
            if user.get('type') != 'Bot' and not is_bot(name, email):
                authors.add(name.lower())
        stats[f'commits_{days}d'] = len(recent)
        stats[f'contributors_{days}d'] = len(authors)
    return stats


repo_statuses = []
print('processing projects from json')

for project in projects:
    code_url = project.get('codeurl', '').split('\t')[0]

    if 'github.com' in code_url:
        print('code_url', code_url)
        repo_name = '/'.join(code_url.rstrip('/').split('/')[-2:])
        try:
            repo_response = get(f'repos/{repo_name}')
            repo_info = repo_response.json()
            ok = repo_response.status_code == 200
            entry = {
                'name': project['name'],
                'repo_name': repo_name,
                'url': project['url'],
                'created': project['created'],
                'updated': project['updated'],
                'build': project['build'],
                'codeurl': code_url,
                'title': project['title'],
                'level': project['level'],
                'type': project['type'],
                'region': project['region'],
                'pitch': project['pitch'],
                'meetup-group': project['meetup-group'],
                'github_status': repo_info.get('message', 'success'),
                'last_commit': None,
                'date_released': None,
                'release_version': None,
                'committers': None,
                'stars': None,
                'top_language': None,
                'license': None,
                'forks': None,
                'prs': None,
                'issues': None,
                'top_contributors': [],
            }
            if ok:
                releases = get(f'repos/{repo_name}/releases', per_page=1)
                release = releases.json()[0] if releases.status_code == 200 and releases.json() else {}
                committers, top = top_contributors(repo_name)
                prs = count(f'repos/{repo_name}/pulls', state='open')
                open_items = repo_info.get('open_issues_count')  # GitHub counts open PRs as issues
                entry.update(activity(repo_name))
                entry.update({
                    'date_released': release.get('published_at'),
                    'release_version': release.get('tag_name'),
                    'committers': committers,
                    'stars': repo_info.get('stargazers_count'),
                    'top_language': repo_info.get('language'),
                    'license': (repo_info.get('license') or {}).get('name'),
                    'forks': repo_info.get('forks_count'),
                    'prs': prs,
                    'issues': open_items - prs if open_items is not None and prs is not None else None,
                    'pushed_at': repo_info.get('pushed_at'),
                    'archived': repo_info.get('archived', False),
                    'top_contributors': top,
                })
            repo_statuses.append(entry)
        except Exception as e:
            print(f"Error fetching status for {code_url}: {e}")

print(f'writing {OUTPUT_FILE}')

os.makedirs(OUTPUT_DIR, exist_ok=True)
with open(OUTPUT_FILE, 'w') as outfile:
    json.dump(repo_statuses, outfile, indent=2)
