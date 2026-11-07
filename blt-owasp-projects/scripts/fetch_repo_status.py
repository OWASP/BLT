"""repo_status.json: every OWASP project, with its GitHub repo's stats, top contributors and recent
activity. Run daily by scripts/refresh-kv.sh (about 7 GitHub requests per repository, so it needs a
token: GITHUB_TOKEN or ACCESS_TOKEN).

The project list is the owasp.org inventory (https://owasp.org/projects, its public API), cross-checked
with the OWASP organization's www-project-* repositories: an active www-project repo that no inventory
project points to is added with listed=false. owasp.github.io's older projects.json fills in the pitch,
region and project-page fields where a project is in both."""

import html
import json
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import requests

# Bots are left out of the contributor lists with the same rules as the BLT README wall.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'readme'))
from contributors import is_bot  # noqa: E402

OUTPUT_DIR = os.environ.get('OUTPUT_DIR', 'public')
OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'repo_status.json')
API = 'https://api.github.com'
INVENTORY_URL = 'https://owasp.org/api/public/projects/list?limit=2000'
PROJECTS_JSON_URL = 'https://raw.githubusercontent.com/OWASP/owasp.github.io/main/_data/projects.json'
TOP_CONTRIBUTORS = 5
ACTIVITY_PAGES = 3  # commits in the last 90 days: at most 300 are read; more is reported as 300+
WORKERS = 6
SKIP_WWW = {'www-project-template'}

access_token = os.environ.get('ACCESS_TOKEN') or os.environ.get('GITHUB_TOKEN')
local = threading.local()

now = datetime.now(timezone.utc)
since_30 = now - timedelta(days=30)
since_90 = now - timedelta(days=90)


def session():
    if not hasattr(local, 'http'):
        local.http = requests.Session()
        local.http.headers['Accept'] = 'application/vnd.github+json'
        if access_token:
            local.http.headers['Authorization'] = f'token {access_token}'
    return local.http


def get(path, **params):
    resp = session().get(f'{API}/{path}', params=params, timeout=60)
    # An organization that requires two-factor auth refuses a member's token that lacks it, even for
    # its public repositories; those few requests go out without the token instead.
    if resp.status_code == 403 and b'two-factor' in resp.content:
        resp = requests.get(f'{API}/{path}', params=params, timeout=60,
                            headers={'Accept': 'application/vnd.github+json'})
    return resp


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


def repo_of(url):
    """'owner/repo' from a github.com URL ('.../repo/subscription', '...repo"><img' and '.git' are
    trimmed); None for an organization URL or anything else."""
    m = re.match(r'https?://(?:www\.)?github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)', (url or '').strip())
    if not m or m.group(1).lower() in ('orgs', 'sponsors', 'topics'):
        return None
    return f'{m.group(1)}/{m.group(2).removesuffix(".git")}'


def norm_title(title):
    return re.sub(r'[^a-z0-9]', '', re.sub(r'^owasp\s+', '', (title or '').lower().strip()))


def text_of(fragment, limit=320):
    """Plain text from the inventory's HTML descriptions, cut at a word near `limit`."""
    text = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', fragment or ''))).strip()
    if len(text) > limit:
        text = text[:limit].rsplit(' ', 1)[0].rstrip('.,;:') + '…'
    return text


def www_repos():
    """{lower-case name: repo} for the OWASP organization's www-project-* repositories."""
    repos, page = {}, 1
    while True:
        resp = get('orgs/OWASP/repos', per_page=100, page=page, type='public')
        resp.raise_for_status()
        batch = resp.json()
        for r in batch:
            if r['name'].lower().startswith('www-project-') and r['name'].lower() not in SKIP_WWW:
                repos[r['name'].lower()] = r
        if len(batch) < 100:
            return repos
        page += 1


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


LANGUAGE_QUERY = """{ %s }"""
LANGUAGE_FIELDS = """r%d: repository(owner: %s, name: %s) {
  nameWithOwner languages(first: 8, orderBy: {field: SIZE, direction: DESC}) { totalSize edges { size node { name color } } } }"""


