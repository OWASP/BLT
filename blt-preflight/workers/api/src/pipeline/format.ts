import type { Advisory } from "./types";

export function formatGitLabComment(a: Advisory): string {
  const recs = a.recommendations.map((r, i) => `${i + 1}. ${r}`).join("\n");
  const refs = a.owaspRefs.map((r) => `- [${r.title}](${r.url})`).join("\n");
  const evidence = a.evidence.map((e) => `- ${e}`).join("\n");
  return [
    `## BLT Preflight advisory`,
    ``,
    `| | |`,
    `|---|---|`,
    `| Severity | **${a.severity}** |`,
    `| Confidence | ${a.confidence}% |`,
    `| OWASP | ${a.owaspCategory} |`,
    `| MR | ${a.projectPath}!${a.mrIid} |`,
    `| Score | ${a.score.raw.toFixed(2)} |`,
    ``,
    `### ${a.title}`,
    ``,
    a.explanation,
    ``,
    `### Recommendations (priority order)`,
    recs,
    ``,
    `### Evidence`,
    evidence || "- (title/labels only — no file list in webhook)",
    ``,
    `### References`,
    refs || "- none above retrieval threshold",
    ``,
    `---`,
    `_Guidance only. Does not block merge. Dismiss with label \`preflight-inapplicable\`._`,
  ].join("\n");
}