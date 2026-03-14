"""Parse a mentor application issue body and append the new entry to src/mentors.yml.

Expected issue body format (produced by the homepage form or the issue template):

    ## Mentor Application

    - **Name**: Jane Doe
    - **GitHub Username**: @janedoe
    - **Specialties**: frontend, python
    - **Max Mentees**: 3
    - **Timezone**: UTC+5:30

Environment variables (set by the GitHub Actions workflow):
    ISSUE_BODY      - Raw issue body text.
    MENTORS_YML     - Path to the mentors config file (default: src/mentors.yml).
    GITHUB_OUTPUT   - Set automatically by the GitHub Actions runner; outputs are written here.
"""

import os
import re
import sys
import yaml


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?$")
_SPECIALTY_RE = re.compile(r"^[a-z0-9][a-z0-9+#.\-]{0,29}$")


def _clean_text(val: str) -> str:
    """Strip whitespace and remove characters that are special in YAML scalars.

    HTML comments are stripped first so that inline ``<!-- ... -->`` fragments
    from GitHub issue templates don't pollute parsed field values.
    Newlines and carriage returns are then collapsed to a single space to prevent
    YAML multi-line injection (e.g. a crafted name field that adds extra YAML keys).
    """
    # Remove HTML comments (e.g. template guidance hints like <!-- required -->)
    val = re.sub(r"<!--.*?-->", "", val, flags=re.DOTALL)
    # Collapse newlines/carriage returns before any other processing
    val = re.sub(r"[\r\n]+", " ", val)
    val = val.strip()
    # Remove other YAML-unsafe characters
    val = re.sub(r'["\'\[\]{}|>&]', "", val)
    return val.strip()


def _parse_field(pattern: str, body: str) -> str:
    m = re.search(pattern, body, re.IGNORECASE | re.MULTILINE)
    return _clean_text(m.group(1)) if m else ""


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_body(body: str) -> dict:
    """Extract mentor fields from the markdown-formatted issue body."""
    name = _parse_field(r"^\s*-\s*\*\*Name\*\*:\s*(.+)$", body)
    raw_username = _parse_field(r"^\s*-\s*\*\*GitHub Username\*\*:\s*@?(\S+)", body)
    raw_specialties = _parse_field(r"^\s*-\s*\*\*Specialties\*\*:\s*(.+)$", body)
    max_mentees_raw = _parse_field(r"^\s*-\s*\*\*Max Mentees\*\*:\s*(\d+)", body)
    timezone = _parse_field(r"^\s*-\s*\*\*Timezone\*\*:\s*(.+)$", body)
    raw_referred_by = _parse_field(r"^\s*-\s*\*\*Referred By\*\*:\s*@?(\S+)", body)

    # Normalize placeholder values to empty string
    for placeholder in ("_none_", "_not specified_", "none", "n/a", "-", ""):
        if raw_specialties.lower() == placeholder:
            raw_specialties = ""
        if timezone.lower() == placeholder:
            timezone = ""
        if raw_referred_by.lower() == placeholder:
            raw_referred_by = ""

    # Strip leading @ from referred_by if present (single @ only)
    referred_by = (raw_referred_by[1:] if raw_referred_by.startswith("@") else raw_referred_by).strip()
    # Validate referred_by as a GitHub username (optional field)
    if referred_by and not _USERNAME_RE.match(referred_by):
        referred_by = ""

    # Parse and validate specialties
    specialties = []
    if raw_specialties:
        for tag in raw_specialties.split(","):
            tag = tag.strip().lower()
            if tag and _SPECIALTY_RE.match(tag):
                specialties.append(tag)

    # Max mentees — default 3, clamp 1–10
    try:
        max_mentees = max(1, min(10, int(max_mentees_raw))) if max_mentees_raw else 3
    except ValueError:
        max_mentees = 3

    return {
        "name": name,
        "github_username": raw_username,
        "specialties": specialties,
        "max_mentees": max_mentees,
        "timezone": timezone,
        "referred_by": referred_by,
    }


# ---------------------------------------------------------------------------
# YAML entry builder
# ---------------------------------------------------------------------------

def _yaml_quote(val: str) -> str:
    """Return a double-quoted YAML scalar representation of val using PyYAML."""
    # yaml.dump with double-quote style handles all special characters correctly.
    return yaml.dump(val, default_style='"').rstrip("\n")


