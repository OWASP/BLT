// Open and update pull requests on the BLT forge (git.owaspblt.org) as the Renovate bot.
//
// ForkMesh has no Gitea/GitHub-style API, so Renovate cannot open pull requests itself. A forge pull
// request is a signed patch: title, base, head, the diff (`patch`) and a `git format-patch` series
// (`commits`), signed with Ed25519 the way app/src/events.py verify_pull_event checks it, and posted to
// the repository's public pull inbox (POST /api/repo/<owner>/<repo>/pulls), as the web client does
// (dashboard 03-issues-profile-io.js signWebPullContent / submitWebPullRevision). A later change to the
// same pull request goes in as a revision, which only the key that opened it may send.
//
// The key comes from the seed in the BLT_RENOVATE_SEED secret (32 bytes, base64url or 64 hex). Its
// public key is the pull request's author; the forge shows the claimed name until the key is
// registered to an account (docs/renovate.md).
import { createHash, createPrivateKey, createPublicKey, sign as edSign } from "node:crypto";
import { parseFrontMatter } from "../../blt-action/forge/stale.mjs";
import { parseSeed } from "../../blt-action/forge/assign.mjs";

export const FORGE_URL = "https://git.owaspblt.org";
export const OWNER = "owasp-blt";
export const REPO = "BLT";
export const PULL_LEDGER = "forkmesh/pulls";
export const BOT_NAME = "blt-renovate";
const SIGNING_REPO = `${OWNER}/${REPO}`.toLowerCase();
const PKCS8_ED25519 = Buffer.from("302e020100300506032b657004220420", "hex");
const BLOB_BATCH = 50;
const NUL = "\u0000";

const sha256 = (text) => createHash("sha256").update(text, "utf8").digest("hex");

export function makePullSigner(seedText, { authorName = BOT_NAME } = {}) {
  const key = createPrivateKey({ key: Buffer.concat([PKCS8_ED25519, parseSeed(seedText)]), format: "der", type: "pkcs8" });
  const author = createPublicKey(key).export({ format: "jwk" }).x;
  const signText = (kind, body) =>
    edSign(null, Buffer.from(`forkmesh-${kind}-v2\n${SIGNING_REPO}\n${body}`, "utf8"), key).toString("base64url");
  return {
    author,
    authorName,
    /** A new pull request, as signWebPullContent builds it. `ts` is in seconds. */
    pull({ title, description = "", base, head, patch, commits = "", aiModel = "None", baseOid = "", ts }) {
      const content = [title, base, head, patch, commits].join(NUL);
      const sig = signText("pull-event", `${author}\n${ts}\n${sha256(content)}`);
      const pull = { title, description, base, head, patch, commits, author, authorName, ts, sig, aiModel };
      if (baseOid) pull.creationBaseOid = baseOid;
      return pull;
    },
    /** A revision of pull request `number`, as submitWebPullRevision builds it. */
    revision(number, fields) {
      const { description: _ignored, ...revision } = this.pull(fields);
      revision.revisionSig = signText("pull-revision", `${Number(number)}\n${revision.author}\n${revision.ts}\n${revision.sig}`);
      return revision;
    },
  };
}

function blobText(blob) {
  if (blob == null) return "";
  if (typeof blob === "string") return blob;
  const content = blob.content ?? blob.text ?? "";
  return blob.encoding === "base64" ? Buffer.from(content, "base64").toString("utf8") : content;
}

/** The pull.md text after its front matter. */
export function pullBody(text) {
  const lines = String(text ?? "").split("\n");
  if (lines[0]?.trim() !== "---") return "";
  const end = lines.findIndex((line, i) => i > 0 && line.trim() === "---");
  return end < 0 ? "" : lines.slice(end + 1).join("\n");
}

/**
 * Pull requests signed by `author` (a public key) from the forkmesh/pulls ledger, as
 * [{number, head, status, body}]. `getJson(url)` returns {status, data}. No ledger yet means none.
 */
export async function readBotPulls(getJson, author, { url = FORGE_URL } = {}) {
  const api = `${url.replace(/\/+$/, "")}/api/repo/${OWNER}/${REPO}`;
  const get = async (op, params) => {
    const { status, data } = await getJson(`${api}/${op}?${new URLSearchParams(params)}`);
    if (status === 404) return null;
    if (status >= 400 || !data || typeof data !== "object") throw new Error(`forge ${op} answered ${status}`);
    return data;
  };
  const tree = await get("tree", [["path", ".forkmesh/pulls"], ["ref", PULL_LEDGER]]);
  if (!tree) return [];
  const numbers = (tree.entries || []).filter((e) => e?.type === "tree" && /^\d+$/.test(String(e.name))).map((e) => String(e.name));
  const pulls = [];
  for (let i = 0; i < numbers.length; i += BLOB_BATCH) {
    const chunk = numbers.slice(i, i + BLOB_BATCH);
    const paths = chunk.map((n) => `.forkmesh/pulls/${n}/pull.md`);
    const data = await get("blobs", [...paths.map((p) => ["path", p]), ["ref", PULL_LEDGER]]);
    chunk.forEach((n, j) => {
      const text = blobText(data?.blobs?.[paths[j]]);
      const meta = parseFrontMatter(text);
      if (meta.author !== author) return;
      pulls.push({ number: Number(n), head: meta.head || "", status: String(meta.status || "open").toLowerCase(), body: pullBody(text) });
    });
  }
  return pulls.sort((a, b) => a.number - b.number);
}

/** POST a new pull ({pull}) or a revision ({number, revision}) to the forge's pull inbox. */
export async function submit(payload, { url = FORGE_URL, fetchImpl = fetch } = {}) {
  const response = await fetchImpl(`${url.replace(/\/+$/, "")}/api/repo/${OWNER}/${REPO}/pulls`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ owner: OWNER, repo: REPO, ...payload }),
  });
  const text = await response.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = null;
  }
  if (!response.ok) throw new Error(`pull inbox answered HTTP ${response.status}: ${text.slice(0, 200)}`);
  return data || {};
}
