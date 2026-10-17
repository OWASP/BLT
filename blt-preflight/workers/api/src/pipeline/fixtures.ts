import type { GitLabMergeRequestEvent } from "./types";

function base(
  over: Partial<GitLabMergeRequestEvent> & {
    object_attributes: GitLabMergeRequestEvent["object_attributes"];
  },
): GitLabMergeRequestEvent {
  return {
    object_kind: "merge_request",
    event_type: "merge_request",
    user: { name: "Ada Contributor", username: "ada" },
    project: {
      id: 42,
      path_with_namespace: "owasp-blt/blt-preflight",
      web_url: "https://git.owaspblt.org/BLT/BLT/tree/main/blt-preflight",
    },
    labels: [],
    ...over,
  };
}

export const FIXTURES: Record<string, { label: string; hint: string; event: GitLabMergeRequestEvent }> = {
  auth: {
    label: "Auth change",
    hint: "Touches login.py + session — expect HIGH / A07",
    event: base({
      labels: [{ title: "security" }, { title: "authentication" }],
      changed_files: ["src/auth/login.py", "src/auth/session.py"],
      object_attributes: {
        iid: 124,
        title: "Harden login flow and session cookies",
        description: "Updates `src/auth/login.py` rate limits.",
        state: "opened",
        action: "open",
        source_branch: "feat/login-lockout",
        target_branch: "main",
        url: "https://gitlab.com/owasp-blt/blt-preflight/-/merge_requests/124",
        last_commit: { message: "add lockout after failed logins" },
      },
    }),
  },
  api: {
    label: "New API endpoint",
    hint: "New REST handler — expect MEDIUM–HIGH / A01",
    event: base({
      labels: [{ title: "enhancement" }],
      changed_files: ["src/api/routes/reports.py", "src/api/handlers.py"],
      object_attributes: {
        iid: 123,
        title: "Add reports API endpoint",
        description: "New GET /api/reports/:id",
        state: "opened",
        action: "open",
        source_branch: "feat/reports-api",
        target_branch: "main",
        url: "https://gitlab.com/owasp-blt/blt-preflight/-/merge_requests/123",
        last_commit: { message: "add reports endpoint" },
      },
    }),
  },
  secrets: {
    label: "Secret exposure",
    hint: ".env committed — expect CRITICAL / A02",
    event: base({
      labels: [{ title: "chore" }],
      changed_files: [".env", "config/secrets.yaml"],
      object_attributes: {
        iid: 118,
        title: "Local env for staging",
        description: "Adds `.env` for convenience",
        state: "opened",
        action: "open",
        source_branch: "chore/env",
        target_branch: "main",
        url: "https://gitlab.com/owasp-blt/blt-preflight/-/merge_requests/118",
        last_commit: { message: "add env file" },
      },
    }),
  },
  database: {
    label: "Database change",
    hint: "Query + migration — expect A03",
    event: base({
      labels: [{ title: "backend" }],
      changed_files: ["src/models/user.py", "migrations/0042_add_email.sql"],
      object_attributes: {
        iid: 110,
        title: "Add email column and lookup query",
        description: "SQL in `migrations/0042_add_email.sql`",
        state: "opened",
        action: "open",
        source_branch: "feat/email-lookup",
        target_branch: "main",
        url: "https://gitlab.com/owasp-blt/blt-preflight/-/merge_requests/110",
        last_commit: { message: "user email query" },
      },
    }),
  },
  docs: {
    label: "Docs only",
    hint: "README — expect INFO / LOW",
    event: base({
      labels: [{ title: "documentation" }],
      changed_files: ["README.md", "docs/CONFIGURATION.md"],
      object_attributes: {
        iid: 99,
        title: "Clarify webhook setup in README",
        description: "Docs only",
        state: "opened",
        action: "open",
        source_branch: "docs/webhook",
        target_branch: "main",
        url: "https://gitlab.com/owasp-blt/blt-preflight/-/merge_requests/99",
        last_commit: { message: "docs: webhook" },
      },
    }),
  },
};

export const NON_MR_EVENT = {
  object_kind: "push",
  event_type: "push",
  project: { id: 42, path_with_namespace: "owasp-blt/blt-preflight" },
};
