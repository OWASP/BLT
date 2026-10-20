import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const page = readFileSync(new URL("../progress-tracker.html", import.meta.url), "utf8");

test("contributor fields are escaped or URL-encoded", () => {
  const esc = new Function(`${page.match(/function esc\(value\) \{[\s\S]*?\n        \}/)[0]}\nreturn esc;`)();
  assert.equal(esc(`<b a="1">'`), "&lt;b a=&quot;1&quot;&gt;&#39;");
  const raw = page.match(/\$\{c\.(name|github|gitlab|project|repo)\}/g) || [];
  assert.deepEqual(raw, []);
});
