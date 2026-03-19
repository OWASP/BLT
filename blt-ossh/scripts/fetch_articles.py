"""Fetch articles from DEV.to API and update ossh_catalog.json."""

import json
import logging
import time
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "ossh_catalog.json"
BASE_URL = "https://dev.to/api/articles"
TAGS = ["programming", "javascript", "python", "webdev", "tutorial"]
RATE_LIMIT_DELAY = 1


def fetch_articles():
    articles = {}

    for tag in TAGS:
        try:
            time.sleep(RATE_LIMIT_DELAY)
            response = requests.get(BASE_URL, params={"tag": tag}, timeout=30)
            response.raise_for_status()

            for article in response.json():
                external_id = article.get("id")
                if not external_id or external_id in articles:
                    continue

                articles[external_id] = {
                    "title": article.get("title", ""),
                    "author": article.get("user", {}).get("name", ""),
                    "author_profile_image": article.get("user", {}).get("profile_image", ""),
                    "description": article.get("description", ""),
                    "publication_date": article.get("published_at", ""),
                    "source": "DEV Community",
                    "url": article.get("url", ""),
                    "cover_image": article.get("cover_image"),
                    "reading_time_minutes": article.get("reading_time_minutes"),
                    "tags": article.get("tag_list", []),
                }

            logger.info("Fetched %d articles for tag '%s'", len(response.json()), tag)

        except requests.exceptions.RequestException as e:
            logger.error("Request failed for tag '%s': %s", tag, e)
        except Exception as e:
            logger.error("Unexpected error for tag '%s': %s", tag, e)

    return list(articles.values())


def main():
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    articles = fetch_articles()

    if articles:
        catalog["articles"] = articles
        logger.info("Updated catalog with %d articles", len(articles))
    else:
        logger.warning("No articles fetched, keeping existing data")

    CATALOG_PATH.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
