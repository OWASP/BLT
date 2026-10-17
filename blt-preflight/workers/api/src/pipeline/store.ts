import type { Advisory, PipelineStep } from "./types";

const MAX = 80;

interface WebhookLog {
  id: string;
  at: string;
  status: number;
  event: string;
  project?: string;
  mrIid?: number;
  detail: string;
}

const advisories: Advisory[] = [];
const logs: WebhookLog[] = [];

export function rememberAdvisory(advisory: Advisory) {
  const idx = advisories.findIndex(
    (a) => a.projectId === advisory.projectId && a.mrIid === advisory.mrIid,
  );
  if (idx >= 0) advisories.splice(idx, 1);
  advisories.unshift(advisory);
  if (advisories.length > MAX) advisories.pop();
}

export function listAdvisories(): Advisory[] {
  return advisories;
}

export function getAdvisory(id: string): Advisory | undefined {
  return advisories.find((a) => a.id === id);
}

export function updateAdvisoryStatus(id: string, status: Advisory["status"]): Advisory | undefined {
  const a = getAdvisory(id);
  if (!a) return undefined;
  a.status = status;
  a.updatedAt = new Date().toISOString();
  return a;
}

export function logWebhook(entry: Omit<WebhookLog, "id" | "at"> & { id?: string }) {
  logs.unshift({
    id: entry.id ?? `log-${Date.now().toString(36)}`,
    at: new Date().toISOString(),
    status: entry.status,
    event: entry.event,
    project: entry.project,
    mrIid: entry.mrIid,
    detail: entry.detail,
  });
  if (logs.length > 60) logs.pop();
}

export function listLogs(): WebhookLog[] {
  return logs;
}

export function metrics() {
  const open = advisories.filter((a) => a.status === "open");
  const critical = open.filter((a) => a.severity === "CRITICAL" || a.severity === "HIGH").length;
  const conf =
    open.length === 0 ? 0 : Math.round(open.reduce((s, a) => s + a.confidence, 0) / open.length);
  return {
    openMrs: new Set(open.map((a) => `${a.projectId}:${a.mrIid}`)).size,
    advisories: advisories.length,
    critical,
    avgConfidence: conf,
    logs: logs.length,
  };
}

export function seedIfEmpty(seed: Advisory[]) {
  if (advisories.length === 0) {
    for (const a of seed) advisories.push(a);
  }
}

export function step(
  id: PipelineStep["id"],
  label: string,
  status: PipelineStep["status"],
  detail?: string,
  started?: number,
): PipelineStep {
  return {
    id,
    label,
    status,
    detail,
    at: new Date().toISOString(),
    ms: started !== undefined ? Date.now() - started : undefined,
  };
}
