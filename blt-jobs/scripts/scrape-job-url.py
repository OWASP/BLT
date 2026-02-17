#!/usr/bin/env python3
"""
Fetch a job URL, extract title/description/company, and write _jobs/company-slug-job-title-slug.md.
Used by the quick-add GitHub Action.
"""
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("pip install requests beautifulsoup4", file=sys.stderr)
    sys.exit(1)

JOBS_DIR = Path(__file__).resolve().parent.parent / "_jobs"


def slugify(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[-\s]+", "-", s)
    return s.strip("-") or "job"


def extract_text(soup: BeautifulSoup, selectors: list[str], max_chars: int = 10000) -> str:
    for sel in selectors:
        el = soup.select_one(sel)
        if el:
            text = el.get_text(separator="\n", strip=True)
            if text:
                return text[:max_chars]
    return ""


def scrape_url(url: str) -> tuple[dict, str]:
    """Fetch URL, parse, return (frontmatter_dict, description_body)."""
    headers = {"User-Agent": "OWASP-BLT-Jobs-Bot/1.0 (https://github.com/OWASP-BLT/BLT-Jobs)"}
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    # Title: og:title, <title>, or first h1
    title = ""
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        title = og_title["content"].strip()
    if not title and soup.title:
        title = soup.title.get_text(strip=True)
    if not title:
        title = extract_text(soup, ["h1"])
    if not title:
        title = "Job Listing"

    # Organization: og:site_name, or from URL hostname
    org = ""
    og_site = soup.find("meta", property="og:site_name")
    if og_site and og_site.get("content"):
        org = og_site["content"].strip()
    if not org:
        parsed = urlparse(url)
        host = parsed.netloc or parsed.path
        org = host.replace("www.", "").split(".")[0] if host else "Company"
    org = org or "Company"

    # Description: meta description, or main content
    description = ""
    meta_desc = soup.find("meta", attrs={"name": re.compile(r"description", re.I)})
    if meta_desc and meta_desc.get("content"):
        description = meta_desc["content"].strip()
    if not description:
        description = extract_text(
            soup,
            [
                "[role='main']",
                "main",
                ".content",
                ".job-description",
                ".description",
                "#content",
                "article",
                "body",
            ],
            max_chars=15000,
        )
    if not description:
        description = f"See the full listing at: {url}"

    created = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    fm = {
        "title": title,
        "organization_name": org,
        "organization_logo": "",
        "location": "",
        "job_type": "full-time",
        "salary_range": "",
        "expires_at": "",
        "application_email": "",
        "application_url": url,
        "application_instructions": "",
        "requirements": "",
        "created_at": created,
        "views_count": 0,
    }
    return fm, description


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
    filename = f"{company_slug}-{title_slug}.md" if title_slug != "job" else f"{company_slug}-job.md"
    # Ensure unique
    out_path = JOBS_DIR / filename
    if out_path.exists():
        base, ext = out_path.stem, out_path.suffix
        for i in range(1, 100):
            out_path = JOBS_DIR / f"{base}-{i}{ext}"
            if not out_path.exists():
                break

    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    lines = ["---"]
    for k, v in fm.items():
        s = str(v)
        s = s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
        lines.append(f'{k}: "{s}"')
    lines.append("---")
    lines.append("")
    lines.append(body)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(str(out_path))


if __name__ == "__main__":
    main()
