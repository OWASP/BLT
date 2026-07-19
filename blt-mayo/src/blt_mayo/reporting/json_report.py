from __future__ import annotations

import json
from pathlib import Path

from blt_mayo.models.scan import ScanResult


def write_json_report(result: ScanResult, output: Path, include_artifacts: bool = True) -> Path:
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result.to_dict(include_artifacts=include_artifacts), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return output
