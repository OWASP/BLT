import os
import requests
import csv
import re
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import yaml   

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

ORGS = ["OWASP"]                      
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

headers = {
    "Accept": "application/vnd.github.v3.raw",
    "Authorization": f"token {GITHUB_TOKEN}" if GITHUB_TOKEN else None
}

CACHE_DIR = Path(".cache")
CACHE_TTL_HOURS = 24

OUTPUT_CSV = DATA_DIR / "metadata.csv"
SUMMARY_MD = DATA_DIR / "metadata_summary.md"
MATRIX_CSV = DATA_DIR / "metadata_matrix.csv"
MATRIX_JSON = DATA_DIR / "metadata_matrix.json"
METADATA_JSON = DATA_DIR / "metadata.json"

def log(msg): 
    print(f"[+] {msg}")

def warn(msg): 
    print(f"[!] {msg}")

def cache_path(owner, repo):
    return CACHE_DIR / f"{owner}__{repo}.json"

def save_cache(owner, repo, content):
    CACHE_DIR.mkdir(exist_ok=True)
    with open(cache_path(owner, repo), "w") as f:
        json.dump({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "content": content
        }, f)

def load_cache(owner, repo):
    path = cache_path(owner, repo)
    if not path.exists():
        return None

    data = json.load(open(path))
    ts = datetime.fromisoformat(data["timestamp"])
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) - ts > timedelta(hours=CACHE_TTL_HOURS):
        return None

    return data["content"]

def fetch_repos_from_org(org):
    repos = []
    page = 1

    while True:
        url = f"https://api.github.com/orgs/{org}/repos?per_page=100&page={page}"
        r = requests.get(url, headers=headers)

        if r.status_code != 200:
            warn(f"Failed to fetch repos from org {org}")
            break

        batch = r.json()
        if not batch:
            break

        for repo in batch:
            repos.append({"owner": org, "repo": repo["name"]})

        page += 1

    log(f"Fetched {len(repos)} repos from {org}")
    return repos

def fetch_file(owner, repo, filename):
    """Fetch a file from a repository, trying main and master branches."""
    for branch in ["main", "master"]:
        url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{filename}"
        r = requests.get(url)
        if r.status_code == 200:
            return r.text
    return None


def fetch_index_md(owner, repo):
    return fetch_file(owner, repo, "index.md")


def fetch_sidebar_files(owner, repo):
    """Fetch sidebar files (info.md, leaders.md) from a repository."""
    sidebar_data = {}
    
    # Fetch info.md
    info_content = fetch_file(owner, repo, "info.md")
    if info_content:
        sidebar_data["info_md"] = info_content
    
    # Fetch leaders.md
    leaders_content = fetch_file(owner, repo, "leaders.md")
    if leaders_content:
        sidebar_data["leaders_md"] = leaders_content
    
    return sidebar_data


