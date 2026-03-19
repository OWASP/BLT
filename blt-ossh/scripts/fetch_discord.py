"""Fetch programming-related Discord servers and update ossh_catalog.json."""

import json
import logging
import os
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "ossh_catalog.json"
DISCORD_API_URL = "https://discord.com/api/v10/discovery/search"

SEARCH_TERMS = [
    "programming",
    "coding",
    "developers",
    "software engineering",
    "open source",
    "opensource",
    "open-source projects",
    "FOSS",
    "developer community",
    "software development",
    "coding help",
    "hackathons",
    "tech discussions",
    "CS students",
    "coding challenges",
    "devops",
    "AI developers",
    "machine learning",
    "data science",
    "web development",
    "backend development",
    "frontend development",
    "full stack developers",
    "game development",
    "cybersecurity",
    "blockchain developers",
    "cloud computing",
    "Linux users",
    "GitHub discussions",
    "collaborative coding",
    "tech startups",
    "coding mentorship",
    "bug bounty",
    "ethical hacking",
    "software architecture",
    "API development",
    "automation",
    "scripting",
    "Python developers",
    "JavaScript developers",
    "React developers",
    "Django developers",
    "Node.js developers",
    "Rust programming",
    "Go programming",
    "Java developers",
    "C++ programming",
    "Android development",
    "iOS development",
    "open-source contributions",
    "freeCodeCamp",
    "100DaysOfCode",
    "code reviews",
    "pair programming",
    "developer networking",
    "open-source events",
    "open-source maintainers",
    "open-source contributors",
    "community-driven development",
    "open-source foundations",
]


def fetch_discord_servers():
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        logger.error("DISCORD_BOT_TOKEN environment variable not set")
        return []

    headers = {"Authorization": f"Bot {token}", "Content-Type": "application/json"}
    seen_ids = set()
    channels = []

    for term in SEARCH_TERMS:
        try:
            response = requests.get(
                DISCORD_API_URL,
                headers=headers,
                params={"query": term, "limit": 20},
                timeout=30,
            )
            response.raise_for_status()
            servers = response.json().get("hits", [])

            for server in servers:
                server_id = server.get("id")
                if not server_id or server_id in seen_ids:
                    continue

                seen_ids.add(server_id)
                icon = server.get("icon")
                logo_url = f"https://cdn.discordapp.com/icons/{server_id}/{icon}.png" if icon else ""

                channels.append({
                    "name": server.get("name", "Unknown"),
                    "description": server.get("description", ""),
                    "source": "Discord",
                    "member_count": server.get("approximate_member_count", 0),
                    "invite_url": f"https://discord.gg/{server.get('vanity_url_code', server_id)}",
                    "logo_url": logo_url,
                    "tags": server.get("keywords", []),
                })

            logger.info("Fetched %d servers for term '%s' (%d unique total)", len(servers), term, len(seen_ids))

        except requests.exceptions.RequestException as e:
            logger.error("Request failed for term '%s': %s", term, e)
        except Exception as e:
            logger.error("Unexpected error for term '%s': %s", term, e)

    return channels


def main():
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    channels = fetch_discord_servers()

    if channels:
        catalog["discussion_channels"] = channels
        logger.info("Updated catalog with %d discussion channels", len(channels))
    else:
        logger.warning("No channels fetched, keeping existing data")

    CATALOG_PATH.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