def build_entry(fields: dict) -> str:
    """Return a YAML block for one mentor entry, indented for the mentors list."""
    lines = [
        f'  - github_username: {_yaml_quote(fields["github_username"])}',
        f'    name: {_yaml_quote(fields["name"])}',
    ]
    if fields["specialties"]:
        lines.append("    specialties:")
        for tag in fields["specialties"]:
            lines.append(f"      - {tag}")
    lines.append(f'    max_mentees: {fields["max_mentees"]}')
    lines.append("    active: true")
    if fields["timezone"]:
        lines.append(f'    timezone: {_yaml_quote(fields["timezone"])}')
    if fields.get("referred_by"):
        lines.append(f'    referred_by: {_yaml_quote(fields["referred_by"])}')
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    body = os.environ.get("ISSUE_BODY", "")
    if not body:
        print("ERROR: ISSUE_BODY env var is empty.", file=sys.stderr)
        sys.exit(1)

    fields = parse_body(body)

    if not fields["name"]:
        print("ERROR: Could not parse 'Name' from the issue body.", file=sys.stderr)
        sys.exit(1)

    if not fields["github_username"]:
        print("ERROR: Could not parse 'GitHub Username' from the issue body.", file=sys.stderr)
        sys.exit(1)

    if not _USERNAME_RE.match(fields["github_username"]):
        print(
            f"ERROR: '{fields['github_username']}' is not a valid GitHub username.",
            file=sys.stderr,
        )
        sys.exit(1)

    mentors_path = os.environ.get("MENTORS_YML", "src/mentors.yml")

    try:
        with open(mentors_path, "r", encoding="utf-8") as fh:
            content = fh.read()
    except OSError as exc:
        print(f"ERROR: Cannot read {mentors_path}: {exc}", file=sys.stderr)
        sys.exit(1)

    # Exact case-insensitive duplicate check: parse the YAML and compare usernames
    # rather than doing a raw substring search (which causes false positives).
    try:
        existing = yaml.safe_load(content) or {}
        existing_mentors = existing.get("mentors", []) if isinstance(existing, dict) else []
    except yaml.YAMLError:
        existing_mentors = []
    username_lower = fields["github_username"].lower()
    if any(
        str(m.get("github_username", "")).lower() == username_lower
        for m in existing_mentors
        if isinstance(m, dict)
    ):
        print(
            f"::warning::{fields['github_username']} is already in {mentors_path} — skipping.",
            flush=True,
        )
        # Write empty outputs so the downstream step is skipped
        _write_output("github_username", "")
        _write_output("name", "")
        sys.exit(0)

    new_entry = build_entry(fields)
    new_content = content.rstrip("\n") + "\n\n" + new_entry + "\n"

    with open(mentors_path, "w", encoding="utf-8") as fh:
        fh.write(new_content)

    # Keep src/mentors_data.py in sync so the Cloudflare Workers bundle always
    # has up-to-date mentor data without relying on open() path resolution.
    _write_mentors_data_module(new_content, mentors_path)

    print(
        f"Added mentor @{fields['github_username']} ({fields['name']}) to {mentors_path}.",
        flush=True,
    )

    _write_output("github_username", fields["github_username"])
    _write_output("name", fields["name"])


def _write_output(key: str, value: str) -> None:
    """Append a key=value pair to GITHUB_OUTPUT (GitHub Actions step outputs)."""
    github_output = os.environ.get("GITHUB_OUTPUT", "")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as fh:
            fh.write(f"{key}={value}\n")


def _write_mentors_data_module(yaml_content: str, mentors_path: str) -> None:
    """Regenerate ``src/mentors_data.py`` from the updated YAML content.

    This keeps the bundled Python module in sync with ``src/mentors.yml`` so
    that the Cloudflare Workers runtime always has the latest mentor data
    available via ``from mentors_data import MENTORS_YAML``, regardless of
    whether ``open()`` path resolution works in that environment.
    """
    data_module_path = os.path.join(
        os.path.dirname(os.path.abspath(mentors_path)),
        "mentors_data.py",
    )
    module_content = (
        '"""Bundled mentor pool data.\n\n'
        "Auto-generated from src/mentors.yml \u2014 do not edit manually.\n"
        "Regenerated by .github/scripts/add_mentor.py whenever a new mentor is added.\n\n"
        "Embedding the YAML as a Python string ensures that the content is always\n"
        "available in the Cloudflare Workers bundle, regardless of how the runtime\n"
        'resolves ``open()`` paths.\n'
        '"""\n\n'
        'MENTORS_YAML = """\\\n'
        + yaml_content
        + '"""\n'
    )
    with open(data_module_path, "w", encoding="utf-8") as fh:
        fh.write(module_content)
    print(f"Regenerated {data_module_path}.", flush=True)


if __name__ == "__main__":
    main()
