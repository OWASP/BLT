/**
 * BLT Preflight API Worker — GitLab webhook (Phase 2)
 * Overlay onto gitlab.com/owasp-blt/blt-preflight  workers/api/
 */
import { handleGitLabWebhook, setWebhookSecret } from "./pipeline/webhook";

export interface Env {
  ENVIRONMENT?: string;
  GITLAB_WEBHOOK_SECRET: string;
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
    if (env.GITLAB_WEBHOOK_SECRET) setWebhookSecret(env.GITLAB_WEBHOOK_SECRET);

    if (path === "/health" || path === "/healthz") {
      return json({
        status: "ok",
        service: "blt-preflight-api",
        phase: 2,
        environment: env.ENVIRONMENT ?? "unknown",
      });
    }

    if (path === "/" || path === "") {
      return json({
        name: "BLT Preflight API",
        version: "0.2.0",
        phase: 2,
        endpoints: { health: "GET /health", webhook: "POST /webhooks/gitlab" },
      });
    }

    if (path === "/webhooks/gitlab" || path === "/api/webhooks/gitlab") {
      const result = await handleGitLabWebhook(request);
      return json(result.body, result.status);
    }

    return json({ error: "Not found", path }, 404);
  },
};
