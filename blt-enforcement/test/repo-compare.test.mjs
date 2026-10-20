import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const page = readFileSync(new URL("../public/repo-compare.html", import.meta.url), "utf8");
const pick = (name) => page.match(new RegExp(`function ${name}\\([^)]*\\) \\{[\\s\\S]*?\\n    \\}`))[0];
const { esc, safeUrl } = new Function(`${pick("esc")}\n${pick("safeUrl")}\nreturn { esc, safeUrl };`)();

test("GitHub API values are escaped before innerHTML", () => {
  assert.equal(esc(`<img src=x onerror="alert('1')">`), "&lt;img src=x onerror=&quot;alert(&#39;1&#39;)&quot;&gt;");
  assert.equal(safeUrl("javascript:alert(1)"), "#");
  assert.equal(safeUrl("https://github.com/a/b"), "https://github.com/a/b");
  for (const raw of ["${r.description", ">${r.full_name}<", 'href="${r.html_url}"', ">${f}<", "${dataA.info.full_name}", "${r.language"]) {
    assert.ok(!page.includes(raw), `raw interpolation left: ${raw}`);
  }
});
