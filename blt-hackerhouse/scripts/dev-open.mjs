#!/usr/bin/env node
// Wraps `uv run pywrangler dev` and opens the landing page once ready.
// Usage: node scripts/dev-open.mjs [wrangler dev args...]

import { spawn } from "node:child_process";
import http from "node:http";

const args = process.argv.slice(2);

function getArg(name, fallback) {
  const i = args.indexOf(name);
  if (i !== -1 && args[i + 1] && !args[i + 1].startsWith("--")) return args[i + 1];
  const eq = args.find((a) => a.startsWith(`${name}=`));
  if (eq) return eq.slice(name.length + 1);
  return fallback;
}

const port = Number(getArg("--port", 8787));
const rawHost = getArg("--ip", "127.0.0.1");
const host = rawHost === "0.0.0.0" ? "127.0.0.1" : rawHost;
const url = `http://${host}:${port}/landing`;

const child = spawn("uv", ["run", "pywrangler", "dev", ...args], {
  stdio: "inherit",
});

let opened = false;
let exited = false;

child.on("exit", (code) => {
  exited = true;
  process.exit(code ?? 0);
});

function openBrowser() {
  if (opened) return;
  opened = true;
  const cmd =
    process.platform === "win32"
      ? `start "" "${url}"`
      : process.platform === "darwin"
        ? `open "${url}"`
        : `xdg-open "${url}"`;
  spawn(process.platform === "win32" ? "cmd" : "sh", ["/c", cmd], { stdio: "ignore" });
  console.log(`\n[dev] Opening ${url}`);
}

function probe() {
  if (exited) return;
  const req = http.get(url, (res) => {
    if (res.statusCode < 500) {
      openBrowser();
    } else {
      setTimeout(probe, 500);
    }
  });
  req.on("error", () => setTimeout(probe, 500));
  req.setTimeout(1000, () => {
    req.destroy();
    setTimeout(probe, 500);
  });
}

probe();
