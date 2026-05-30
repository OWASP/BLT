import requests
import json
import os

projects_url = 'https://raw.githubusercontent.com/OWASP/owasp.github.io/main/_data/projects.json'
response = requests.get(projects_url)
projects = response.json()
access_token = os.environ.get('ACCESS_TOKEN')
headers = {'Authorization': f'token {access_token}'}

repo_statuses = []
print('processing projects from json')

for project in projects:
    code_url = project.get('codeurl', '').split('\t')[0]

    if 'github.com' in code_url:
        print('code_url', code_url)
        repo_name = '/'.join(code_url.split('/')[-2:])
        try:
            slug = repo_name.replace('/', '%2F')
            repo_api_url = f'https://api.github.com/repos/{repo_name}'
            repo_response = requests.get(repo_api_url, headers=headers)
            repo_info = repo_response.json()

            # Additional API requests
            commits_url = f'https://api.github.com/repos/{repo_name}/commits'
            releases_url = f'https://api.github.com/repos/{repo_name}/releases'
            contributors_url = f'https://api.github.com/repos/{repo_name}/contributors'
            forks_url = f'https://api.github.com/repos/{repo_name}/forks'
            prs_url = f'https://api.github.com/repos/{repo_name}/pulls'
            issues_url = f'https://api.github.com/repos/{repo_name}/issues'

            commits_response = requests.get(commits_url, headers=headers)
            releases_response = requests.get(releases_url, headers=headers)
            contributors_response = requests.get(contributors_url, headers=headers)
            forks_response = requests.get(forks_url, headers=headers)
            prs_response = requests.get(prs_url, headers=headers)
            issues_response = requests.get(issues_url, headers=headers)

            last_commit = commits_response.json()[0]['commit']['committer']['date'] if commits_response.status_code == 200 else None
            date_released = releases_response.json()[0]['published_at'] if releases_response.status_code == 200 and releases_response.json() else None
            release_version = releases_response.json()[0]['tag_name'] if releases_response.status_code == 200 and releases_response.json() else None
            committers = len(contributors_response.json()) if contributors_response.status_code == 200 else None
            stars = repo_info.get('stargazers_count')
            top_language = repo_info.get('language')
            license = repo_info.get('license', {}).get('name')
            forks = repo_info.get('forks_count')
            prs = len(prs_response.json()) if prs_response.status_code == 200 else None
            issues = len(issues_response.json()) if issues_response.status_code == 200 else None

            repo_statuses.append({
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
                'last_commit': last_commit,
                'date_released': date_released,
                'release_version': release_version,
                'committers': committers,
                'stars': stars,
                'top_language': top_language,
                'license': license,
                'forks': forks,
                'prs': prs,
                'issues': issues
            })
        except Exception as e:
            print(f"Error fetching status for {code_url}: {e}")

print('writing repo_status.json')

with open('repo_status.json', 'w') as outfile:
    json.dump(repo_statuses, outfile, indent=2)