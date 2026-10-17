import json
import os
import re
import requests
from bs4 import BeautifulSoup

OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "public")
INPUT_FILE = os.path.join(OUTPUT_DIR, "www_project_repos.json")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "project_repos_links.json")

def check_url_exists(url):
    """Check if a URL returns a 404 status code."""
    try:
        response = requests.head(url, timeout=10, allow_redirects=True)
        return response.status_code != 404
    except requests.RequestException as e:
        # If we can't check the URL, assume it's valid to avoid false positives
        print(f"Warning: Could not validate URL {url}: {type(e).__name__}")
        return True

def extract_github_links(url, project_name):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    links = soup.find_all('a', href=True)
    
    github_links = set()
    for link in links:
        match = re.match(r'https://github\.com/[^/]+/[^/#]+', link['href'].lower())
        if match and project_name.lower() not in link['href'].lower():
            github_url = match.group(0)
            # Check if the URL returns 404 before adding
            if check_url_exists(github_url):
                github_links.add(github_url)
            else:
                print(f"Skipping 404 URL: {github_url}")
    
    return list(github_links)

with open(INPUT_FILE, 'r') as f:
    data = json.load(f)

project_links = []

for project in data:
    print("project name", project['name'])
    project_name = project['name']
    github_url = project['html_url'].replace('github.com/OWASP/', 'owasp.org/')

    repo_links = extract_github_links(github_url, project_name)
    if repo_links:  # Only append projects with GitHub links
        project_links.append({
            'project_name': project_name,
            'repo_links': repo_links
        })

os.makedirs(OUTPUT_DIR, exist_ok=True)
with open(OUTPUT_FILE, 'w') as f:
    json.dump(project_links, f, indent=2)
