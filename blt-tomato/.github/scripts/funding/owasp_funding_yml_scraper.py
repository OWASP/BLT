import json
import requests
import yaml

GITHUB_API_URL = "https://api.github.com"
ORG_NAME = "OWASP"
ADDITIONAL_PROJECTS = [
    {"name": "ASVS", "repo_url": "https://github.com/OWASP/ASVS"},
    {"name": "BLT", "repo_url": "https://github.com/OWASP-BLT/BLT"},
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
    url = f"{GITHUB_API_URL}/orgs/{ORG_NAME}/repos"
    repos = []
    while url:
        response = requests.get(url)
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
output_file = "project_repos_links.json"
with open(output_file, "w") as f:
    json.dump(project_links, f, indent=2)

print(f"Output written to '{output_file}'")

# Generate the index.html file
html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BLT Tomato - OWASP Projects Seeking Funding</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f4f4f4;
            color: #333;
        }
        header {
            background-color: #d9534f;
            color: white;
            padding: 10px 0;
            text-align: center;
        }
        header img {
            vertical-align: middle;
            margin-right: 10px;
        }
        header h1 {
            display: inline;
            font-size: 24px;
            vertical-align: middle;
        }
        main {
            padding: 20px;
        }
        ul {
            list-style-type: none;
            padding: 0;
        }
        li {
            background-color: white;
            margin: 10px 0;
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 0 5px rgba(0, 0, 0, 0.1);
        }
        .heart-icon {
            color: red;
            margin-left: 10px;
            text-decoration: none;
        }
        .donate-button {
            display: inline-block;
            padding: 5px 10px;
            background-color: #d9534f;
            color: white;
            border-radius: 5px;
            text-decoration: none;
        }
        footer {
            text-align: center;
            padding: 20px;
            background-color: #d9534f;
            color: white;
        }
        footer a {
            color: white;
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <header>
        <img src="https://img.icons8.com/emoji/48/000000/tomato-emoji.png" alt="Tomato" width="40" height="40">
        <h1>BLT Tomato - this is an OWASP BLT project created to help other OWASP projects.</h1>
    </header>
    <main>
        <p>The following OWASP projects are seeking funding and have a funding.yml file:</p>
        <ul>
"""

for index, project in enumerate(
    sorted(project_links, key=lambda p: p["project_name"]), start=1
):
    funding_links_html = ""
    funding_details = project["funding_details"].split(", ")
    for link in funding_details:
        if "https://owasp.org/donate/" in link:
            funding_links_html += f'<a href="{link}" class="donate-button">Donate</a> '
        else:
            funding_links_html += f'<a href="{link}" class="heart-icon">&#10084;</a> '
    html_content += f'<li>{index}. <a href="{project["repo_url"]}">{project["project_name"]}</a> {funding_links_html}<span>{project["funding_details"]}</span></li>\n'

html_content += """
        </ul>
    </main>
    <footer>
        <p><a href="https://github.com/OWASP-BLT/BLT-Tomato">View this script on GitHub</a></p>
    </footer>
</body>
</html>
"""

with open("index.html", "w") as f:
    f.write(html_content)

print("index.html file has been created.")