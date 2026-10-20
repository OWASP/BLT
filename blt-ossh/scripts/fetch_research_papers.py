"""Fetch research papers from arXiv and update ossh_catalog.json."""

import json
import logging
import os
import time
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from defusedxml import ElementTree as ET

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

CATALOG_PATH = Path(
    os.environ.get("OSSH_CATALOG_PATH")
    or Path(__file__).resolve().parent.parent / "public" / "data" / "ossh_catalog.json"
)
ARXIV_API_URL = "https://export.arxiv.org/api/query?"
MAX_PAPERS = 100
RATE_LIMIT_DELAY = 3

# arXiv categories for software-adjacent topics that map well to user interests.
CATEGORY_TAGS = {
    "cs.SE": ["software-engineering", "testing"],
    "cs.PL": ["programming-languages"],
    "cs.LG": ["machine-learning"],
    "cs.AI": ["artificial-intelligence"],
    "cs.CR": ["security", "cryptography"],
    "cs.DS": ["data-structures", "algorithms"],
    "cs.DB": ["databases"],
    "cs.DC": ["distributed-systems"],
    "cs.NE": ["neural-networks", "machine-learning"],
    "cs.CL": ["natural-language-processing", "nlp"],
    "cs.CV": ["computer-vision"],
    "cs.IR": ["information-retrieval"],
}

SEARCH_QUERIES = [
    "cat:cs.SE",
    "cat:cs.PL",
    "cat:cs.LG",
    "cat:cs.AI",
    "cat:cs.CR",
    "cat:cs.DS",
    "cat:cs.DB",
    "cat:cs.DC",
    "cat:cs.NE",
    "cat:cs.CL",
]


def category_to_tags(term):
    if not term:
        return []
    return CATEGORY_TAGS.get(term, [term.lower().replace(".", "-")])


def dedupe_tags(tags):
    return list(OrderedDict.fromkeys(tags))


def fetch_arxiv_papers():
    """Fetch papers from arXiv using API queries."""
    papers = {}
    failed_queries = 0
    now = datetime.now(timezone.utc)
    lower_bound = (now - timedelta(days=30)).strftime("%Y%m%d%H%M")
    upper_bound = now.strftime("%Y%m%d%H%M")
    date_query = f"submittedDate:[{lower_bound} TO {upper_bound}]"

    for query in SEARCH_QUERIES:
        try:
            time.sleep(RATE_LIMIT_DELAY)

            full_query = f"{query} AND {date_query}"
            params = {
                "search_query": full_query,
                "start": 0,
                "max_results": 20,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }

            response = requests.get(ARXIV_API_URL, params=params, timeout=30)
            response.raise_for_status()

            root = ET.fromstring(response.content)
            ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

            for entry in root.findall("atom:entry", ns):
                try:
                    arxiv_id = entry.find("atom:id", ns).text.split("/abs/")[-1]
                    if arxiv_id in papers:
                        continue

                    title = entry.find("atom:title", ns).text.strip()
                    summary = entry.find("atom:summary", ns).text.strip()
                    published = entry.find("atom:published", ns).text

                    authors = []
                    for author in entry.findall("atom:author", ns):
                        name = author.find("atom:name", ns)
                        if name is not None and name.text:
                            authors.append(name.text)

                    tags = []
                    for category in entry.findall("atom:category", ns):
                        tags.extend(category_to_tags(category.get("term")))

                    tags = dedupe_tags(tags)

                    papers[arxiv_id] = {
                        "title": title,
                        "authors": authors[:3],
                        "summary": summary[:500],
                        "published": published,
                        "arxiv_id": arxiv_id,
                        "url": f"https://arxiv.org/abs/{arxiv_id}",
                        "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}.pdf",
                        "source": "arXiv",
                        "tags": tags,
                    }
                except Exception as exc:
                    logger.warning("Failed to parse entry: %s", exc)

            logger.info("Fetched papers for query '%s' (total unique: %d)", query, len(papers))

        except requests.exceptions.RequestException as exc:
            logger.error("Request failed for query '%s': %s", query, exc)
            failed_queries += 1
        except Exception as exc:
            logger.error("Unexpected error for query '%s': %s", query, exc)
            failed_queries += 1

    if failed_queries == len(SEARCH_QUERIES):
        raise RuntimeError("Failed to fetch research papers: all arXiv queries failed")

    return list(papers.values())[:MAX_PAPERS]


def main():
    """Update catalog with research papers."""
    try:
        catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.error("Failed to read catalog: %s", exc)
        return

    papers = fetch_arxiv_papers()

    existing_count = len(catalog.get("research_papers", []))
    if not papers:
        logger.warning("No papers fetched, keeping existing data")
    elif existing_count > 0 and len(papers) < existing_count * 0.5:
        logger.warning(
            "Fetched significantly fewer papers (%d vs %d), keeping existing data",
            len(papers),
            existing_count,
        )
    else:
        catalog["research_papers"] = papers
        logger.info("Updated catalog with %d research papers", len(papers))

    CATALOG_PATH.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
