import type { KnowledgeChunk } from "./types";

/** Curated OWASP summaries — not full cheat sheets. Retrieval only. */
export const OWASP_CORPUS: Omit<KnowledgeChunk, "score">[] = [
  {
    id: "a01-broken-access",
    owasp: "A01:2021",
    title: "Broken Access Control",
    text: "New or changed API endpoints must enforce authorization on every request. Never rely on hiding URLs. Check object-level access for IDs in path or body. Default deny; allow only explicit roles.",
    source: "OWASP Top 10 2021",
    url: "https://owasp.org/Top10/A01_2021-Broken_Access_Control/",
  },
  {
    id: "a02-crypto",
    owasp: "A02:2021",
    title: "Cryptographic Failures",
    text: "Do not invent crypto. Use established libraries. Secrets, tokens, and keys must never be committed. Prefer environment variables or a secrets manager. Hash passwords with Argon2 or bcrypt.",
    source: "OWASP Top 10 2021",
    url: "https://owasp.org/Top10/A02_2021-Cryptographic_Failures/",
  },
  {
    id: "a03-injection",
    owasp: "A03:2021",
    title: "Injection",
    text: "Treat all query construction as untrusted. Use parameterized queries / ORM bindings. Never concatenate user input into SQL, OS commands, or LDAP filters. Validate and encode output.",
    source: "OWASP Top 10 2021",
    url: "https://owasp.org/Top10/A03_2021-Injection/",
  },
  {
    id: "a04-design",
    owasp: "A04:2021",
    title: "Insecure Design",
    text: "Threat-model authentication, session, and privilege boundaries before shipping. Rate-limit sensitive flows. Fail closed. Document trust boundaries for new features.",
    source: "OWASP Top 10 2021",
    url: "https://owasp.org/Top10/A04_2021-Insecure_Design/",
  },
  {
    id: "a07-auth",
    owasp: "A07:2021",
    title: "Identification and Authentication Failures",
    text: "Authentication changes require MFA support where possible, secure session cookies (HttpOnly, Secure, SameSite), lockout after failed attempts, and no credential stuffing gaps. Never log passwords or session IDs.",
    source: "OWASP Authentication Cheat Sheet",
    url: "https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html",
  },
  {
    id: "session",
    owasp: "A07:2021",
    title: "Session Management",
    text: "Rotate session identifiers on login. Set cookie flags. Idle and absolute timeouts. Invalidate on logout. Store session state server-side or in signed, short-lived tokens.",
    source: "OWASP Session Management Cheat Sheet",
    url: "https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html",
  },
  {
    id: "api-authz",
    owasp: "API1:2023",
    title: "Broken Object Level Authorization",
    text: "For every new endpoint, verify the caller can access the specific object. Test with another user's ID. Do not trust client-supplied owner fields.",
    source: "OWASP API Security Top 10",
    url: "https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/",
  },
  {
    id: "secrets",
    owasp: "A02:2021",
    title: "Secret Handling",
    text: "API keys, tokens, .env files, and private keys must not land in the repository. Rotate anything that was committed. Use secret scanning and pre-commit hooks.",
    source: "OWASP Secrets Management",
    url: "https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html",
  },
  {
    id: "docs-low",
    owasp: "INFO",
    title: "Documentation-only change",
    text: "Markdown and docs-only diffs are usually low risk. Still scan for accidentally pasted credentials or internal hostnames.",
    source: "BLT Preflight policy",
    url: "https://owasp.org/www-project-bug-logging-tool/",
  },
];

function tokenize(s: string): string[] {
  return s
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter((t) => t.length > 2);
}

export function retrieveKnowledge(query: string, k = 3): KnowledgeChunk[] {
  const q = new Set(tokenize(query));
  if (q.size === 0) return [];
  const scored = OWASP_CORPUS.map((chunk) => {
    const bag = tokenize(`${chunk.title} ${chunk.text} ${chunk.owasp} ${chunk.id}`);
    let overlap = 0;
    for (const t of bag) if (q.has(t)) overlap += 1;
    const score = overlap / Math.sqrt(bag.length || 1);
    return { ...chunk, score };
  })
    .filter((c) => c.score > 0)
    .sort((a, b) => b.score - a.score);
  return scored.slice(0, k);
}
