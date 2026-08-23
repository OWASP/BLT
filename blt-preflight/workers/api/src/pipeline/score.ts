import { classifyFiles } from "./signals";
import type { ExtractedSignals, ScoreBreakdown, Severity } from "./types";

export const WEIGHTS = {
  authFile: 0.4,
  labelSeverity: 0.3,
  keyword: 0.25,
  docsOnly: -0.3,
  secretFile: 0.45,
};

export function scoreSignals(signals: ExtractedSignals): ScoreBreakdown {
  const flags = classifyFiles(signals.changedFiles);
  const labels = signals.labels.map((l) => l.toLowerCase());
  const labelHit =
    labels.some((l) => /security|auth|critical|vulnerability/.test(l)) ? 1 : labels.length ? 0.2 : 0;

  const keywordHit = Math.min(1, signals.keywords.length / 4);
  const authScore = flags.auth || flags.crypto ? 1 : 0;
  const secretBoost = flags.secret ? WEIGHTS.secretFile : 0;
  const apiBoost = flags.api ? 0.2 : 0;
  const dbBoost = flags.database ? 0.2 : 0;
  const docsPenalty = flags.docsOnly ? WEIGHTS.docsOnly : 0;

  let raw =
    WEIGHTS.authFile * authScore +
    WEIGHTS.labelSeverity * labelHit +
    WEIGHTS.keyword * keywordHit +
    secretBoost +
    apiBoost +
    dbBoost +
    docsPenalty;

  raw = Math.max(0, Math.min(1, raw));

  let severity: Severity;
  const hardSecret = flags.secret && !flags.docsOnly;

  if (hardSecret || raw > 0.85) severity = "CRITICAL";
  else if (raw > 0.7) severity = "HIGH";
  else if (raw >= 0.4) severity = "MEDIUM";
  else if (raw > 0.15) severity = "LOW";
  else severity = "INFO";

  if (flags.docsOnly && !hardSecret) severity = raw > 0.3 ? "LOW" : "INFO";

  return {
    authFile: authScore,
    labelSeverity: labelHit,
    keyword: keywordHit,
    docsOnlyPenalty: flags.docsOnly ? 1 : 0,
    raw,
    severity,
  };
}

export function primaryOwasp(signals: ExtractedSignals): string {
  const flags = classifyFiles(signals.changedFiles);
  if (flags.secret) return "A02:2021";
  if (flags.auth) return "A07:2021";
  if (flags.database) return "A03:2021";
  if (flags.api) return "A01:2021";
  if (flags.crypto) return "A02:2021";
  if (signals.labels.some((l) => /auth/i.test(l))) return "A07:2021";
  return "INFO";
}
