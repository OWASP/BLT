import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const src = readFileSync(new URL("../public/dashboard.js", import.meta.url), "utf8");
const pick = (name) => src.match(new RegExp(`function ${name}\\([^)]*\\) \\{[\\s\\S]*?\\n\\}`))[0];
const { escapeHtml, httpsUrl, renderGitHubStats } = new Function(
  `${pick("escapeHtml")}\n${pick("httpsUrl")}\n${pick("renderGitHubStats")}\nreturn { escapeHtml, httpsUrl, renderGitHubStats };`,
)();

test("contribution titles, bodies and links are escaped", () => {
  const els = {};
  globalThis.document = { getElementById: (id) => (els[id] ??= { textContent: "", innerHTML: "" }) };
  globalThis.formatDate = (d) => String(d);
  renderGitHubStats({
    stats: {},
    contributions: [
      { title: "<img src=x onerror=alert(1)>", description: '"><script>alert(2)</script>', date: "2026", url: "javascript:alert(3)" },
      { title: "ok", description: "ok", date: "2026", url: "https://github.com/a/b/pull/1" },
    ],
  });
  const html = els["contribution-list"].innerHTML;
  assert.doesNotMatch(html, /<img|<script|javascript:/);
  assert.match(html, /href="https:\/\/github\.com\/a\/b\/pull\/1"/);
  assert.equal(httpsUrl('https://x.example/" onclick="y'), "");
  assert.equal(escapeHtml("'"), "&#39;");
});
