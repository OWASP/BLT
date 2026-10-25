import json
from pathlib import Path

from brokers import BROKERS


def test_brokers_match_json_data():
    project_root = Path(__file__).resolve().parents[2]
    data_path = project_root / "data" / "brokers" / "brokers.json"

    with data_path.open(encoding="utf-8") as data_file:
        source_brokers = json.load(data_file)

    assert BROKERS == source_brokers
