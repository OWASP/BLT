import type { ExtractedSignals, GitLabMergeRequestEvent } from "./types";

const AUTH_FILES = /(auth|login|session|password|oauth|sso|jwt|mfa)/i;
const DB_FILES = /(db|database|sql|migration|query|model|schema)/i;
const API_FILES = /(api|route|endpoint|controller|handler|graphql)/i;
const SECRET_FILES = /(\.env|secret|credential|apikey|api-key|private.?key|id_rsa)/i;
const CRYPTO_FILES = /(crypto|encrypt|hash|cipher|tls|ssl)/i;
const DOC_FILES = /\.(md|mdx|rst|txt)$/i;

export function extractSignals(event: GitLabMergeRequestEvent): ExtractedSignals {
  const attrs = event.object_attributes;
  const labels = (event.labels ?? []).map((l) => l.title).filter(Boolean);
  const files = inferChangedFiles(event);
  const commitMessage = attrs.last_commit?.message ?? attrs.last_commit?.title ?? "";
  const blob = `${attrs.title} ${attrs.description ?? ""} ${commitMessage} ${files.join(" ")} ${labels.join(" ")}`;
  const keywords = unique(
    blob
      .toLowerCase()
      .match(
        /auth|login|password|session|token|secret|sql|inject|api|endpoint|encrypt|oauth|jwt|mfa|cors|xss/g,
      ) ?? [],
  );

  return {
    projectId: event.project.id,
    projectPath: event.project.path_with_namespace,
    mrIid: attrs.iid,
    title: attrs.title,
    description: attrs.description ?? "",
    action: attrs.action,
    state: attrs.state,
    sourceBranch: attrs.source_branch,
    targetBranch: attrs.target_branch,
    labels,
    changedFiles: files,
    commitMessage,
    keywords,
  };
}

function inferChangedFiles(event: GitLabMergeRequestEvent): string[] {
  if (event.changed_files?.length) return unique(event.changed_files);
  const fromChanges: string[] = [];
  const changes = event.changes ?? {};
  for (const key of Object.keys(changes)) {
    if (key.includes("/") || key.includes(".")) fromChanges.push(key);
  }
  const desc = event.object_attributes.description ?? "";
  const listed = [...desc.matchAll(/`([^`]+\.[a-zA-Z0-9]+)`/g)].map((m) => m[1]);
  return unique([...fromChanges, ...listed]);
}

export function classifyFiles(files: string[]) {
  const flags = {
    auth: files.some((f) => AUTH_FILES.test(f)),
    database: files.some((f) => DB_FILES.test(f)),
    api: files.some((f) => API_FILES.test(f)),
    secret: files.some((f) => SECRET_FILES.test(f)),
    crypto: files.some((f) => CRYPTO_FILES.test(f)),
    docsOnly: files.length > 0 && files.every((f) => DOC_FILES.test(f)),
  };
  return flags;
}

function unique(arr: string[]): string[] {
  return [...new Set(arr)];
}
