"""open_issues.json and open_prs.json: every open issue and pull request in the repositories of
repo_status.json (run fetch_repo_status.py first), for the sortable tables on open.html; and
open_summary.json, each repository's counts of the quick views (good first issues, help wanted,
pull requests waiting for review...) for the cards and the home page's "Contribute" strip.

One GitHub GraphQL query per 100 items and repository, so there is no 1,000-result cap like the
search API's. Needs a token: GITHUB_TOKEN or ACCESS_TOKEN."""

import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import requests

OUTPUT_DIR = os.environ.get('OUTPUT_DIR', 'public')
STATUS_FILE = os.path.join(OUTPUT_DIR, 'repo_status.json')
GRAPHQL = 'https://api.github.com/graphql'
WORKERS = 4
MAX_PAGES = 30  # 3,000 of each per repository at most

access_token = os.environ.get('ACCESS_TOKEN') or os.environ.get('GITHUB_TOKEN')
local = threading.local()

COMMON = """number title url createdAt updatedAt
  author { __typename login }
  authorAssociation
  labels(first: 10) { nodes { name color } }
  assignees(first: 5) { nodes { login } }
  comments { totalCount }"""

QUERIES = {
    'issues': """query($owner: String!, $name: String!, $after: String) {
  repository(owner: $owner, name: $name) {
    items: issues(states: OPEN, first: 100, after: $after, orderBy: {field: UPDATED_AT, direction: DESC}) {
      pageInfo { hasNextPage endCursor }
      nodes { %s }
    }
  }
}""" % COMMON,
    'prs': """query($owner: String!, $name: String!, $after: String) {
  repository(owner: $owner, name: $name) {
    items: pullRequests(states: OPEN, first: 100, after: $after, orderBy: {field: UPDATED_AT, direction: DESC}) {
      pageInfo { hasNextPage endCursor }
      nodes { %s isDraft reviewDecision additions deletions changedFiles }
    }
  }
}""" % COMMON,
}


# The quick views on open.html (open.js uses the same rules).
GOOD_FIRST = re.compile(r'good[\s_-]?first|first[\s_-]?timers?|beginner|\beasy\b|starter|newcomer|low[\s_-]?hanging', re.I)
HELP_WANTED = re.compile(r'help[\s_-]?wanted|contributions?[\s_-]?welcome|up[\s_-]?for[\s_-]?grabs', re.I)
QUICK_LINES = 50
# No earlier commit to the repository. On open pull requests GitHub's GraphQL reports most such
# authors as NONE rather than FIRST_TIME_CONTRIBUTOR.
FIRST_TIME = {'FIRST_TIME_CONTRIBUTOR', 'FIRST_TIMER', 'NONE'}


def labelled(row, pattern):
    return any(pattern.search(name) for name, _ in row['labels'])


def needs_review(row):
    return not row.get('draft') and row.get('review') not in ('APPROVED', 'CHANGES_REQUESTED')


def summary(issues, prs):
    """[{repo, counts...}] for every repository with open work; bots' items left out."""
    out = {}
    blank = {'issues': 0, 'prs': 0, 'good_first': 0, 'help_wanted': 0, 'needs_review': 0, 'quick': 0, 'first_time': 0}
    for r in issues:
        if r['bot']:
            continue
        s = out.setdefault(r['repo'], {'repo': r['repo'], **blank})
        s['issues'] += 1
        s['good_first'] += labelled(r, GOOD_FIRST)
        s['help_wanted'] += labelled(r, HELP_WANTED)
    for r in prs:
        if r['bot']:
            continue
        s = out.setdefault(r['repo'], {'repo': r['repo'], **blank})
        s['prs'] += 1
        if needs_review(r):
            s['needs_review'] += 1
            s['quick'] += 1 <= r['additions'] + r['deletions'] <= QUICK_LINES
            s['first_time'] += r['role'] in FIRST_TIME
    return sorted(out.values(), key=lambda s: s['repo'].lower())


def session():
    if not hasattr(local, 'http'):
        local.http = requests.Session()
        local.http.headers['Authorization'] = f'bearer {access_token}'
    return local.http


