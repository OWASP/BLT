import os
import re
import json
import requests

GITHUB_API_URL = "https://api.github.com"
ORG_NAME = "owasp"
REPO_PREFIX = "www-project"
OUTPUT_FILE = "www_project_repos.json"
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "public")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, OUTPUT_FILE)
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")
MAX_SNIPPET_LENGTH = 500

def get_repos(headers):
    all_repos = []
    page = 1
    max_pages = 100  # Safety limit: 100 pages * 100 per page = 10,000 repos max

    # Fetch all pages until API returns empty response or safety limit reached
    while page <= max_pages:
        url = f"{GITHUB_API_URL}/orgs/{ORG_NAME}/repos?per_page=100&page={page}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        repos = response.json()
        if not repos:  # No more repositories to fetch
            break

        all_repos.extend(repos)
        page += 1

    return all_repos

def filter_and_format_repos(repos):
    filtered_repos = []

    for repo in repos:
        if repo["name"].startswith(REPO_PREFIX):
            filtered_repos.append(repo)

    return filtered_repos

def get_project_snippet(repo_name, headers):
    """Fetch index.md from the project repo and extract a short description snippet."""
    for branch in ("main", "master"):
        url = f"https://raw.githubusercontent.com/{ORG_NAME}/{repo_name}/{branch}/index.md"
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                continue
            content = response.text

            # Try to extract the 'pitch' field from YAML front matter
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    for line in parts[1].splitlines():
                        if line.lower().startswith("pitch:"):
                            pitch = line[line.index(":") + 1:].strip()
                            if pitch:
                                return pitch
                    body = parts[2].strip()
                else:
                    body = content.strip()
            else:
                body = content.strip()

            # Fall back to extracting the first two sentences from the body text
            lines = [line.strip() for line in body.splitlines() if line.strip() and not line.startswith("#")]
            text = " ".join(lines)
            sentences = re.split(r"(?<=[.!?])\s+", text)
            snippet = " ".join(sentences[:2]).strip()
            if snippet:
                return snippet[:MAX_SNIPPET_LENGTH]
        except (requests.RequestException, ValueError):
            pass
    return ""

def send_slack_alert(new_repos, headers):
    if not SLACK_WEBHOOK_URL:
        print("No SLACK_WEBHOOK_URL set, skipping Slack notification")
        return

    message = "New OWASP project repositories detected:\n"
    for repo in new_repos:
        repo_url = f"https://github.com/{repo['full_name']}"
        # Embed the link using Slack's <url|text> format so the URL appears only once
        line = f"- <{repo_url}|{repo['full_name']}>"
        snippet = get_project_snippet(repo["name"], headers)
        if snippet:
            line += f": {snippet}"
        message += line + "\n"

    payload = {"text": message}
    response = requests.post(SLACK_WEBHOOK_URL, json=payload)
    response.raise_for_status()

def main():
    print('parsing repos')
    headers = {"Authorization": f"token {os.environ['GITHUB_TOKEN']}"}
    repos = get_repos(headers)
    www_project_repos = filter_and_format_repos(repos)

    try:
        with open(OUTPUT_PATH, "r") as f:
            old_repos = json.load(f)
    except FileNotFoundError:
        old_repos = []

    new_repos = [repo for repo in www_project_repos if repo['id'] not in [old_repo['id'] for old_repo in old_repos]]
    if new_repos:
        send_slack_alert(new_repos, headers)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(www_project_repos, f, indent=2)

if __name__ == "__main__":
    main()