def parse_sidebar_content(content):
    """Parse sidebar markdown content to extract structured data."""
    data = {}
    if not content:
        return data
    
    # Check if this is primarily a leaders file (contains "### Leaders" header)
    is_leaders_file = "### Leaders" in content or "## Leaders" in content
    
    # Extract leaders from leaders.md format: "* [Name](mailto:email)" or "* Name"
    # Only extract if this looks like a leaders section
    if is_leaders_file:
        leader_pattern = re.compile(r'\*\s*\[([^\]]+)\]\(mailto:([^)]+)\)', re.IGNORECASE)
        leader_simple_pattern = re.compile(r'^\s*\*\s*\[([^\]]+)\]\([^)]*\)\s*$', re.MULTILINE)
        
        leaders = []
        for match in leader_pattern.finditer(content):
            leaders.append({"name": match.group(1).strip(), "email": match.group(2).strip()})
        
        # Also capture leaders without mailto links but only if they don't have email
        for match in leader_simple_pattern.finditer(content):
            name = match.group(1).strip()
            # Avoid duplicates and filter out non-leader entries
            if not any(l.get("name") == name for l in leaders):
                # Skip entries that look like links to resources
                lower_name = name.lower()
                if not any(x in lower_name for x in ['download', 'repo', 'github', 'http', 'license']):
                    leaders.append({"name": name})
        
        if leaders:
            data["leaders_list"] = leaders
    
    # Extract social links from info.md
    social_patterns = {
        "twitter": re.compile(r'\[(?:Twitter|X)\]\((https?://(?:twitter\.com|x\.com)/[^)]+)\)', re.IGNORECASE),
        "facebook": re.compile(r'\[Facebook\]\((https?://(?:www\.)?facebook\.com/[^)]+)\)', re.IGNORECASE),
        "linkedin": re.compile(r'\[Linkedin\]\((https?://(?:www\.)?linkedin\.com/[^)]+)\)', re.IGNORECASE),
        "youtube": re.compile(r'\[YouTube\]\((https?://(?:www\.)?youtube\.com/[^)]+)\)', re.IGNORECASE),
        "meetup": re.compile(r'\[Meetup(?:\.com)?\]\((https?://(?:www\.)?meetup\.com/[^)]+)\)', re.IGNORECASE),
    }
    
    for name, pattern in social_patterns.items():
        match = pattern.search(content)
        if match:
            data[f"social_{name}"] = match.group(1)
    
    # Extract project classification info
    if "Flagship Project" in content:
        data["project_classification"] = "Flagship"
    elif "Lab Project" in content or "Lab project" in content:
        data["project_classification"] = "Lab"
    elif "Incubator Project" in content or "Incubator project" in content:
        data["project_classification"] = "Incubator"
    elif "Production Project" in content:
        data["project_classification"] = "Production"
    
    # Extract project type from info.md
    type_patterns = {
        "Tool": re.compile(r'<i class="fas fa-tools"', re.IGNORECASE),
        "Documentation": re.compile(r'<i class="fas fa-book"', re.IGNORECASE),
        "Code": re.compile(r'<i class="fas fa-code"', re.IGNORECASE),
    }
    
    for proj_type, pattern in type_patterns.items():
        if pattern.search(content):
            data["sidebar_type"] = proj_type
            break
    
    # Extract audience info
    audiences = []
    if re.search(r'\bBreaker\b', content):
        audiences.append("Breaker")
    if re.search(r'\bBuilder\b', content):
        audiences.append("Builder")
    if re.search(r'\bDefender\b', content):
        audiences.append("Defender")
    if audiences:
        data["audience"] = audiences
    
    # Extract download links
    download_pattern = re.compile(r'\[Download[^\]]*\]\(([^)]+)\)', re.IGNORECASE)
    downloads = download_pattern.findall(content)
    if downloads:
        data["download_links"] = downloads
    
    # Extract repository links from code repository section
    repo_section_pattern = re.compile(r'###?\s*Code\s*Repositor(?:y|ies).*?(?=###?|\Z)', re.IGNORECASE | re.DOTALL)
    repo_section = repo_section_pattern.search(content)
    if repo_section:
        repo_pattern = re.compile(r'\[([^\]]+)\]\((https?://github\.com/[^)]+)\)', re.IGNORECASE)
        repos = repo_pattern.findall(repo_section.group(0))
        if repos:
            data["code_repositories"] = [url for name, url in repos]
    
    # Extract licensing info
    license_patterns = [
        (re.compile(r'Apache\s*2(?:\s*License)?', re.IGNORECASE), "Apache 2.0"),
        (re.compile(r'MIT\s*License', re.IGNORECASE), "MIT"),
        (re.compile(r'GPL', re.IGNORECASE), "GPL"),
        (re.compile(r'Creative Commons', re.IGNORECASE), "Creative Commons"),
        (re.compile(r'CC BY', re.IGNORECASE), "CC BY"),
    ]
    
    for pattern, license_name in license_patterns:
        if pattern.search(content):
            data["license"] = license_name
            break
    
    return data

def extract_front_matter(content):
    m = re.search(r"---(.*?)---", content, re.DOTALL)
    if not m:
        return {}
    try:
        data = yaml.safe_load(m.group(1))
        return data if isinstance(data, dict) else {}
    except:
        return {}

