import os
import json
import requests
from datetime import datetime, timedelta
import base64

GITHUB_API_URL = "https://api.github.com"
ORG_NAME = "owasp"
REPO_PREFIX = "www-project"
OUTPUT_FILE = "www_project_repos.json"
SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL_SWEEP"]
SEARCH_STRING = "This is an example of a Project or Chapter Page"

headers = {"Authorization": f"token {os.environ['GITHUB_TOKEN']}"}

def filter_and_format_repos(repos):
    filtered_repos = []

    for repo in repos:
        if repo["name"].startswith(REPO_PREFIX) and not repo.get("archived", False):
            filtered_repos.append(repo)

    return filtered_repos
    
def get_repos():
    all_repos = []
    page = 1
    max_pages = 100  # Safety limit: 100 pages * 100 per page = 10,000 repos max

    headers = {"Authorization": f"token {os.environ['GITHUB_TOKEN']}"}

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
    
def get_index_md_content(repo_full_name):
    url = f"{GITHUB_API_URL}/repos/{repo_full_name}/contents/index.md"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        file_content = response.json()["content"]
        return base64.b64decode(file_content).decode('utf-8') # Updated line here
    return None

def check_last_updated_date(repo_full_name):
    url = f"{GITHUB_API_URL}/repos/{repo_full_name}/commits?path=index.md&per_page=1"
    response = requests.get(url, headers=headers)
    if response.status_code == 200 and response.json():
        last_updated_date = response.json()[0]['commit']['committer']['date']
        return datetime.strptime(last_updated_date, "%Y-%m-%dT%H:%M:%SZ")
    return None

def send_slack_alert(repo_full_name):
    repo_url = f"https://github.com/{repo_full_name}"
    message_text = f"Repo *<{repo_url}|{repo_full_name}>* has not been updated in over a month. Check index.md."
    
    payload = {
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message_text
                }
            }
        ]
    }
    
    response = requests.post(SLACK_WEBHOOK_URL, json=payload)
    response.raise_for_status()

def main():
    print('Parsing repos...')
    repos = get_repos()
    www_project_repos = filter_and_format_repos(repos)
    
    for repo in www_project_repos:
        repo_full_name = repo['full_name']
        index_md_content = get_index_md_content(repo_full_name)
        
        if index_md_content and SEARCH_STRING in index_md_content:  # Changed the condition here
            last_updated_date = check_last_updated_date(repo_full_name)
            if last_updated_date and datetime.utcnow() - last_updated_date > timedelta(days=30):
                send_slack_alert(repo_full_name)
            
if __name__ == "__main__":
    main()