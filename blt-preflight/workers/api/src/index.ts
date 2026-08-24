import { handleGitLabWebhook } from "./pipeline/webhook";
import type { D1Like } from "./pipeline/store";

export interface Env {
  ENVIRONMENT?: string;
  GITLAB_WEBHOOK_SECRET?: string;
  DB: D1Like;
}

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data, null, 2), {
    status,
    headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
  });
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const path = new URL(request.url).pathname;
    const ctx = { db: env.DB, secret: env.GITLAB_WEBHOOK_SECRET };

    if (path === "/health" || path === "/healthz") {
      return json({
        status: "ok",
        service: "blt-preflight-api",
        phase: 2,
        environment: env.ENVIRONMENT ?? "unknown",
        secretConfigured: Boolean(env.GITLAB_WEBHOOK_SECRET?.trim()),
        d1Bound: Boolean(env.DB),
      });
    }

    if (path === "/" || path === "") {
      return json({
        name: "BLT Preflight API",
        version: "0.2.1",
        endpoints: { health: "GET /health", webhook: "POST /webhooks/gitlab" },
      });
    }

    if (path === "/webhooks/gitlab" || path === "/api/webhooks/gitlab") {
      const result = await handleGitLabWebhook(request, ctx);
      return json(result.body, result.status);
    }

    return json({ error: "Not found", path }, 404);
  },
};