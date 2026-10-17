export type Severity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO";
export type AdvisoryStatus = "open" | "dismissed" | "resolved" | "false_positive";

export type PipelineStepId =
  | "received"
  | "token_validated"
  | "event_parsed"
  | "signals_extracted"
  | "heuristic_scored"
  | "knowledge_retrieved"
  | "advisory_generated"
  | "stored";

export interface PipelineStep {
  id: PipelineStepId;
  label: string;
  status: "pending" | "ok" | "skipped" | "error";
  detail?: string;
  at: string;
  ms?: number;
}

export interface GitLabProject {
  id: number;
  path_with_namespace: string;
  web_url?: string;
  default_branch?: string;
}

export interface GitLabLabel {
  title: string;
}

export interface GitLabMergeRequestAttributes {
  iid: number;
  title: string;
  description: string | null;
  state: string;
  action: string;
  source_branch: string;
  target_branch: string;
  url?: string;
  last_commit?: {
    id?: string;
    message?: string;
    title?: string;
  };
}

export interface GitLabMergeRequestEvent {
  object_kind: string;
  event_type?: string;
  user?: { name?: string; username?: string };
  project: GitLabProject;
  object_attributes: GitLabMergeRequestAttributes;
  labels?: GitLabLabel[];
  changes?: Record<string, unknown>;
  /** Demo / analysis extension — GitLab diffs are fetched later via API. */
  changed_files?: string[];
}

export interface ExtractedSignals {
  projectId: number;
  projectPath: string;
  mrIid: number;
  title: string;
  description: string;
  action: string;
  state: string;
  sourceBranch: string;
  targetBranch: string;
  labels: string[];
  changedFiles: string[];
  commitMessage: string;
  keywords: string[];
}

export interface ScoreBreakdown {
  authFile: number;
  labelSeverity: number;
  keyword: number;
  docsOnlyPenalty: number;
  raw: number;
  severity: Severity;
}

export interface KnowledgeChunk {
  id: string;
  owasp: string;
  title: string;
  text: string;
  source: string;
  url: string;
  score: number;
}

export interface Advisory {
  id: string;
  projectId: number;
  projectPath: string;
  mrIid: number;
  mrTitle: string;
  mrUrl?: string;
  action: string;
  severity: Severity;
  confidence: number;
  owaspCategory: string;
  title: string;
  explanation: string;
  recommendations: string[];
  evidence: string[];
  owaspRefs: { title: string; url: string }[];
  knowledge: KnowledgeChunk[];
  score: ScoreBreakdown;
  signals: ExtractedSignals;
  status: AdvisoryStatus;
  pipeline: PipelineStep[];
  createdAt: string;
  updatedAt: string;
}

export interface WebhookAccept {
  accepted: true;
  skipped?: boolean;
  reason?: string;
  jobId: string;
  advisoryId?: string;
}

export interface WebhookReject {
  accepted: false;
  error: string;
  code:
    | "invalid_token"
    | "invalid_json"
    | "unsupported_event"
    | "missing_payload";
}

export type WebhookResult = WebhookAccept | WebhookReject;
