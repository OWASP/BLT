import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const script = readFileSync(new URL("../public/script.js", import.meta.url), "utf8");
const fn = (name) => script.match(new RegExp(`function ${name}\\([^)]*\\) \\{[\\s\\S]*?\\n\\}`))[0];
const { esc, safeUrl } = new Function(`${fn("esc")}\n${fn("safeUrl")}\nreturn { esc, safeUrl };`)();

test("esc and safeUrl neutralise scraped Marketplace values", () => {
  assert.equal(esc(`<img src=x onerror="a('1')">`), "&lt;img src=x onerror=&quot;a(&#39;1&#39;)&quot;&gt;");
  assert.equal(safeUrl("javascript:alert(1)"), "#");
  assert.equal(safeUrl(" https://slack.com/apps/x "), "https://slack.com/apps/x");
});

test("every app field is escaped where it is interpolated", () => {
  assert.doesNotMatch(script, /\$\{app\.[a-z_]+\}/);
  assert.doesNotMatch(script, /href="\$\{(?!esc\(safeUrl\()/);
});