def languages(repos, batch=25):
    """{lower-case repo: [[language, colour, share], ...]} from GitHub's language breakdown, the
    colourful bar on every GitHub repository page; one GraphQL query per `batch` repositories."""
    out = {}
    if not access_token:
        return out
    for i in range(0, len(repos), batch):
        chunk = repos[i:i + batch]
        fields = ' '.join(LANGUAGE_FIELDS % (j, json.dumps(r.split('/')[0]), json.dumps(r.split('/', 1)[1]))
                          for j, r in enumerate(chunk))
        try:
            resp = session().post(f'{API}/graphql', json={'query': LANGUAGE_QUERY % fields}, timeout=90)
            data = resp.json().get('data') or {}
        except Exception as e:
            print(f'languages {chunk[0]}…: {e}')
            continue
        for node in data.values():
            if not node:
                continue  # a missing repository, or one whose organization refuses the token
            total = node['languages']['totalSize'] or 0
            out[node['nameWithOwner'].lower()] = [
                [e['node']['name'], e['node']['color'] or '#94a3b8', round(e['size'] / total, 4)]
                for e in node['languages']['edges'] if total and e['size'] / total >= 0.005]
    return out


def repo_stats(repo_name):
    """GitHub stats for one repository; github_status is 'success' or GitHub's error message."""
    stats = {'github_status': None, 'last_commit': None, 'date_released': None, 'release_version': None,
             'committers': None, 'stars': None, 'top_language': None, 'license': None, 'forks': None,
             'prs': None, 'issues': None, 'top_contributors': []}
    try:
        repo_response = get(f'repos/{repo_name}')
        repo_info = repo_response.json()
        stats['github_status'] = repo_info.get('message', 'success') if isinstance(repo_info, dict) else 'error'
        if repo_response.status_code != 200:
            return stats
        releases = get(f'repos/{repo_name}/releases', per_page=1)
        release = releases.json()[0] if releases.status_code == 200 and releases.json() else {}
        committers, top = top_contributors(repo_name)
        prs = count(f'repos/{repo_name}/pulls', state='open')
        open_items = repo_info.get('open_issues_count')  # GitHub counts open PRs as issues
        stats.update(activity(repo_name))
        stats.update({
            'repo_name': repo_info.get('full_name', repo_name),
            'date_released': release.get('published_at'),
            'release_version': release.get('tag_name'),
            'committers': committers,
            'stars': repo_info.get('stargazers_count'),
            'top_language': repo_info.get('language'),
            'license': (repo_info.get('license') or {}).get('name'),
            'forks': repo_info.get('forks_count'),
            'prs': prs,
            'issues': max(open_items - prs, 0) if open_items is not None and prs is not None else None,
            'pushed_at': repo_info.get('pushed_at'),
            'archived': repo_info.get('archived', False),
            'top_contributors': top,
        })
    except Exception as e:  # one bad repository never stops the run
        print(f'Error fetching status for {repo_name}: {e}')
        stats['github_status'] = f'error: {e}'
    return stats


