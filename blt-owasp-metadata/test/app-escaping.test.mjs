import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const app = readFileSync(new URL("../public/app.js", import.meta.url), "utf8");
const pick = (name) => app.match(new RegExp(`function ${name}\\([^)]*\\) \\{[\\s\\S]*?\\n\\}`))[0];
const { escapeHtml, formatColumnName } = new Function(
  `${pick("escapeHtml")}\n${pick("formatColumnName")}\nreturn { escapeHtml, formatColumnName };`,
)();

test("column names from front matter are escaped and never built into inline handlers", () => {
  const key = `x') ;alert(1);('"><img src=x onerror=alert(2)>`;
  assert.doesNotMatch(escapeHtml(key), /[<>"']/);
  assert.doesNotMatch(escapeHtml(formatColumnName(key)), /[<>"']/);
  assert.doesNotMatch(app, /onclick=/);
  assert.doesNotMatch(app, /value="\$\{field\}"|data-field="\$\{field\}"|data-column="\$\{col\}"/);
  assert.match(app, /th\.addEventListener\('click'/);
});
