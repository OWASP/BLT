// Every project logo, homepage Explore copy and site copy matches what the badge generator makes.
import { test } from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));

test("wasp badge logos are up to date (run scripts/wasp-badges/build.mjs)", () => {
  const r = spawnSync(process.execPath, [join(here, "..", "scripts", "wasp-badges", "build.mjs"), "--check"], { encoding: "utf8" });
  assert.equal(r.status, 0, r.stderr);
});
