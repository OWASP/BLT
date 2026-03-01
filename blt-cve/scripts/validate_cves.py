#!/usr/bin/env python3
"""
Validate all BLT CVE JSON files in /cves/** against the JSON schema.

Checks:
  - Each file validates against schema/blt-cve-schema.json
  - The 'id' field matches the filename
  - The year in the 'id' matches the containing folder
  - No duplicate IDs across the registry
"""

import json
import os
import re
import sys

try:
    import jsonschema
except ImportError:
    print("ERROR: jsonschema package is required. Install with: pip install jsonschema")
    sys.exit(1)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_PATH = os.path.join(REPO_ROOT, "schema", "blt-cve-schema.json")
CVES_DIR = os.path.join(REPO_ROOT, "cves")

ID_PATTERN = re.compile(r"^BLT-(\d{4})-\d{4}$")


def load_schema():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def collect_cve_files():
    """Yield (year_folder, filepath) for every .json file under /cves."""
    for year in sorted(os.listdir(CVES_DIR)):
        year_dir = os.path.join(CVES_DIR, year)
        if not os.path.isdir(year_dir):
            continue
        for fname in sorted(os.listdir(year_dir)):
            if fname.endswith(".json"):
                yield year, os.path.join(year_dir, fname)


def validate():
    schema = load_schema()
    validator = jsonschema.Draft7Validator(schema)

    errors = []
    seen_ids = {}

    for year_folder, filepath in collect_cve_files():
        rel = os.path.relpath(filepath, REPO_ROOT)

        # Load JSON
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                entry = json.load(f)
        except json.JSONDecodeError as exc:
            errors.append(f"{rel}: invalid JSON – {exc}")
            continue

        # Schema validation
        schema_errors = sorted(validator.iter_errors(entry), key=lambda e: e.path)
        for err in schema_errors:
            path = ".".join(str(p) for p in err.absolute_path) or "(root)"
            errors.append(f"{rel}: schema error at '{path}': {err.message}")

        entry_id = entry.get("id", "")

        # ID must match filename (without .json)
        expected_id = os.path.splitext(os.path.basename(filepath))[0]
        if entry_id != expected_id:
            errors.append(
                f"{rel}: 'id' field '{entry_id}' does not match filename '{expected_id}'"
            )

        # Year in ID must match folder name
        match = ID_PATTERN.match(entry_id)
        if match:
            id_year = match.group(1)
            if id_year != year_folder:
                errors.append(
                    f"{rel}: year in ID '{entry_id}' ({id_year}) does not match "
                    f"folder year '{year_folder}'"
                )
        else:
            errors.append(
                f"{rel}: 'id' field '{entry_id}' does not match BLT-YYYY-NNNN pattern"
            )

        # Duplicate ID check
        if entry_id in seen_ids:
            errors.append(
                f"{rel}: duplicate ID '{entry_id}' (already seen in {seen_ids[entry_id]})"
            )
        else:
            seen_ids[entry_id] = rel

    return errors


def main():
    if not os.path.isdir(CVES_DIR):
        print("No /cves directory found – nothing to validate.")
        sys.exit(0)

    print("Validating BLT CVE entries...")
    errors = validate()

    if errors:
        print(f"\nFound {len(errors)} validation error(s):\n")
        for err in errors:
            print(f"  ✗ {err}")
        sys.exit(1)
    else:
        print("All entries are valid ✓")
        sys.exit(0)


if __name__ == "__main__":
    main()
