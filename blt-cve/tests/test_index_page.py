"""public/index.html escapes registry entries before inserting them as HTML."""

import pathlib
import re
import shutil
import subprocess
import tempfile
import unittest

PAGE = pathlib.Path(__file__).resolve().parents[1] / "public" / "index.html"


class IndexPageTest(unittest.TestCase):
    def test_entries_are_escaped(self):
        page = PAGE.read_text()
        self.assertNotIn("${item.title", page)
        self.assertNotIn(">${item.id}<", page)
        self.assertIn("escHtml(item.title", page)
        self.assertIn("escHtml(item.id)", page)

    @unittest.skipIf(shutil.which("node") is None, "node not installed")
    def test_inline_script_parses(self):
        scripts = re.findall(r"<script(?![^>]*src)[^>]*>([\s\S]*?)</script>", PAGE.read_text())
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
            f.write("\n;\n".join(scripts))
        result = subprocess.run(["node", "--check", f.name], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
