import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const src = readFileSync(new URL("../public/js/main.js", import.meta.url), "utf8");
const methods = src.match(/    escapeHtml\(text\) \{[\s\S]*?\n    escapeAttribute\(text\) \{[\s\S]*?\n    \}/)[0];
const Helpers = new Function(`return class { ${methods} };`)();
const h = new Helpers();

test("main.js escape helpers escape quotes for attribute use", () => {
  assert.equal(h.escapeHtml(`a" onmouseover="b'`), "a&quot; onmouseover=&quot;b&#39;");
  assert.equal(h.escapeAttribute("`x`<"), "&#96;x&#96;&lt;");
  assert.equal(h.escapeHtml(null), "");
});
