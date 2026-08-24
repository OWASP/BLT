import { buildAdvisory, retrieveFor } from "./advisory";
import { extractSignals } from "./signals";
import { logWebhook, rememberAdvisory, step } from "./store";
import { timingSafeEqual } from "./timing-safe";
import type { GitLabMergeRequestEvent, PipelineStep, WebhookResult } from "./types";

export const DEMO_WEBHOOK_SECRET = "blt-preflight-dev-secret";

let boundSecret: string | undefined;

export function setWebhookSecret(secret: string) {
  boundSecret = secret;
}

export function webhookSecret(): string {
  if (boundSecret) return boundSecret;
  try {
    const fromEnv = (globalThis as { process?: { env?: { GITLAB_WEBHOOK_SECRET?: string } } }).process
      ?.env?.GITLAB_WEBHOOK_SECRET;
    if (fromEnv) return fromEnv;
  } catch {
    /* Workers without nodejs_compat */
  }
  return DEMO_WEBHOOK_SECRET;
}


export function readGitLabToken(request: Request): string {
  return request.headers.get("X-Gitlab-Token") ?? request.headers.get("x-gitlab-token") ?? "";
}

export function gitlabEventName(request: Request): string {
  return request.headers.get("X-Gitlab-Event") ?? request.headers.get("x-gitlab-event") ?? "";
}

export async function handleGitLabWebhook(request: Request): Promise<{
  status: number;
  body: WebhookResult | { error: string };
}> {
  if (request.method !== "POST") {
    return { status: 405, body: { error: "Method not allowed" } };
  }

  const token = readGitLabToken(request);
  const expected = webhookSecret();
  if (!timingSafeEqual(token, expected)) {
    logWebhook({
      status: 401,
      event: gitlabEventName(request) || "unknown",
      detail: "Rejected: invalid X-Gitlab-Token",
    });
    return {
      status: 401,
      body: { accepted: false, error: "Invalid webhook token", code: "invalid_token" },
    };
  }

  let payload: unknown;
  try {
    payload = await request.json();
  } catch {
    logWebhook({ status: 400, event: "invalid_json", detail: "Body was not JSON" });
    return {
      status: 400,
      body: { accepted: false, error: "Invalid JSON", code: "invalid_json" },
    };
  }

  if (!payload || typeof payload !== "object") {
    return {
      status: 400,
      body: { accepted: false, error: "Missing payload", code: "missing_payload" },
    };
  }

  const event = payload as GitLabMergeRequestEvent;
  const kind = event.object_kind || event.event_type || "";
  const jobId = `job-${Date.now().toString(36)}`;

  if (kind !== "merge_request") {
    logWebhook({
      status: 202,
      event: kind || "other",
      detail: "Skipped non merge_request event",
    });
    return {
      status: 202,
      body: {
        accepted: true,
        skipped: true,
        reason: `Ignored object_kind=${kind || "unknown"}`,
        jobId,
      },
    };
  }

  if (!event.project || !event.object_attributes) {
    return {
      status: 400,
      body: { accepted: false, error: "Malformed merge request payload", code: "missing_payload" },
    };
  }

  if (
    typeof event.project.id !== "number" ||
    typeof event.object_attributes.iid !== "number" ||
    (event.labels !== undefined && !Array.isArray(event.labels)) ||
    (event.changed_files !== undefined && !Array.isArray(event.changed_files))
  ) {
    return {
      status: 400,
      body: { accepted: false, error: "Malformed merge request payload", code: "missing_payload" },
    };
  }

  const pipeline: PipelineStep[] = [];
  const t0 = Date.now();
  pipeline.push(step("received", "Webhook received", "ok", gitlabEventName(request) || "Merge Request Hook", t0));
  pipeline.push(step("token_validated", "X-Gitlab-Token verified", "ok", "constant-time compare"));

  const tParse = Date.now();
  const signals = extractSignals(event);
  pipeline.push(
    step(
      "event_parsed",
      "Merge request parsed",
      "ok",
      `${signals.projectPath}!${signals.mrIid} action=${signals.action}`,
      tParse,
    ),
  );
  pipeline.push(
    step(
      "signals_extracted",
      "Signals extracted",
      "ok",
      `${signals.changedFiles.length} files, ${signals.labels.length} labels, ${signals.keywords.length} keywords`,
    ),
  );

  const expected = resolveWebhookSecret(ctx.secret);
if (!expected) {
  return { status: 503, body: { accepted: false, error: "GITLAB_WEBHOOK_SECRET is not configured", code: "misconfigured" } };
}
  
  const tScore = Date.now();
  const score = scoreSignals(signals);
  pipeline.push(step("heuristic_scored", "Heuristic risk scored", "ok", undefined, tScore));

  const tKnowledge = Date.now();
  const knowledge = retrieveFor(signals);
  
  pipeline.push(
    step(
      "knowledge_retrieved",
      "OWASP corpus retrieved",
      knowledge.length ? "ok" : "skipped",
      knowledge.map((k) => k.owasp).join(", ") || "no chunks above threshold",
      tKnowledge,
    ),
  );

  const advisory = buildAdvisory(signals, knowledge, pipeline, event.object_attributes.url);
  advisory.pipeline = [
    ...pipeline,
    step("advisory_generated", "Structured advisory generated", "ok", advisory.severity),
    step("stored", "Stored for maintainer queue", "ok", advisory.id),
  ];

  rememberAdvisory(advisory);
  logWebhook({
    status: 202,
    event: "merge_request",
    project: signals.projectPath,
    mrIid: signals.mrIid,
    detail: `${advisory.severity} ${advisory.owaspCategory} conf=${advisory.confidence}`,
  });

  return {
    status: 202,
    body: {
      accepted: true,
      jobId,
      advisoryId: advisory.id,
    },
  };
}
