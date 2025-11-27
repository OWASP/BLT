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

def fetch_index_md(owner, repo):
    for branch in ["main", "master"]:
        url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/index.md"
        r = requests.get(url)
        if r.status_code == 200:
            return r.text
    return None

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

    result = {
        "repo": f"{owner}/{repo}",
        "source_file": "index.md" if content else None,
        "metadata": metadata
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

    with ThreadPoolExecutor(max_workers=20) as ex:
        futures = {ex.submit(scan_repo, r): r for r in repos}

        for fut in as_completed(futures):
            res = fut.result()
            meta = res.get("metadata", {})
            
            row = {
                "repo": res["repo"],
                "source_file": res["source_file"]
            }
            row.update(meta)
            if meta:
                for k in meta:
                    all_keys[k] += 1

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
        f.write("| Field | Count |\n|---|---|\n")
        for k, c in sorted(all_keys.items()):
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
