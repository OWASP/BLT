// Shared helpers for .forkmesh workflow scripts (Node 22, no dependencies).
//
// Reads the event payload from FORKMESH_EVENT_PATH / GITHUB_EVENT_PATH and calls the
// platform job API (FORKMESH_API_URL, Authorization: Bearer $FORKMESH_TOKEN).
// See docs/workflows.md.
import { readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

export const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");

export function readEvent() {
  const file = process.env.FORKMESH_EVENT_PATH || process.env.GITHUB_EVENT_PATH;
  if (!file) return {};
  return JSON.parse(readFileSync(file, "utf8"));
}

export function eventName() {
  return process.env.FORKMESH_EVENT || process.env.GITHUB_EVENT_NAME || "";
}

async function api(method, path, body) {
  const base = (process.env.FORKMESH_API_URL || "").replace(/\/+$/, "");
  const token = process.env.FORKMESH_TOKEN || process.env.GITHUB_TOKEN || "";
  if (!base || !token) throw new Error("FORKMESH_API_URL and FORKMESH_TOKEN are required");
  const response = await fetch(`${base}${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/json",
      ...(body === undefined ? {} : { "Content-Type": "application/json" }),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await response.text();
  if (!response.ok) {
    const error = new Error(`${method} ${path}: HTTP ${response.status} ${text.slice(0, 200)}`);
    error.status = response.status;
    try {
      error.body = text ? JSON.parse(text) : null;
    } catch {
      error.body = null;
    }
    throw error;
  }
  return text ? JSON.parse(text) : null;
}

const issuePath = (n) => `/api/actions/job/issues/${Number(n)}`;

export const getIssue = (n) => api("GET", issuePath(n));
export const comment = (n, body) => api("POST", `${issuePath(n)}/comments`, { body });
export const changeLabels = (n, { add = [], remove = [] } = {}) =>
  api("POST", `${issuePath(n)}/labels`, { add, remove });
export const changeAssignees = (n, { add = [], remove = [] } = {}) =>
  api("POST", `${issuePath(n)}/assignees`, { add, remove });
export const setState = (n, state) => api("POST", `${issuePath(n)}/state`, { state });
export const closeIssue = (n) => setState(n, "closed");
export const createIssue = ({ title, body = "", labels = [] }) =>
  api("POST", "/api/actions/job/issues", { title, body, labels });

/** True when a job API error says the route does not exist (an instance older than the endpoint). */
export const missingEndpoint = (error) => error?.status === 404 && error?.body?.error === "not_found";

/** Label names from either [{name}] (event payload) or ["name"] (job API). */
export function labelNames(issue) {
  return (issue?.labels || []).map((l) => (typeof l === "string" ? l : l?.name)).filter(Boolean);
}

/** Login of the issue author from the event payload ({user:{login}}) or the job API ({author}). */
export function authorLogin(issue) {
  const a = issue?.user?.login ?? issue?.author;
  return typeof a === "string" ? a : a?.login || a?.username || a?.name || "";
}

/** Web address of the repository on the instance, e.g. https://git.example.org/BLT/BLT. */
export function repoUrl() {
  const base = (process.env.FORKMESH_API_URL || "").replace(/\/+$/, "");
  return `${base}/${process.env.GITHUB_REPOSITORY || ""}`;
}

export const issueUrl = (n) => `${repoUrl()}/issues/${n}`;

/**
 * Commit `paths` (relative to `cwd`) and push them to `branch` through
 * scripts/actions/commit-back.sh. `rebuild` (a fixed command) regenerates the paths on the new
 * origin/<branch> when the push is refused, instead of rebasing with -X theirs.
 * Returns true when a commit was pushed.
 */
export function commitBack({ cwd = process.cwd(), message, paths, branch = "main", deploy = "", rebuild = "" }) {
  const args = ["-m", message, "-b", branch];
  if (deploy) args.push("--deploy", deploy);
  if (rebuild) args.push("--rebuild", rebuild);
  const before = git(cwd, ["rev-parse", "HEAD"]);
  const result = spawnSync(join(ROOT, "scripts", "actions", "commit-back.sh"), [...args, "--", ...paths], {
    cwd,
    stdio: "inherit",
  });
  if (result.status !== 0) throw new Error(`commit-back.sh failed (exit ${result.status})`);
  return git(cwd, ["rev-parse", "HEAD"]) !== before;
}

function git(cwd, args) {
  return spawnSync("git", args, { cwd, encoding: "utf8" }).stdout.trim();
}

/** Run `main`, printing the error and exiting 1 on failure. */
export function run(main) {
  main().catch((error) => {
    console.error(error?.stack || String(error));
    process.exit(1);
  });
}
