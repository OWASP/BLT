#!/usr/bin/env python3
"""Validate that a generated Jekyll site only contains publishable output."""

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent

# Repository-only files and directories. Keep in sync with `exclude` in _config.yml.
FORBIDDEN_PATHS = (
    ".github",
    ".gitlab-ci.yml",
    "CONTRIBUTING.md",
    "Gemfile",
    "Gemfile.lock",
    "LICENSE",
    "QUICKSTART.md",
    "README.md",
    "docs",
    "node_modules",
    "package-lock.json",
    "package.json",
    "playwright.config.js",
    "schemas",
    "scripts",
    "tests",
    "tmp",
    "wrangler.toml",
)

# Output directories generated from a source collection: output directory -> source directory.
COLLECTION_OUTPUTS = {
    "courses": "_courses",
    "instructors": "_instructors",
    "labs": "_labs",
}


def find_problems(site_dir: Path, repo_root: Path = REPO_ROOT) -> list[str]:
    """Return a description of every file that should not be in the site output."""
    problems = []

    for name in FORBIDDEN_PATHS:
        if (site_dir / name).exists():
            problems.append(f"{name}: repository-only path must not be published")

    for output_name, source_name in COLLECTION_OUTPUTS.items():
        output_dir = site_dir / output_name
        if not output_dir.is_dir():
            continue

        for page_dir in sorted(path for path in output_dir.iterdir() if path.is_dir()):
            if not (repo_root / source_name / f"{page_dir.name}.md").is_file():
                problems.append(
                    f"{output_name}/{page_dir.name}: no matching {source_name}/{page_dir.name}.md"
                )

    return problems


def main(argv: list[str]) -> int:
    """Validate the site directory passed on the command line."""
    if len(argv) != 2:
        print("Usage: validate_site_output.py <site-dir>", file=sys.stderr)
        return 2

    site_dir = Path(argv[1])
    if not (site_dir / "index.html").is_file():
        print(f"{site_dir} is not a generated site: index.html is missing", file=sys.stderr)
        return 2

    problems = find_problems(site_dir)
    for problem in problems:
        print(f"FAILED: {problem}")

    if problems:
        return 1

    print(f"Site output {site_dir} contains only publishable files.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