def build_projects(inventory, old_projects, www):
    """One entry per inventory project, then one per active www-project repo none of them points to."""
    old_by_www = {p['url'].rstrip('/').rsplit('/', 1)[-1].lower(): p for p in old_projects}
    old_by_title = {}
    for p in old_projects:
        old_by_title.setdefault(norm_title(p.get('name')), p)
        old_by_title.setdefault(norm_title(p.get('title')), p)
    old_by_code = {repo_of(p.get('codeurl')).lower(): p for p in old_projects if repo_of(p.get('codeurl'))}

    www_by_norm = {norm_title(name.removeprefix('www-project-')): name for name in www}

    entries, used_www = [], set()
    for p in inventory:
        slug = p['slug']
        links = [p.get('github_url'), p.get('website_url'), p.get('documentation_url')]
        # 'audiovideo-communications-top-10' is www-project-audio-video-communications-top-10.
        www_name = (f'www-project-{slug}'.lower() if f'www-project-{slug}'.lower() in www
                    else www_by_norm.get(norm_title(slug)))
        for link in links:
            m = re.search(r'www-project-[A-Za-z0-9_.-]+', link or '')
            if not www_name and m and m.group(0).lower() in www:
                www_name = m.group(0).lower()
        github = repo_of(p.get('github_url'))
        old = (old_by_www.get(www_name or '') or old_by_title.get(norm_title(p.get('title')))
               or old_by_code.get((github or '').lower()))
        if not www_name and old:
            name = old['url'].rstrip('/').rsplit('/', 1)[-1].lower()
            www_name = name if name in www else None
        if www_name:
            used_www.add(www_name)
        old = old or {}
        code = github or repo_of(old.get('codeurl')) or (www[www_name]['full_name'] if www_name else None)
        image = p.get('image') or ''
        entries.append({
            'slug': slug,
            'name': p.get('title') or slug,
            'title': p.get('title') or slug,
            'url': f'https://owasp.org/projects/{slug}',
            'listed': True,
            'www_repo': www[www_name]['full_name'] if www_name else None,
            'level': p.get('project_type') or 'other',
            'type': p.get('category') if (p.get('category') or 'Other') != 'Other' else (old.get('type') or 'Other'),
            'pitch': text_of(p.get('description')) or old.get('pitch', ''),
            'image': f'https://owasp.org{image}' if image.startswith('/') else image,
            'website': p.get('website_url') or None,
            'created': (p.get('created_at') or '')[:10] or old.get('created'),
            'updated': (p.get('updated_at') or '')[:10] or old.get('updated'),
            'build': old.get('build'),
            'region': old.get('region'),
            'meetup-group': old.get('meetup-group'),
            'codeurl': f'https://github.com/{code}' if code else (p.get('github_url') or None),
            'repo_name': code,
        })

    for name, repo in sorted(www.items()):
        if name in used_www or repo.get('archived'):
            continue
        old = old_by_www.get(name, {})
        code = repo_of(old.get('codeurl')) or repo['full_name']
        slug = name.removeprefix('www-project-')
        entries.append({
            'slug': slug,
            'name': old.get('name') or slug.replace('-', ' ').title(),
            'title': old.get('title') or old.get('name') or slug.replace('-', ' ').title(),
            'url': old.get('url') or f'https://owasp.org/{repo["name"]}/',
            'listed': False,
            'www_repo': repo['full_name'],
            'level': {'4': 'flagship', '3.5': 'production', '3': 'lab', '2': 'incubator'}.get(str(old.get('level')), 'other'),
            'type': old.get('type') or 'Other',
            'pitch': old.get('pitch') or repo.get('description') or '',
            'image': '',
            'website': None,
            'created': old.get('created') or (repo.get('created_at') or '')[:10],
            'updated': old.get('updated') or (repo.get('pushed_at') or '')[:10],
            'build': old.get('build'),
            'region': old.get('region'),
            'meetup-group': old.get('meetup-group'),
            'codeurl': f'https://github.com/{code}',
            'repo_name': code,
        })
    return entries


def main():
    inventory = requests.get(INVENTORY_URL, timeout=60).json()['projects']
    old_projects = requests.get(PROJECTS_JSON_URL, timeout=60).json()
    www = www_repos()
    print(f'{len(inventory)} inventory projects, {len(old_projects)} in projects.json, {len(www)} www-project repos')
    entries = build_projects(inventory, old_projects, www)

    repos = sorted({e['repo_name'] for e in entries if e['repo_name']}, key=str.lower)
    print(f'{len(entries)} projects, {len(repos)} repositories')
    with ThreadPoolExecutor(WORKERS) as pool:
        stats = dict(zip(repos, pool.map(repo_stats, repos)))
    langs = languages(repos)
    for e in entries:
        if e['repo_name']:
            e.update(stats[e['repo_name']])
            e['languages'] = langs.get(e['repo_name'].lower(), [])
        else:
            e.update({'github_status': 'no repository', 'top_contributors': []})

    print(f'writing {OUTPUT_FILE}')
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, 'w') as outfile:
        json.dump(entries, outfile, indent=2)


if __name__ == '__main__':
    main()
