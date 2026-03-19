"""Fetch tech/open-source communities from Reddit and update ossh_catalog.json."""

import json
import logging
import re
from pathlib import Path
from time import sleep

import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "ossh_catalog.json"
HEADERS = {"User-Agent": "OsshCommunity/1.0"}
MAX_COMMUNITIES = 100

BASE_TOPICS = [
    "programming",
    "coding",
    "developers",
    "computerscience",
    "technology",
    "opensource",
    "software",
]

TECH_KEYWORDS = {
    "programming", "code", "coding", "developer", "software", "web", "api",
    "database", "devops", "cloud", "opensource", "github", "computer", "tech",
    "engineering", "framework", "language", "script", "algorithm", "backend",
    "frontend", "fullstack", "infrastructure", "security", "docker", "kubernetes",
    "linux", "python", "javascript", "java", "rust", "golang", "cpp", "csharp",
}


def is_tech_related(data):
    text = (
        (data.get("description", "") or "").lower()
        + (data.get("title", "") or "").lower()
        + (data.get("display_name", "") or "").lower()
    )
    return any(kw in text for kw in TECH_KEYWORDS)


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def extract_tags(data):
    tags = {slugify(data["display_name"])}
    for keyword in TECH_KEYWORDS:
        if keyword in (data.get("description", "") or "").lower():
            tags.add(keyword)
    return [t for t in tags if t]


def search_subreddits(query):
    url = f"https://www.reddit.com/subreddits/search.json?q={query}&limit=100"
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        return response.json()["data"]["children"]
    except Exception as e:
        logger.error("Error searching subreddits for '%s': %s", query, e)
        return []


def fetch_communities():
    processed = set()
    communities = []

    for topic in BASE_TOPICS:
        try:
            sleep(1)
            subreddits = search_subreddits(topic)
            for subreddit in subreddits:
                if len(communities) >= MAX_COMMUNITIES:
                    logger.info("Reached max communities limit (%d)", MAX_COMMUNITIES)
                    return communities

                data = subreddit["data"]
                name = data.get("display_name", "")

                if name in processed or not is_tech_related(data):
                    continue

                processed.add(name)
                communities.append({
                    "name": name,
                    "description": (data.get("description", "") or "")[:500],
                    "url": f"https://reddit.com/r/{name}",
                    "source": "Reddit",
                    "member_count": data.get("subscribers", 0),
                    "primary_language": None,
                    "tags": extract_tags(data),
                })
                logger.info("Added r/%s (%d subscribers)", name, data.get("subscribers", 0))

        except Exception as e:
            logger.error("Failed processing topic '%s': %s", topic, e)

    return communities


def main():
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    communities = fetch_communities()

    if communities:
        catalog["communities"] = communities
        logger.info("Updated catalog with %d communities", len(communities))
    else:
        logger.warning("No communities fetched, keeping existing data")

    CATALOG_PATH.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