def scan_repo(entry):
    owner = entry["owner"]
    repo = entry["repo"]

    cached = load_cache(owner, repo)
    if cached:
        return cached

    content = fetch_index_md(owner, repo)
    metadata = extract_front_matter(content) if content else {}
    
    # Fetch and parse sidebar files
    sidebar_files = fetch_sidebar_files(owner, repo)
    sidebar_metadata = {}
    
    source_files = []
    if content:
        source_files.append("index.md")
    
    # Parse info.md
    if "info_md" in sidebar_files:
        source_files.append("info.md")
        info_data = parse_sidebar_content(sidebar_files["info_md"])
        sidebar_metadata.update(info_data)
    
    # Parse leaders.md
    if "leaders_md" in sidebar_files:
        source_files.append("leaders.md")
        leaders_data = parse_sidebar_content(sidebar_files["leaders_md"])
        sidebar_metadata.update(leaders_data)

    result = {
        "repo": f"{owner}/{repo}",
        "source_file": ", ".join(source_files) if source_files else None,
        "metadata": metadata,
        "sidebar_metadata": sidebar_metadata
    }

    save_cache(owner, repo, result)
    return result

def main():
    repos = []
    for org in ORGS:
        repos.extend(fetch_repos_from_org(org))

    log(f"Total repos to scan: {len(repos)}")

    all_metadata = []
    all_keys = defaultdict(int)
    sidebar_keys = defaultdict(int)

    with ThreadPoolExecutor(max_workers=20) as ex:
        futures = {ex.submit(scan_repo, r): r for r in repos}

        for fut in as_completed(futures):
            res = fut.result()
            meta = res.get("metadata", {})
            sidebar_meta = res.get("sidebar_metadata", {})
            
            row = {
                "repo": res["repo"],
                "source_file": res["source_file"]
            }
            row.update(meta)
            
            # Add sidebar metadata with "sidebar_" prefix to distinguish
            for key, value in sidebar_meta.items():
                # Handle list values for CSV compatibility
                if isinstance(value, list):
                    if all(isinstance(item, dict) for item in value):
                        # For leader lists, extract just names
                        if key == "leaders_list":
                            row[key] = ", ".join(item.get("name", "") for item in value)
                        else:
                            row[key] = json.dumps(value)
                    else:
                        row[key] = ", ".join(str(v) for v in value)
                else:
                    row[key] = value
            
            if meta:
                for k in meta:
                    all_keys[k] += 1
            
            if sidebar_meta:
                for k in sidebar_meta:
                    sidebar_keys[k] += 1

            all_metadata.append(row)

    if all_metadata:
        keys = sorted({k for item in all_metadata for k in item.keys()})
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(all_metadata)

    with open(METADATA_JSON, "w", encoding="utf-8") as f:
        json.dump(all_metadata, f, indent=2)

    log(f"Generated full metadata JSON → {METADATA_JSON}")

    with open(SUMMARY_MD, "w") as f:
        f.write("# Metadata Summary\n\n")
        f.write("## Front Matter Fields (index.md)\n\n")
        f.write("| Field | Count |\n|---|---|\n")
        for k, c in sorted(all_keys.items()):
            f.write(f"| {k} | {c} |\n")
        
        f.write("\n## Sidebar Fields (info.md, leaders.md)\n\n")
        f.write("| Field | Count |\n|---|---|\n")
        for k, c in sorted(sidebar_keys.items()):
            f.write(f"| {k} | {c} |\n")

    if all_metadata:
        all_fields = sorted({k for item in all_metadata for k in item.keys() if k not in ["repo", "source_file"]})
        matrix_rows = []

        for item in all_metadata:
            row = {"repo": item["repo"]}
            for f in all_fields:
                row[f] = "✔" if f in item and item[f] not in [None, "", []] else ""
            matrix_rows.append(row)

        with open(MATRIX_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["repo"] + all_fields)
            writer.writeheader()
            writer.writerows(matrix_rows)

        with open(MATRIX_JSON, "w", encoding="utf-8") as f:
            json.dump(matrix_rows, f, indent=2)

    log(f"Generated matrix CSV → {MATRIX_CSV}")
    log(f"Generated matrix JSON → {MATRIX_JSON}")
    print("\nDone!")

if __name__ == "__main__":
    main()
