/**
 * BLT Preflight — API Worker
 *
 * Entry point for HTTP requests.
 * Phase 1: Health check + basic routing skeleton only.
 * No authentication, no GitLab, no analysis yet.
 */

export interface Env {
    ENVIRONMENT: string;
    // Future bindings (will be added in later phases):
    // DB: D1Database;
    // ANALYSIS_QUEUE: Queue;
    // CACHE: KVNamespace;
    // GITLAB_WEBHOOK_SECRET: string;
    // GITLAB_TOKEN: string;
    // LLM_API_KEY: string;
  }
  
  export default {
    async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
      const url = new URL(request.url);
      const path = url.pathname;
  
      // --- Health check (public) ---
      if (path === "/health" || path === "/healthz") {
        return json({
          status: "ok",
          service: "blt-preflight-api",
          environment: env.ENVIRONMENT,
          timestamp: new Date().toISOString(),
          phase: 1,
        });
      }
  
      // --- Root ---
      if (path === "/" || path === "") {
        return json({
          name: "BLT Preflight API",
          description: "AI-powered security review system for GitLab Merge Requests",
          version: "0.1.0",
          phase: 1,
          endpoints: {
            health: "GET /health",
          },
          note: "Backend scaffolding only. No analysis, auth, or GitLab integration yet.",
        });
      }
  
      // --- Placeholder routes (will be implemented in later phases) ---
      if (path.startsWith("/webhooks/")) {
        return json(
          {
            error: "Not implemented",
            message: "GitLab webhook receiver will be added in Phase 2",
          },
          501
        );
      }
  
      if (path.startsWith("/api/maintainer/")) {
        return json(
          {
            error: "Not implemented",
            message: "Maintainer APIs require authentication and authorization (Phase 5+)",
          },
          501
        );
      }
  
      // --- 404 ---
      return json(
        {
          error: "Not found",
          path,
        },
        404
      );
    },
  };
  
  function json(data: unknown, status = 200): Response {
    return new Response(JSON.stringify(data, null, 2), {
      status,
      headers: {
        "Content-Type": "application/json",
        "Cache-Control": "no-store",
      },
    });
  }