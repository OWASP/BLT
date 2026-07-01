import glob
import json
import sys
from pathlib import Path

import frontmatter
from jsonschema import Draft202012Validator


repo_root = Path(__file__).resolve().parent.parent
schema_path = repo_root / "schemas" / "lab.schema.json"

with schema_path.open(encoding="utf-8") as f:
    schema = json.load(f)

validator = Draft202012Validator(schema)

failed = False

for lab_file in sorted(glob.glob(str(repo_root / "_labs" / "*.md"))):
    lab_path = Path(lab_file)
    display_path = lab_path.relative_to(repo_root)

    try:
        post = frontmatter.load(lab_path)
    except Exception as e:
        failed = True
        print(f"\nFAILED: {display_path}")
        print(f"  - Could not parse frontmatter: {e}")
        continue

    errors = sorted(
        validator.iter_errors(post.metadata),
        key=lambda e: tuple(str(p) for p in e.path)
    )

    if errors:
        failed = True
        print(f"\nFAILED: {display_path}")

        for error in errors:
            path = ".".join(str(p) for p in error.path)
            print(f"  - {path}: {error.message}")
    else:
        print(f"PASS: {display_path}")

if failed:
    sys.exit(1)

print("\nAll labs passed validation.")