def query(kind, owner, name, after, tries=4):
    """One page; GitHub's GraphQL answers big pull request pages with an occasional 502 or timeout,
    so those are retried."""
    for attempt in range(tries):
        try:
            resp = session().post(GRAPHQL, json={'query': QUERIES[kind], 'variables': {
                'owner': owner, 'name': name, 'after': after}}, timeout=90)
            if resp.status_code < 500:
                return resp.json()
        except (requests.RequestException, ValueError):
            pass
        time.sleep(2 * (attempt + 1))
    return None


def fetch(repo, kind):
    """All open items of one kind in one repository; [] when the repository can't be read."""
    owner, name = repo.split('/', 1)
    items, after = [], None
    for _ in range(MAX_PAGES):
        data = query(kind, owner, name, after)
        if data is None:
            print(f'{repo} {kind}: GitHub kept failing; keeping the {len(items)} read so far')
            break
        conn = ((data.get('data') or {}).get('repository') or {}).get('items')
        if not conn:
            print(f'{repo} {kind}: {data.get("errors") or resp.status_code}')
            break
        items += conn['nodes']
        if not conn['pageInfo']['hasNextPage']:
            break
        after = conn['pageInfo']['endCursor']
    return items


def row(node, repo, projects, kind, meta=None):
    author = node.get('author') or {}
    out = {
        'repo': repo,
        'projects': projects,
        'lang': (meta or {}).get('lang') or '',
        'level': (meta or {}).get('level') or '',
        'number': node['number'],
        'title': node['title'],
        'url': node['url'],
        'author': author.get('login') or 'ghost',
        'bot': author.get('__typename') == 'Bot' or (author.get('login') or '').endswith('[bot]'),
        # OWNER, MEMBER, COLLABORATOR, CONTRIBUTOR, FIRST_TIME_CONTRIBUTOR, FIRST_TIMER or NONE.
        'role': node.get('authorAssociation') or 'NONE',
        'labels': [[lbl['name'], lbl['color']] for lbl in node['labels']['nodes']],
        'assignees': [a['login'] for a in node['assignees']['nodes']],
        'comments': node['comments']['totalCount'],
        'created_at': node['createdAt'],
        'updated_at': node['updatedAt'],
    }
    if kind == 'prs':
        out.update({
            'draft': node['isDraft'],
            'review': node.get('reviewDecision'),
            'additions': node['additions'],
            'deletions': node['deletions'],
            'files': node['changedFiles'],
        })
    return out


def main():
    if not access_token:
        sys.exit('fetch_open_work.py needs GITHUB_TOKEN or ACCESS_TOKEN (GraphQL has no anonymous access)')
    with open(STATUS_FILE) as f:
        status = json.load(f)
    projects = {}  # repo -> [[slug, title], ...]
    meta = {}  # repo -> primary language and the best level of its projects
    order = ['flagship', 'production', 'lab', 'incubator', 'other']
    for p in status:
        if p.get('github_status') == 'success' and p.get('repo_name'):
            projects.setdefault(p['repo_name'], []).append([p.get('slug') or p['name'], p.get('title') or p['name']])
            level = str(p.get('level') or 'other').lower()
            level = level if level in order else 'other'
            m = meta.setdefault(p['repo_name'], {'lang': p.get('top_language') or '', 'level': level})
            if order.index(level) < order.index(m['level']):
                m['level'] = level
    repos = sorted(projects, key=str.lower)
    print(f'{len(repos)} repositories')

    found_rows = {}
    for kind in ('issues', 'prs'):
        with ThreadPoolExecutor(WORKERS) as pool:
            found = pool.map(lambda r: (r, fetch(r, kind)), repos)
            rows = [row(n, r, projects[r], kind, meta[r]) for r, nodes in found for n in nodes]
        rows.sort(key=lambda x: x['updated_at'], reverse=True)
        found_rows[kind] = rows
        path = os.path.join(OUTPUT_DIR, f'open_{kind}.json')
        with open(path, 'w') as f:
            json.dump(rows, f, separators=(',', ':'))
        print(f'wrote {len(rows)} to {path}')
    path = os.path.join(OUTPUT_DIR, 'open_summary.json')
    with open(path, 'w') as f:
        json.dump(summary(found_rows['issues'], found_rows['prs']), f, separators=(',', ':'))
    print(f'wrote {path}')


if __name__ == '__main__':
    main()
