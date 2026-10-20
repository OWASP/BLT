import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import test from "node:test";

const here = new URL("..", import.meta.url).pathname;
const generated = execFileSync(
  "python3",
  ["-c", "import sys; sys.path.insert(0, '.'); import generate_repo_list as g; print(g.generate_html([], 'OWASP'))"],
  { cwd: here, encoding: "utf8" },
);
const committed = readFileSync(new URL("../public/index.html", import.meta.url), "utf8");

function helpers(page) {
  const pick = (name) => page.match(new RegExp(`function ${name}\\([^)]*\\) \\{[\\s\\S]*?\\n        \\}`))[0];
  return new Function(`${pick("escapeHtml")}\n${pick("safeUrl")}\nreturn { escapeHtml, safeUrl };`)();
}

for (const [label, page] of [["generated", generated], ["committed public/index.html", committed]]) {
  test(`${label}: escapeHtml is quote-safe and links are http(s) only`, () => {
    const { escapeHtml, safeUrl } = helpers(page);
    assert.equal(escapeHtml(`fix" onmouseover="alert(1)`), "fix&quot; onmouseover=&quot;alert(1)");
    assert.equal(escapeHtml("it's <b>"), "it&#39;s &lt;b&gt;");
    assert.equal(escapeHtml(0), "0");
    assert.equal(safeUrl("javascript:alert(1)"), "#");
    assert.equal(safeUrl("https://github.com/OWASP/x"), "https://github.com/OWASP/x");
    assert.doesNotMatch(page, /href="\$\{repo\.html_url\}"/);
    assert.doesNotMatch(page, /document\.createElement\('div'\);\s*div\.textContent = text;/);
  });
}
