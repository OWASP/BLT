#!/usr/bin/env python3
"""Import the OWASP BLT posts on dev.to (dev.to/owaspblt) into posts/devto/.

Each article becomes posts/devto/<date>-<slug>.html: a front matter block, then dev.to's rendered
HTML with scripts and event handlers stripped and its images saved under public/images/<slug>/, so
the blog no longer depends on dev.to's CDN. The post keeps its dev.to (or own) canonical URL and
author. Run it again to pick up new or edited articles; files are rewritten in place.

    python3 scripts/import_devto.py [--org owaspblt]
"""

import json
import mimetypes
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "posts" / "devto"
IMAGES = ROOT / "public" / "images"
API = "https://dev.to/api"
HEADERS = {"User-Agent": "blt-blog-import (+https://blog.owaspblt.org)", "Accept": "application/json"}
IMAGE_TYPES = {"image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif", "image/webp": ".webp", "image/svg+xml": ".svg"}
IFRAME_HOSTS = ("www.youtube.com", "www.youtube-nocookie.com", "player.vimeo.com")


def fetch(url, accept=None, tries=6):
    """GET url; dev.to answers "Retry later" (429) when called quickly, so back off and retry."""
    headers = dict(HEADERS, Accept=accept) if accept else HEADERS
    for attempt in range(tries):
        try:
            with urlopen(Request(url, headers=headers), timeout=30) as response:
                return response.read(), response.headers.get_content_type()
        except HTTPError as error:
            if error.code not in (429, 500, 502, 503) or attempt == tries - 1:
                raise
        except URLError:
            if attempt == tries - 1:
                raise
        time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"unreachable: {url}")


def fetch_json(url):
    body, _ = fetch(url)
    return json.loads(body)


def clean_slug(slug):
    """dev.to appends a random suffix (-56o9) to every slug; drop it."""
    return re.sub(r"-[0-9a-z]{2,5}$", "", slug).strip("-")


def source_url(src):
    """dev.to's resizing proxy wraps the original URL; prefer the original when it is an upload."""
    match = re.search(r"/(https?%3A%2F%2F.+)$", src)
    return unquote(match.group(1)) if match else src


def save_image(src, slug, index, cache):
    if src in cache:
        return cache[src]
    folder = IMAGES / slug
    for candidate in dict.fromkeys([src, source_url(src)]):
        try:
            data, ctype = fetch(candidate, accept="image/webp,image/png,image/jpeg,image/gif,image/*;q=0.8")
        except (HTTPError, URLError, TimeoutError) as error:
            print(f"  image failed ({error}): {candidate}", file=sys.stderr)
            continue
        ext = IMAGE_TYPES.get(ctype) or mimetypes.guess_extension(ctype or "") or Path(urlparse(candidate).path).suffix
        if not ext or not (ctype or "").startswith("image/"):
            continue
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{index:02d}{ext}"
        path.write_bytes(data)
        cache[src] = f"/images/{slug}/{path.name}"
        return cache[src]
    cache[src] = src  # keep the remote URL rather than lose the image
    return src


def sanitize(html):
    html = re.sub(r"<script\b.*?</script>", "", html, flags=re.S | re.I)
    html = re.sub(r"<style\b.*?</style>", "", html, flags=re.S | re.I)
    html = re.sub(r"\s+on[a-z]+\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)", "", html, flags=re.I)
    html = re.sub(r"(href|src)\s*=\s*\"\s*javascript:[^\"]*\"", r'\1="#"', html, flags=re.I)

    def keep_iframe(match):
        src = re.search(r'src="([^"]+)"', match.group(0))
        host = urlparse(src.group(1)).hostname if src else ""
        return match.group(0) if host in IFRAME_HOSTS else ""

    html = re.sub(r"<iframe\b[^>]*>.*?</iframe>", keep_iframe, html, flags=re.S | re.I)
    return html.strip()


def localize_images(html, slug, cache, counter):
    def replace(match):
        counter[0] += 1
        return f'{match.group(1)}"{save_image(match.group(2), slug, counter[0], cache)}"'

    return re.sub(r'(<img\b[^>]*?\bsrc=)"([^"]+)"', replace, html)


def front_matter(fields):
    lines = ["---"]
    for key, value in fields.items():
        if value in (None, "", []):
            continue
        lines.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
    lines.append("---")
    return "\n".join(lines)


def import_article(summary):
    article = fetch_json(f"{API}/articles/{summary['id']}")
    slug = clean_slug(article["slug"])
    cache, counter = {}, [0]
    cover = save_image(article["cover_image"], slug, 0, cache) if article.get("cover_image") else ""
    body = localize_images(sanitize(article["body_html"]), slug, cache, counter)
    user = article.get("user") or {}
    avatar = save_image(user["profile_image_90"], "authors", 0, {}) if user.get("profile_image_90") else ""
    if avatar.startswith("/images/authors/"):  # one file per author, not 00.* for everyone
        target = IMAGES / "authors" / f"{user['username']}{Path(avatar).suffix}"
        (IMAGES / "authors" / Path(avatar).name).replace(target)
        avatar = f"/images/authors/{target.name}"
    fields = {
        "title": article["title"],
        "slug": slug,
        "date": article["published_at"][:10],
        "updated": (article.get("edited_at") or "")[:10],
        "author": user.get("name") or user.get("username"),
        "author_url": f"https://dev.to/{user['username']}" if user.get("username") else "",
        "author_avatar": avatar,
        "description": article.get("description") or "",
        "tags": article.get("tags") or [],
        "cover": cover,
        "reading_time": article.get("reading_time_minutes") or 0,
        "canonical": article.get("canonical_url") or article.get("url"),
        "source": article.get("url"),
    }
    path = POSTS / f"{fields['date']}-{slug}.html"
    path.write_text(front_matter(fields) + "\n" + body + "\n", encoding="utf-8")
    return path


def main():
    org = sys.argv[sys.argv.index("--org") + 1] if "--org" in sys.argv else "owaspblt"
    POSTS.mkdir(parents=True, exist_ok=True)
    articles = fetch_json(f"{API}/articles?username={org}&per_page=1000")
    print(f"{len(articles)} articles from dev.to/{org}")
    for summary in articles:
        path = import_article(summary)
        print(f"  {path.relative_to(ROOT)}")
        time.sleep(1)


if __name__ == "__main__":
    main()
