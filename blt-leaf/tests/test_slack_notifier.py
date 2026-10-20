"""slack_notifier escapes visitor text before it reaches Slack mrkdwn."""

import asyncio
import json
import pathlib
import sys
import types
import unittest

SRC = pathlib.Path(__file__).resolve().parent.parent / "src"


def load_notifier(sent):
    js = types.ModuleType("js")

    async def fetch(url, options):
        sent.append(json.loads(options["body"]))
        return types.SimpleNamespace(ok=True, status=200)

    js.fetch = fetch
    js.Object = types.SimpleNamespace(fromEntries=dict)
    ffi = types.ModuleType("pyodide.ffi")
    ffi.to_js = lambda value, **kw: value
    pyodide = types.ModuleType("pyodide")
    pyodide.ffi = ffi
    sys.modules.update({"js": js, "pyodide": pyodide, "pyodide.ffi": ffi})
    import importlib.util

    spec = importlib.util.spec_from_file_location("slack_notifier_under_test", SRC / "slack_notifier.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SlackEscapeTest(unittest.TestCase):
    def test_links_and_mentions_are_inert(self):
        sent = []
        notifier = load_notifier(sent)
        ok = asyncio.run(
            notifier.notify_slack_error(
                "https://hooks.slack.com/services/x",
                error_type="<!channel>",
                error_message="see <https://evil.example|your account>",
                context={"<@U123>": "<!here> " + "x" * 500, **{f"k{i}": i for i in range(30)}},
                stack_trace="```\n<https://evil.example|x>",
            )
        )
        self.assertTrue(ok)
        text = sent[0]["text"]
        self.assertNotIn("<", text)
        self.assertNotIn(">", text.replace("&gt;", ""))
        self.assertIn("&lt;!channel&gt;", text)
        self.assertLessEqual(text.count("• "), notifier.MAX_CONTEXT_FIELDS)
        self.assertEqual(text.count("```"), 2)
        self.assertNotIn("x" * 201, text)


if __name__ == "__main__":
    unittest.main()
