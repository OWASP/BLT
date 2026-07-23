#!/usr/bin/env python3
"""Validate every lab's front matter against the lab schema."""

import json
import sys
from pathlib import Path

import frontmatter
from jsonschema import Draft202012Validator


REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schemas" / "lab.schema.json"
LABS_DIR = REPO_ROOT / "_labs"


def main() -> int:
    """Validate each lab and report the exit status."""
    with SCHEMA_PATH.open(encoding="utf-8") as handle:
        schema = json.load(handle)

    validator = Draft202012Validator(schema)
    failed = False

    for lab_path in sorted(LABS_DIR.glob("*.md")):
        display_path = lab_path.relative_to(REPO_ROOT)

        try:
            post = frontmatter.load(lab_path)
        except Exception as error:
            failed = True
            print(f"\nFAILED: {display_path}")
            print(f"  - Could not parse frontmatter: {error}")
            continue

        errors = sorted(
            validator.iter_errors(post.metadata),
            key=lambda error: tuple(str(item) for item in error.path),
        )

        if errors:
            failed = True
            print(f"\nFAILED: {display_path}")

            for error in errors:
                path = ".".join(str(item) for item in error.path)
                print(f"  - {path}: {error.message}")
        else:
            print(f"PASS: {display_path}")

    if failed:
        return 1

    print("\nAll labs passed validation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
