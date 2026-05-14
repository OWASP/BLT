"""
Tests for the static API-key smoke script.
"""

import os
import subprocess
from pathlib import Path

from libs.api_key import PUBLIC_BLT_API_KEY


def test_smoke_script_uses_public_static_api_key_by_default(tmp_path):
    """The smoke script should use the public shared API key without local env setup."""
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_curl = fake_bin / "curl"
    fake_curl_source = """#!/usr/bin/env bash
set -euo pipefail

output_file=""
api_key=""
url=""

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    -o)
      output_file="$2"
      shift 2
      ;;
    -H)
      if [[ "$2" == X-BLT-API-Key:* ]]; then
        api_key="${2#X-BLT-API-Key: }"
      fi
      shift 2
      ;;
    -sS)
      shift
      ;;
    -w)
      shift 2
      ;;
    *)
      url="$1"
      shift
      ;;
  esac
done

if [[ "$url" == */health ]]; then
  printf '{"status":"healthy"}' > "$output_file"
  printf '200'
elif [[ -z "$api_key" ]]; then
  printf '{"message":"Missing API key"}' > "$output_file"
  printf '401'
elif [[ "$api_key" == "__PUBLIC_BLT_API_KEY__" ]]; then
  printf '{"success":true}' > "$output_file"
  printf '200'
else
  printf '{"message":"Invalid API key"}' > "$output_file"
  printf '401'
fi
""".replace("__PUBLIC_BLT_API_KEY__", PUBLIC_BLT_API_KEY)
    fake_curl.write_text(fake_curl_source, encoding="utf-8")
    fake_curl.chmod(0o755)

    env = {
        **os.environ,
        "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
        "BASE_URL": "http://localhost:8787",
    }
    env.pop("BLT_API_KEY", None)
    env.pop("API_KEY", None)
    env.pop("API_KEY_ENV_FILE", None)

    result = subprocess.run(
        ["bash", "scripts/test_static_api_key.sh"],
        cwd=Path(__file__).resolve().parent.parent,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert f"API key: {PUBLIC_BLT_API_KEY}" in result.stdout
    assert "FAIL" not in result.stdout
    assert result.stdout.count("PASS expected HTTP") == 4
