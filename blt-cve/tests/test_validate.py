"""Unit tests for validate_cves.py and build_index.py."""

import copy
import json
import pathlib
import sys
import tempfile
import unittest

SCRIPTS_DIR = pathlib.Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import build_index
import validate_cves

VALID_ENTRY = {
    "id": "BLT-2026-0001",
    "published": "2026-02-22T00:00:00Z",
    "modified": "2026-02-22T00:00:00Z",
    "title": "Example SQL Injection in ExampleApp Login Endpoint",
    "description": "An unauthenticated SQL injection vulnerability exists in the login endpoint of ExampleApp.",
    "affected": [
        {
            "vendor": "ExampleCorp",
            "product": "ExampleApp",
            "versions": "1.0.0 through 1.2.3",
        }
    ],
    "severity": {
        "cvss_score": 9.8,
        "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
    },
    "references": [
        "https://example.com/advisory/2026-001",
    ],
    "reporter": "blt-community",
}


def write_cve(cves_dir, year, filename, data):
    year_dir = pathlib.Path(cves_dir) / str(year)
    year_dir.mkdir(parents=True, exist_ok=True)
    filepath = year_dir / filename
    if isinstance(data, (dict, list)):
        filepath.write_text(json.dumps(data), encoding="utf-8")
    else:
        filepath.write_text(str(data), encoding="utf-8")
    return filepath


class TestValidateCVEs(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.cves_dir = self.tmpdir.name

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_valid_entry(self):
        write_cve(self.cves_dir, 2026, "BLT-2026-0001.json", VALID_ENTRY)
        errors = validate_cves.validate(cves_dir=self.cves_dir)
        self.assertEqual(errors, [])

    def test_invalid_json(self):
        write_cve(self.cves_dir, 2026, "BLT-2026-0001.json", "{ invalid json ")
        errors = validate_cves.validate(cves_dir=self.cves_dir)
        self.assertEqual(len(errors), 1)
        self.assertIn("invalid JSON", errors[0])

    def test_schema_error(self):
        entry = copy.deepcopy(VALID_ENTRY)
        del entry["description"]  # required field
        write_cve(self.cves_dir, 2026, "BLT-2026-0001.json", entry)
        errors = validate_cves.validate(cves_dir=self.cves_dir)
        self.assertTrue(any("schema error" in e for e in errors))

    def test_id_filename_mismatch(self):
        entry = copy.deepcopy(VALID_ENTRY)
        entry["id"] = "BLT-2026-0002"
        write_cve(self.cves_dir, 2026, "BLT-2026-0001.json", entry)
        errors = validate_cves.validate(cves_dir=self.cves_dir)
        self.assertTrue(any("does not match filename" in e for e in errors))

    def test_id_pattern_mismatch(self):
        entry = copy.deepcopy(VALID_ENTRY)
        entry["id"] = "INVALID-ID"
        write_cve(self.cves_dir, 2026, "INVALID-ID.json", entry)
        errors = validate_cves.validate(cves_dir=self.cves_dir)
        self.assertTrue(any("does not match BLT-YYYY-NNNN pattern" in e for e in errors))

    def test_year_folder_mismatch(self):
        write_cve(self.cves_dir, 2025, "BLT-2026-0001.json", VALID_ENTRY)
        errors = validate_cves.validate(cves_dir=self.cves_dir)
        self.assertTrue(any("does not match folder year" in e for e in errors))

    def test_duplicate_id(self):
        write_cve(self.cves_dir, 2026, "BLT-2026-0001.json", VALID_ENTRY)
        entry2 = copy.deepcopy(VALID_ENTRY)
        # Even if in different folder or file, duplicate ID must be caught
        write_cve(self.cves_dir, 2027, "BLT-2026-0001.json", entry2)
        errors = validate_cves.validate(cves_dir=self.cves_dir)
        self.assertTrue(any("duplicate ID" in e for e in errors))

    def test_empty_or_nonexistent_directory(self):
        self.assertEqual(validate_cves.validate(cves_dir=self.cves_dir), [])
        non_existent = pathlib.Path(self.cves_dir) / "does_not_exist"
        self.assertEqual(validate_cves.validate(cves_dir=str(non_existent)), [])
        self.assertEqual(list(validate_cves.collect_cve_files(cves_dir=str(non_existent))), [])


class TestBuildIndex(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.cves_dir = self.tmpdir.name

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_collect_entries(self):
        e1 = copy.deepcopy(VALID_ENTRY)
        e1["id"] = "BLT-2026-0002"
        e2 = copy.deepcopy(VALID_ENTRY)
        e2["id"] = "BLT-2026-0001"
        write_cve(self.cves_dir, 2026, "BLT-2026-0002.json", e1)
        write_cve(self.cves_dir, 2026, "BLT-2026-0001.json", e2)
        # Non-json file should be ignored
        (pathlib.Path(self.cves_dir) / "2026" / "ignore.txt").write_text("skip", encoding="utf-8")
        # Regular file in cves_dir root should be ignored
        (pathlib.Path(self.cves_dir) / "file.json").write_text("{}", encoding="utf-8")

        entries = build_index.collect_entries(cves_dir=self.cves_dir)
        self.assertEqual(len(entries), 2)
        # Check sorted by ID
        self.assertEqual(entries[0][0], "BLT-2026-0001")
        self.assertEqual(entries[1][0], "BLT-2026-0002")

    def test_collect_entries_invalid_json(self):
        write_cve(self.cves_dir, 2026, "BLT-2026-0001.json", "{ bad json")
        entries = build_index.collect_entries(cves_dir=self.cves_dir)
        self.assertEqual(entries, [])

    def test_collect_entries_nonexistent_dir(self):
        entries = build_index.collect_entries(cves_dir="/nonexistent/dir")
        self.assertEqual(entries, [])

    def test_null_severity_does_not_crash(self):
        entry = copy.deepcopy(VALID_ENTRY)
        entry["severity"] = None
        entries = [("BLT-2026-0001", "/cves/2026/BLT-2026-0001.json", entry)]
        now = "2026-02-22T00:00:00Z"

        idx = build_index.build_index(entries, now)
        feed = build_index.build_feed(entries, now)

        self.assertIsNone(idx["entries"][0]["severity"])
        self.assertIsNone(feed["items"][0]["severity"])

    def test_missing_severity_does_not_crash(self):
        entry = copy.deepcopy(VALID_ENTRY)
        del entry["severity"]
        entries = [("BLT-2026-0001", "/cves/2026/BLT-2026-0001.json", entry)]
        now = "2026-02-22T00:00:00Z"

        idx = build_index.build_index(entries, now)
        feed = build_index.build_feed(entries, now)

        self.assertIsNone(idx["entries"][0]["severity"])
        self.assertIsNone(feed["items"][0]["severity"])

    def test_valid_severity(self):
        entries = [("BLT-2026-0001", "/cves/2026/BLT-2026-0001.json", VALID_ENTRY)]
        now = "2026-02-22T00:00:00Z"

        idx = build_index.build_index(entries, now)
        feed = build_index.build_feed(entries, now)

        self.assertEqual(idx["entries"][0]["severity"], 9.8)
        self.assertEqual(feed["items"][0]["severity"], 9.8)


if __name__ == "__main__":
    unittest.main()
