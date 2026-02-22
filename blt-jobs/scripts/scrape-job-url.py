#!/usr/bin/env python3
"""
Fetch a job URL and write jobs/<slug>.md with structured frontmatter.
Strategy (in order):
  1. Greenhouse public JSON API  (boards.greenhouse.io / job-boards.greenhouse.io)
  2. Lever public JSON API       (jobs.lever.co)
  3. JSON-LD JobPosting schema   (Workable, Indeed, LinkedIn, most modern ATS)
  4. Static HTML heuristics      (BeautifulSoup title + body extraction)
  5. Jina Reader API fallback    (r.jina.ai — handles JS-rendered pages)
"""

import json
import re
import sys
from datetime import datetime
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("pip install requests beautifulsoup4", file=sys.stderr)
    sys.exit(1)

JOBS_DIR = Path(__file__).resolve().parent.parent / "jobs"
HEADERS = {
    "User-Agent": "OWASP-BLT-Jobs-Bot/1.0 (https://github.com/OWASP-BLT/BLT-Jobs)"
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def slugify(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[-\s]+", "-", s)
    return s.strip("-") or "job"


def html_to_text(html: str, max_chars: int = 15000) -> str:
    """Strip HTML tags and return plain text."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator="\n", strip=True)[:max_chars]


def soup_main_text(soup: BeautifulSoup, max_chars: int = 15000) -> str:
    """Pull the most content-rich section from a parsed page."""
    candidates = [
        ".job-description", "#job-description",
        "[class*='job-desc']", "[id*='job-desc']",
        ".posting-content", "#posting-content",
        ".content-intro", ".jobsearch-jobDescriptionText",
        "[role='main']", "main", "article",
        ".content", "#content",
    ]
    for sel in candidates:
        el = soup.select_one(sel)
        if el:
            text = el.get_text(separator="\n", strip=True)
            if len(text) > 300:
                return text[:max_chars]
    # Last resort: strip nav/header/footer noise then dump body
    for tag in soup(["nav", "header", "footer", "script", "style", "noscript"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)[:max_chars]


def org_from_host(url: str) -> str:
    host = urlparse(url).netloc or ""
    return host.replace("www.", "").split(".")[0].replace("-", " ").title()


# ---------------------------------------------------------------------------
# 1. Greenhouse API
# ---------------------------------------------------------------------------

_GREENHOUSE_HOSTS = {
    "boards.greenhouse.io",
    "boards.eu.greenhouse.io",
    "job-boards.greenhouse.io",
    "job-boards.eu.greenhouse.io",
}

def scrape_greenhouse(url: str):
    parsed = urlparse(url)
    if parsed.netloc not in _GREENHOUSE_HOSTS:
        return None

    parts = [p for p in parsed.path.strip("/").split("/") if p]
    # Expected path: /<company>/jobs/<id>
    if len(parts) < 3 or parts[1] != "jobs":
        return None

    company, job_id = parts[0], parts[2]
    api_base = (
        "https://boards-api.eu.greenhouse.io/v1/boards"
        if "eu" in parsed.netloc
        else "https://boards-api.greenhouse.io/v1/boards"
    )

    try:
        # Get company display name
        cr = requests.get(f"{api_base}/{company}", headers=HEADERS, timeout=15)
        org_name = cr.json().get("name", company.replace("-", " ").title()) if cr.ok else company.replace("-", " ").title()

        # Get job details
        jr = requests.get(f"{api_base}/{company}/jobs/{job_id}", headers=HEADERS, timeout=15)
        jr.raise_for_status()
        data = jr.json()
    except Exception as e:
        print(f"Greenhouse API error: {e}", file=sys.stderr)
        return None

    title = (data.get("title") or "Job Listing").strip()
    loc_obj = data.get("location") or {}
    location = (loc_obj.get("name") or "").strip()
    # Greenhouse returns HTML-entity-escaped HTML — unescape before parsing
    description = html_to_text(unescape(data.get("content") or ""))

    print(f"[Greenhouse API] {org_name} — {title}", file=sys.stderr)
    return {
        "title": title,
        "organization_name": org_name,
        "location": location,
        "job_type": "full-time",
        "salary_range": "",
        "application_url": url,
    }, description


# ---------------------------------------------------------------------------
# 2. Lever API
# ---------------------------------------------------------------------------

def scrape_lever(url: str):
    parsed = urlparse(url)
    if parsed.netloc != "jobs.lever.co":
        return None

    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(parts) < 2:
        return None

    company, posting_id = parts[0], parts[1]

    try:
        r = requests.get(
            f"https://api.lever.co/v0/postings/{company}/{posting_id}",
            headers=HEADERS,
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"Lever API error: {e}", file=sys.stderr)
        return None

    title = (data.get("text") or "Job Listing").strip()
    org_name = company.replace("-", " ").title()
    cats = data.get("categories") or {}
    location = (cats.get("location") or "").strip()
    job_type = (cats.get("commitment") or "full-time").lower()

    # Build description from multiple HTML fields Lever provides
    html_parts = [data.get("description") or ""]
    for lst in data.get("lists") or []:
        html_parts.append(f"<h3>{lst.get('text', '')}</h3>")
        html_parts.append(lst.get("content") or "")
    html_parts.append(data.get("additional") or "")
    description = html_to_text("\n".join(html_parts))

    print(f"[Lever API] {org_name} — {title}", file=sys.stderr)
    return {
        "title": title,
        "organization_name": org_name,
        "location": location,
        "job_type": job_type or "full-time",
        "salary_range": "",
        "application_url": url,
    }, description


# ---------------------------------------------------------------------------
# 3 & 4. Generic: JSON-LD + static HTML heuristics
# ---------------------------------------------------------------------------

def extract_json_ld(soup: BeautifulSoup) -> dict | None:
    """Return the first JobPosting JSON-LD block found, or None."""
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            raw = json.loads(script.string or "")
            items = raw if isinstance(raw, list) else [raw]
            if isinstance(raw, dict) and "@graph" in raw:
                items = raw["@graph"]
            for item in items:
                if str(item.get("@type", "")).lower() in ("jobposting",):
                    return item
        except (json.JSONDecodeError, AttributeError):
            continue
    return None


def parse_json_ld(ld: dict, url: str) -> tuple[dict, str]:
    title = (ld.get("title") or ld.get("name") or "Job Listing").strip()

    org_obj = ld.get("hiringOrganization") or {}
    org_name = (org_obj.get("name") if isinstance(org_obj, dict) else str(org_obj)).strip() or org_from_host(url)

    # Location
    loc_obj = ld.get("jobLocation") or {}
    if isinstance(loc_obj, list):
        loc_obj = loc_obj[0] if loc_obj else {}
    addr = (loc_obj.get("address") or {}) if isinstance(loc_obj, dict) else {}
    if isinstance(addr, str):
        location = addr
    else:
        parts = [
            addr.get("addressLocality", ""),
            addr.get("addressRegion", ""),
            addr.get("addressCountry", ""),
        ]
        location = ", ".join(p for p in parts if p).strip(", ")
    if not location and isinstance(loc_obj, dict):
        location = loc_obj.get("name") or ""

    # Employment type
    emp = (ld.get("employmentType") or "full-time").lower()

    # Salary
    salary_obj = ld.get("baseSalary") or {}
    salary = ""
    if isinstance(salary_obj, dict):
        val = salary_obj.get("value") or {}
        currency = salary_obj.get("currency", "")
        if isinstance(val, dict):
            mn, mx = val.get("minValue", ""), val.get("maxValue", "")
            if mn and mx:
                salary = f"{currency} {mn}–{mx}".strip()
            elif mn or mx:
                salary = f"{currency} {mn or mx}".strip()

    description = html_to_text(ld.get("description") or "")

    return {
        "title": title,
        "organization_name": org_name,
        "location": location,
        "job_type": emp,
        "salary_range": salary,
        "application_url": url,
    }, description


def scrape_static(url: str):
    """Fetch static HTML, try JSON-LD then heuristics. Returns None if page looks JS-rendered."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"Static fetch error: {e}", file=sys.stderr)
        return None

    # --- JSON-LD (best quality) ---
    ld = extract_json_ld(soup)
    if ld:
        fm, description = parse_json_ld(ld, url)
        if description or fm["title"] != "Job Listing":
            print(f"[JSON-LD] {fm['organization_name']} — {fm['title']}", file=sys.stderr)
            return fm, description

    # --- Heuristic HTML extraction ---
    body_text = soup.get_text(strip=True)
    if len(body_text) < 400:
        # Too little content — likely JS-rendered, signal caller to use fallback
        return None

    title = ""
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        title = og["content"].strip()
    if not title and soup.title:
        title = soup.title.get_text(strip=True)
    if not title:
        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else "Job Listing"

    og_site = soup.find("meta", property="og:site_name")
    org_name = (og_site["content"].strip() if og_site and og_site.get("content") else "") or org_from_host(url)

    description = soup_main_text(soup)
    print(f"[Static HTML] {org_name} — {title}", file=sys.stderr)
    return {
        "title": title,
        "organization_name": org_name,
        "location": "",
        "job_type": "full-time",
        "salary_range": "",
        "application_url": url,
    }, description


# ---------------------------------------------------------------------------
# 5. Jina Reader fallback
# ---------------------------------------------------------------------------

def scrape_jina(url: str) -> tuple[dict, str]:
    """Use r.jina.ai to render and extract any page, including JS-heavy ones."""
    print("Falling back to Jina Reader API…", file=sys.stderr)
    try:
        jina_url = f"https://r.jina.ai/{url}"
        r = requests.get(
            jina_url,
            headers={**HEADERS, "Accept": "text/plain", "X-Return-Format": "markdown"},
            timeout=45,
        )
        r.raise_for_status()
        content = r.text.strip()
    except Exception as e:
        print(f"Jina Reader error: {e}", file=sys.stderr)
        return {
            "title": "Job Listing",
            "organization_name": org_from_host(url),
            "location": "", "job_type": "full-time", "salary_range": "",
            "application_url": url,
        }, f"See full listing at: {url}"

    lines = [l.strip() for l in content.splitlines() if l.strip()]

    # Jina prepends "Title: ..." and "URL Source: ..." metadata lines
    title = "Job Listing"
    body_start = 0
    for i, line in enumerate(lines):
        if line.startswith("Title:"):
            title = line[6:].strip()
        elif line.startswith("URL Source:") or line.startswith("Markdown Content:"):
            body_start = i + 1
            break

    description = "\n".join(lines[body_start:]) if body_start else "\n".join(lines[1:])
    org_name = org_from_host(url)

    print(f"[Jina Reader] {org_name} — {title}", file=sys.stderr)
    return {
        "title": title,
        "organization_name": org_name,
        "location": "", "job_type": "full-time", "salary_range": "",
        "application_url": url,
    }, description


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def scrape_url(url: str) -> tuple[dict, str]:
    result = scrape_greenhouse(url)
    if result is None:
        result = scrape_lever(url)
    if result is None:
        result = scrape_static(url)
    if result is None:
        result = scrape_jina(url)

    if result is None:
        print("Could not extract job data from URL (all strategies failed).", file=sys.stderr)
        sys.exit(1)

    fm_partial, description = result
    created = datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ") if hasattr(datetime, "UTC") else datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    fm = {
        "title":                   fm_partial.get("title", "Job Listing"),
        "organization_name":       fm_partial.get("organization_name", "Company"),
        "organization_logo":       "",
        "location":                fm_partial.get("location", ""),
        "job_type":                fm_partial.get("job_type", "full-time"),
        "salary_range":            fm_partial.get("salary_range", ""),
        "expires_at":              "",
        "application_email":       "",
        "application_url":         fm_partial.get("application_url", url),
        "application_instructions": "",
        "requirements":            "",
        "created_at":              created,
        "views_count":             0,
    }
    return fm, description


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: scrape-job-url.py <job_url>", file=sys.stderr)
        sys.exit(1)

    url = sys.argv[1].strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    fm, body = scrape_url(url)

    company_slug = slugify(fm["organization_name"])
    title_slug = slugify(fm["title"])[:50]
    filename = (
        f"{company_slug}-{title_slug}.md"
        if title_slug and title_slug != "job"
        else f"{company_slug}-job.md"
    )

    out_path = JOBS_DIR / filename
    if out_path.exists():
        stem = out_path.stem
        for i in range(1, 100):
            out_path = JOBS_DIR / f"{stem}-{i}.md"
            if not out_path.exists():
                break

    JOBS_DIR.mkdir(parents=True, exist_ok=True)

    lines = ["---"]
    for k, v in fm.items():
        s = str(v).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
        lines.append(f'{k}: "{s}"')
    lines += ["---", "", body]

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(str(out_path))


if __name__ == "__main__":
    main()
