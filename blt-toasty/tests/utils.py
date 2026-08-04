import urllib.parse


def parse_path(url):
    """
    Extract clean path from URL, handling query params and fragments.
    This is a copy of the function from worker.py for testing purposes.

    ⚠️  KEEP IN SYNC WITH worker.py parse_path() ⚠️

    Args:
        url: The full URL string

    Returns:
        str: The path component of the URL
    """
    parsed = urllib.parse.urlparse(url)
    path = parsed.path
    if not path or path == "":
        path = "/"
    elif not path.startswith("/"):
        path = "/" + path
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return path
