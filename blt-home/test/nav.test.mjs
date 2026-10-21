// The shared top bar (public/_shared/blt-nav.js): per-site config parsing, run in a tiny
// stand-in for the browser (no DOM library needed; only what the script touches at load).
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import vm from "node:vm";

const here = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(here, "..", "public", "_shared", "blt-nav.js"), "utf8");

function load(hostname = "zero.owaspblt.org") {
  let defined = null;
  const node = () => ({ setAttribute() {}, appendChild() {}, style: {} });
  const document = {
    currentScript: { src: "https://owaspblt.org/_shared/blt-nav.js", getAttribute: () => null, hasAttribute: () => false },
    documentElement: { classList: { contains: () => false, toggle() {} }, getAttribute: () => null, setAttribute() {} },
    head: node(),
    body: null,
    cookie: "",
    createElement: node,
    querySelector: () => null,
    addEventListener() {},
  };
  const window = { customElements: null };
  const ctx = {
    window, document, location: { hostname, pathname: "/" }, URL,
    localStorage: { getItem: () => null, setItem() {} },
    HTMLElement: class {},
    customElements: { get: () => undefined, define: (name, cls) => { defined = [name, cls]; } },
  };
  window.customElements = ctx.customElements;
  vm.runInNewContext(src, ctx);
  assert.equal(defined[0], "blt-nav");
  return defined[1];
}
const attrs = (o) => (name) => (name in o ? o[name] : null);

test("blt-nav registers once and exposes its config parser", () => {
  assert.equal(typeof load().resolveConfig, "function");
});

test("explicit config: project slug, short name, home", () => {
  const { resolveConfig } = load("example.test");
  const c = resolveConfig(attrs({ project: "blt-next", name: "Next", home: "/app/" }), "example.test");
  assert.equal(c.project, "blt-next");
  assert.equal(c.name, "Next");
  assert.equal(c.home, "/app/");
  assert.equal(c.symbol, "https://owaspblt.org/_home/symbols/blt-next.svg");
});

test("data- attributes work too; name and home have defaults", () => {
  const { resolveConfig } = load("example.test");
  const c = resolveConfig(attrs({ "data-project": "blt-design-contest" }), "example.test");
  assert.equal(c.project, "blt-design-contest");
  assert.equal(c.name, "Design Contest");
  assert.equal(c.home, "/");
  assert.equal(resolveConfig(attrs({ project: "my-gsoc-tool" }), "x").name, "GSoC Tool");
  assert.equal(resolveConfig(attrs({ project: "blt-autopatch" }), "x").name, "Autopatch");
});

test("un-updated *.owaspblt.org sites get their project from the host name", () => {
  const { resolveConfig } = load();
  assert.deepEqual(
    JSON.parse(JSON.stringify(resolveConfig(attrs({}), "zero.owaspblt.org"))),
    { project: "blt-zero", name: "Zero", home: "/", symbol: "https://owaspblt.org/_home/symbols/blt-zero.svg" },
  );
  assert.equal(resolveConfig(attrs({}), "timer.owaspblt.org").project, "blt-timer-web");
  assert.equal(resolveConfig(attrs({}), "gsoc-tool.owaspblt.org").name, "GSoC Tool");
  assert.equal(resolveConfig(attrs({}), "unknown.example").project, null);
});

test("no project part on owaspblt.org itself, or with project=none", () => {
  const { resolveConfig } = load("owaspblt.org");
  assert.equal(resolveConfig(attrs({}), "owaspblt.org").project, null);
  assert.equal(resolveConfig(attrs({}), "www.owaspblt.org").project, null);
  assert.equal(resolveConfig(attrs({ project: "none" }), "zero.owaspblt.org").project, null);
});

test("unsafe values are ignored", () => {
  const { resolveConfig } = load("example.test");
  assert.equal(resolveConfig(attrs({ project: "../evil" }), "example.test").project, null);
  assert.equal(resolveConfig(attrs({ project: "blt-zero", home: "javascript:alert(1)" }), "x").home, "/");
  assert.equal(resolveConfig(attrs({ project: "blt-zero", home: " JavaScript:alert(1)" }), "x").home, "/");
});

test("every APPS entry has a symbol and resolves from its own host", async () => {
  const { existsSync } = await import("node:fs");
  const { resolveConfig } = load();
  const apps = [...src.matchAll(/^\s*\["([^"]+)", "https:\/\/([^/]+)\/", "([^"]+)\.svg"\],$/gm)];
  assert.ok(apps.length > 40);
  for (const [, , host, slug] of apps) {
    assert.ok(existsSync(join(here, "..", "public", "_home", "symbols", slug + ".svg")), slug);
    assert.equal(resolveConfig(attrs({}), host).project, slug, host);
  }
});

test("the site's own links are slotted light DOM, never copied or parsed as HTML", () => {
  assert.match(src, /el\("slot"\)/);
  assert.match(src, /el\("slot", \{ name: "actions" \}\)/);
  assert.doesNotMatch(src, /innerHTML|outerHTML|insertAdjacentHTML|document\.write|cloneNode/);
  // the site's hidden links stay hidden: the bar never forces display on slotted elements
  for (const m of src.matchAll(/::slotted\([^)]*\)\{[^}]*\}/g)) assert.doesNotMatch(m[0], /display:/, m[0]);
});
