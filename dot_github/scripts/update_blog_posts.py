#!/usr/bin/env python3
"""Update profile/README.md with the latest 2 blog posts from dev.to/owaspblt."""

import html
import re
import sys
from datetime import datetime, timezone

import requests

DEV_TO_USERNAME = "owaspblt"
DEV_TO_API = f"https://dev.to/api/articles?username={DEV_TO_USERNAME}&per_page=10"
NUM_POSTS = 2
README_PATH = "profile/README.md"

BLOG_POSTS_START = "<!-- BLOG-POSTS-START -->"
BLOG_POSTS_END = "<!-- BLOG-POSTS-END -->"


def fetch_latest_posts():
    """Fetch the 2 most recent articles from dev.to for *DEV_TO_USERNAME*."""
    resp = requests.get(DEV_TO_API, headers={"Cache-Control": "no-cache"}, timeout=15)
    resp.raise_for_status()
    articles = resp.json()
    # Sort by published_at descending so we always surface the newest posts
    # even if the API returns them in a different order due to caching.
    articles.sort(key=lambda a: a.get("published_at") or "", reverse=True)
    return [a for a in articles if a.get("published_at")][:NUM_POSTS]


def build_blog_posts_section(posts):
    """Return the full markdown section string for *posts* (2-across with images)."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        f"{BLOG_POSTS_START}",
        "## 📝 Latest Blog Posts",
        "",
        f"*Last updated: {timestamp} — from [dev.to/owaspblt](https://dev.to/owaspblt)*",
        "",
        '<table><tr>',
    ]

    for post in posts:
        title = html.escape(post.get("title", "Untitled"))
        url = html.escape(post.get("url", ""))
        description = html.escape(post.get("description", ""))
        published = (post.get("published_at") or "")[:10] or "N/A"
        post_id = post.get("id")
        cover_image = html.escape(
            post.get("cover_image")
            or post.get("social_image")
            or (
                f"https://dev.to/social_previews/article/{post_id}.png"
                if isinstance(post_id, int)
                else ""
            )
        )

        reactions = post.get("positive_reactions_count") or 0
        comments = post.get("comments_count") or 0

        cell = "<td align='center' width='50%'>"
        if cover_image:
            cell += f"<a href='{url}'><img src='{cover_image}' width='400' alt='{title}'></a><br>"
        cell += f"<strong><a href='{url}'>{title}</a></strong> ({published})"
        if description:
            cell += f"<br><sub>{description}</sub>"
        cell += f"<br>❤️ {reactions} reactions &nbsp; 💬 {comments} comments"
        cell += "</td>"
        lines.append(cell)

    lines.append("</tr></table>")
    lines.append("")
    lines.append(BLOG_POSTS_END)
    return "\n".join(lines)


def update_readme(section):
    """Insert or replace the blog posts section in the README."""
    with open(README_PATH, "r", encoding="utf-8") as fh:
        content = fh.read()

    if BLOG_POSTS_START in content and BLOG_POSTS_END in content:
        pattern = re.escape(BLOG_POSTS_START) + r".*?" + re.escape(BLOG_POSTS_END)
        updated = re.sub(pattern, section, content, flags=re.DOTALL)
    else:
        # Insert before contributors section if present, otherwise append
        contributors_marker = "<!-- CONTRIBUTORS-START -->"
        if contributors_marker in content:
            updated = content.replace(
                contributors_marker, section + "\n\n" + contributors_marker
            )
        else:
            updated = content.rstrip() + "\n\n" + section + "\n"

    with open(README_PATH, "w", encoding="utf-8") as fh:
        fh.write(updated)


if __name__ == "__main__":
    print(f"Fetching latest posts from dev.to/{DEV_TO_USERNAME}…")
    try:
        posts = fetch_latest_posts()
    except requests.HTTPError as exc:
        print(
            f"HTTP error fetching posts: {exc.response.status_code} {exc.response.reason}",
            file=sys.stderr,
        )
        sys.exit(1)
    except requests.RequestException as exc:
        print(f"Error fetching posts: {exc}", file=sys.stderr)
        sys.exit(1)

    if not posts:
        print("No posts returned — skipping README update.")
        sys.exit(0)

    print(f"Fetched {len(posts)} post(s):")
    for p in posts:
        print(f"  - {p.get('title')} ({p.get('published_at', '')[:10]})")

    section = build_blog_posts_section(posts)
    update_readme(section)
    print("README updated with latest blog posts.")