import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const app = readFileSync(new URL("../public/app.js", import.meta.url), "utf8");

test("avatar fallback uses addEventListener, not an inline onerror", () => {
  assert.doesNotMatch(app, /onerror=/i);
  assert.match(app, /img\.addEventListener\("error"/);
  assert.match(app, /attachAvatarFallbacks\(wrapper\);/);
  const fallback = new Function(`${app.match(/function attachAvatarFallbacks\(root\) \{[\s\S]*?\n    \}/)[0]}\nreturn attachAvatarFallbacks;`)();
  const listeners = {};
  const parent = { textContent: "" };
  const img = { dataset: { initials: "<b>AB</b>" }, parentNode: parent, addEventListener: (t, fn) => (listeners[t] = fn) };
  fallback({ querySelectorAll: () => [img] });
  listeners.error();
  assert.equal(parent.textContent, "<b>AB</b>"); // set as text, never parsed as HTML or JS
});
