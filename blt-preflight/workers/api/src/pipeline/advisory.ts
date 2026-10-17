import { retrieveKnowledge } from "./knowledge";
import { classifyFiles } from "./signals";
import { primaryOwasp, scoreSignals } from "./score";
import type { Advisory, ExtractedSignals, KnowledgeChunk, PipelineStep } from "./types";

export function buildAdvisory(
  signals: ExtractedSignals,
  knowledge: KnowledgeChunk[],
  pipeline: PipelineStep[],
  mrUrl?: string,
): Advisory {
  const score = scoreSignals(signals);
  const owasp = primaryOwasp(signals);
  const flags = classifyFiles(signals.changedFiles);
  const now = new Date().toISOString();
  const id = `adv-${signals.projectId}-${signals.mrIid}-${Date.now().toString(36)}`;

  const title = advisoryTitle(flags, signals);
  const explanation = advisoryExplanation(flags, signals, knowledge);
  const recommendations = advisoryRecs(flags);
  const evidence: string[] = [];
  if (signals.changedFiles.length) {
    evidence.push(`Changed files: ${signals.changedFiles.slice(0, 8).join(", ")}`);
  }
  if (signals.labels.length) evidence.push(`Labels: ${signals.labels.join(", ")}`);
  if (signals.keywords.length) evidence.push(`Intent keywords: ${signals.keywords.join(", ")}`);
  if (signals.commitMessage) evidence.push(`Commit: ${signals.commitMessage.split("\n")[0]}`);
  if (!evidence.length) evidence.push("No file list in webhook payload — scored from title, labels, and branch.");

  const confidence = Math.round(
    Math.min(98, 55 + score.raw * 35 + (signals.changedFiles.length ? 8 : 0) + knowledge.length * 2),
  );

  return {
    id,
    projectId: signals.projectId,
    projectPath: signals.projectPath,
    mrIid: signals.mrIid,
    mrTitle: signals.title,
    mrUrl,
    action: signals.action,
    severity: score.severity,
    confidence,
    owaspCategory: owasp,
    title,
    explanation,
    recommendations,
    evidence,
    owaspRefs: knowledge.map((k) => ({ title: `${k.owasp} ${k.title}`, url: k.url })),
    knowledge,
    score,
    signals,
    status: "open",
    pipeline,
    createdAt: now,
    updatedAt: now,
  };
}

export function retrievalQuery(signals: ExtractedSignals): string {
  const flags = classifyFiles(signals.changedFiles);
  const parts = [signals.title, ...signals.labels, ...signals.keywords, ...signals.changedFiles];
  if (flags.auth) parts.push("authentication session login");
  if (flags.api) parts.push("api authorization endpoint");
  if (flags.database) parts.push("sql injection database");
  if (flags.secret) parts.push("secret api key credential");
  if (flags.docsOnly) parts.push("documentation only");
  return parts.join(" ");
}

export function retrieveFor(signals: ExtractedSignals): KnowledgeChunk[] {
  return retrieveKnowledge(retrievalQuery(signals), 3);
}

function advisoryTitle(flags: ReturnType<typeof classifyFiles>, signals: ExtractedSignals): string {
  if (flags.secret) return "Potential secret or credential material in the change set";
  if (flags.auth) return "Authentication or session surface modified";
  if (flags.api) return "New or changed API surface requires access-control review";
  if (flags.database) return "Data-access path changed — injection and authorization risk";
  if (flags.docsOnly) return "Documentation-only change";
  if (signals.labels.some((l) => /security/i.test(l))) return "Security-labeled merge request";
  return "Contributor change — baseline security advisory";
}

function advisoryExplanation(
  flags: ReturnType<typeof classifyFiles>,
  signals: ExtractedSignals,
  knowledge: KnowledgeChunk[],
): string {
  const grounded = knowledge[0]?.text;
  if (flags.secret) {
    return `This MR appears to touch secret-bearing paths. ${grounded ?? "Secrets must not be committed."} Maintainers should confirm no live credentials landed in git history.`;
  }
  if (flags.auth) {
    return `Files matching authentication/session patterns were changed in ${signals.projectPath}!${signals.mrIid}. ${grounded ?? ""} Verify session flags, password handling, and lockout behavior before merge.`;
  }
  if (flags.api) {
    return `API-related files changed. ${grounded ?? "Every new endpoint needs object-level authorization."} Confirm tests cover a different user's identifier.`;
  }
  if (flags.database) {
    return `Database or query files changed. ${grounded ?? "Use parameterized queries."} Review for concatenated SQL and overly broad migrations.`;
  }
  if (flags.docsOnly) {
    return `All listed files look like documentation. Still scan the diff for pasted tokens or internal URLs.`;
  }
  return `Heuristic signals did not map to a high-risk class. Treat this as a baseline check: ${grounded ?? "confirm the change stays outside auth, secrets, and data-access code."}`;
}

function advisoryRecs(flags: ReturnType<typeof classifyFiles>): string[] {
  if (flags.secret) {
    return [
      "Remove secrets from the branch and rotate any exposed credentials",
      "Add the path to .gitignore and secret scanning",
      "Prefer a secrets manager over committed env files",
    ];
  }
  if (flags.auth) {
    return [
      "Confirm password hashing uses Argon2 or bcrypt",
      "Set Secure, HttpOnly, SameSite on session cookies",
      "Rate-limit login and rotate session IDs on privilege change",
    ];
  }
  if (flags.api) {
    return [
      "Enforce authorization on every new route",
      "Add object-level access tests with a second user",
      "Avoid relying on hidden URLs or client-supplied owner fields",
    ];
  }
  if (flags.database) {
    return [
      "Use parameterized queries or ORM bindings",
      "Review migrations for privilege and data exposure",
      "Reject raw string concatenation into SQL",
    ];
  }
  return [
    "Skim the diff for credentials, debug endpoints, and auth bypasses",
    "Keep the change scoped; avoid mixing docs with production config",
  ];
}
