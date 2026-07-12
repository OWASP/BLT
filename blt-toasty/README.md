# 🥪 BLT-Toasty: AI Triage & Responsible Disclosure Assistant

## Executive Summary
BLT-Toasty is an AI-powered triage and responsible disclosure assistant for the OWASP Bug Logging Tool (BLT). It aims to eliminate the three largest bottlenecks in the vulnerability disclosure pipeline: duplicate issue detection, PII/secret exposure, and manual summarization. By leveraging Cloudflare's edge infrastructure and a strict fail-closed security architecture, Toasty provides lightning-fast semantic deduplication, guaranteed PII redaction, and token-optimized AI summaries, ultimately reducing manual triage time by over 30%.

## Core Architecture & Tech Stack
Toasty operates entirely on Cloudflare's Edge, ensuring high performance, global availability, and seamless integration with existing OWASP infrastructure.

- **Edge Runtime**: Cloudflare Workers (Python/Pyodide)
- **Stateful Operations**: Cloudflare Durable Objects (Multi-turn conversations, Rate Limiting)
- **Database**: Cloudflare D1 (Edge SQLite for state machine and audit logs)
- **Vector Store**: Cloudflare Vectorize (384-dimensional embeddings, cosine similarity)
- **PII Detection**: Microsoft Presidio (Docker sidecar accessed via Cloudflare Tunnel)
- **Embeddings**: FastEmbed Sidecar (`BAAI/bge-small-en-v1.5`)
- **LLM Engine**: Cloudflare Workers AI (`@cf/meta/llama-3.1-8b-instruct`) with OpenAI (`gpt-4o-mini`) fallback; proposed Quality Gate provider routing uses LiteLLM
- **Integration**: GitLab Webhooks & REST API, Slack API, and GitHub Actions/Check Runs for mirror-specific quality automation

## Design Philosophy: Zero-Trust & Fail-Closed Redaction 🔒
The most critical invariant of the BLT-Toasty architecture is **Fail-Closed Redaction**.

```text
RAW PAYLOAD → [REDACTION GATE] → redacted_text → [LLM / Vectorize]
                     ↓ FAIL
              quarantined (D1) — no forward progress
```

**The Guarantee:** No LLM inference and no vector embedding ever executes until Microsoft Presidio and strict regex fallback scanners successfully process the input with a confidence score of `>= 0.70`.
If the redaction gate fails for *any* reason—timeout, parse error, or low confidence—the event is immediately quarantined in D1 and flagged for manual security review. This invariant is enforced at the code level by the `assert_redacted_before_downstream()` guard, ensuring 100% zero-trust processing of all incoming bug reports.

## AI Quality Gate (BLT-Toasty)

The AI Quality Gate is a proposed BLT-Toasty feature that acts as a post-submission gatekeeper for pull requests. It intercepts PR events at the webhook edge, runs deterministic and LLM-backed policy checks, and only allows downstream AI review tools such as CodeRabbit to run after the PR passes the gate.

Although BLT-Toasty's core triage workflow is GitLab-integrated, this Quality Gate design targets the project's GitHub mirror and therefore uses GitHub-specific concepts such as pull requests, Check Runs, and Actions workflows.

This is separate from **BLT-Preflight**. Preflight is an advisory tool that helps contributors before they open a PR; the Toasty Quality Gate runs after a PR is submitted and can enforce a hard `PASS`, `FAIL`, or `HOLD` decision.

### Quality Gate Flow

```text
Pull Request → Webhook Ingress → Cloudflare Queue → Gate Processor
       → deterministic rules → RAG-backed LLM policy review
       → GitHub Check Run: PASS / FAIL / HOLD
       → CodeRabbit runs only after PASS
```

The gate is designed to reduce maintainer review noise, prevent wasted LLM spend on low-quality or spam PRs, and give contributors clear feedback when a PR is blocked.

### Policy Checks

The gate combines fast deterministic checks with LLM policy review:

- **Deterministic rules:** title length, required description, linked issue, draft status, single-file spam patterns, and spam keyword detection.
- **RAG-backed review:** repository policy documents such as `CONTRIBUTING.md` are embedded in Cloudflare Vectorize and retrieved as context for LLM decisions.
- **Structured outcomes:** every decision includes reason codes, policy context, and audit metadata so maintainers can review false positives.
- **Shadow mode:** the gate can run in non-blocking mode before enforcement so maintainers can tune thresholds against real PR traffic.

### Contributor Expectations

Contributors should expect the `toasty/quality-gate` check to appear on PRs once this feature is enabled. A passing PR continues to the normal review flow. A failed or held PR should include actionable reason codes explaining what needs to be fixed before CodeRabbit or maintainer review continues.

To avoid gate failures:

- Write a clear PR title and description.
- Link the relevant issue when required by the repository.
- Avoid draft, placeholder, spam-like, or single-file noise submissions.
- Follow the repository's contribution and security guidance.
- Treat gate feedback as review input; maintainers can override false positives when needed.

### Cloudflare-Native Gate Architecture

The Quality Gate extends BLT-Toasty's Cloudflare-first architecture:

- **Webhook ingress Worker:** validates GitHub HMAC signatures and deduplicates deliveries.
- **Cloudflare Queues:** decouples webhook intake from policy processing with durable delivery.
- **Gate processor Worker:** runs deterministic checks, LiteLLM-powered provider routing, and RAG-grounded policy review.
- **Cloudflare D1:** stores decision logs, audit events, repository policy, cost telemetry, and false-positive tuning data.
- **Cloudflare KV:** stores encrypted BYOK provider keys and rotation metadata.
- **Cloudflare Vectorize:** indexes policy-document embeddings for retrieval during LLM checks.
- **Cloudflare Pages dashboard:** exposes decision traces, key status, cost analytics, and maintainer review tools.

### CodeRabbit Gate Chaining

The intended GitHub Actions flow is:

1. `toasty-quality-gate.yml` runs on PR events and publishes the `toasty/quality-gate` check.
2. `coderabbit-after-gate.yml` runs through `workflow_run` and must explicitly check `github.event.workflow_run.conclusion == 'success'` before running CodeRabbit.
3. `.coderabbit.yaml` can ignore blocked labels such as `bot:blocked` as a defense-in-depth layer.

This keeps expensive AI code review behind the quality filter while preserving a clear audit trail for contributors and maintainers.

## 12-Week Roadmap & Milestones

The project is executed in a rigorous 12-week timeline, divided into three major phases:

### Phase 1: Foundations & Redaction Hardening (Weeks 1-2)
*Goal: Establish bulletproof infrastructure and the fail-closed security gate.*
- **Week 1:** GitLab Webhook ingress, X-Gitlab-Token validation, KV replay protection, and the D1 State Machine.
- **Week 2:** Presidio sidecar deployment, custom PII recognizers, Fail-Closed Redaction Engine, and Golden Set acceptance testing.

### Phase 2: Semantic & Explainability Buildout (Weeks 3-7)
*Goal: Implement AI summarization, semantic search, and human-readable audit trails.*
- **Week 3:** Summarizer v1 with token-budgeted prompts, CWE classification, and Cloudflare Workers AI / OpenAI routing.
- **Week 4:** FastEmbed sidecar, Cloudflare Vectorize integration, and `top_k=20` retrieval pipeline.
- **Week 5:** Duplicate linker with LLM adjudication, GitLab commenting, and Slack pilot notifications.
- **Week 6:** Label Rationale API, CWE reasoning fields, and the Audit Completeness Gate.
- **Week 7:** Durable Objects conversation state, 5-turn rolling buffer, and D1 multi-turn archival.

### Phase 3: Hardening & MCP Export (Weeks 8-12)
*Goal: Secure the pipeline, enable agentic export, and validate against real-world data.*
- **Week 8:** Adversarial test suite (prompt injection, PII evasion, fuzzing).
- **Week 9:** JWT-secured Model Context Protocol (MCP) Export API and REST fallback transport.
- **Week 10:** Shadow Mode validation pipeline comparing Toasty's output against manual maintainer actions.
- **Week 11:** Analytics dashboard via Cloudflare Analytics Engine and bug-fix sweeps.
- **Week 12:** Comprehensive documentation pack, onboarding guides, and final sign-off.

## Current Status & Tracking
Development is strictly tracked via GitLab Issues. Every week corresponds to a specific set of actionable issues mapped directly to our milestones.
You can view our active progress on the [GitLab Issues page](https://gitlab.com/owasp-blt/blt-toasty/-/issues) or project board.

## Setup & Contribution Guidelines

We enforce the OWASP BLT ecosystem quality standards:
- **Python Version**: 3.13+ (managed via `uv`)
- **Formatting & Linting**: `black` (line-length 120), `ruff`, `bandit`
- **Testing**: `pytest`, `pytest-asyncio` with a strict `80%` minimum coverage requirement.
- **Pre-commit**: All commits must pass the configured pre-commit hooks.

### Quick Start (Local Dev)
1. **Clone the repository:**
   ```bash
   git clone https://gitlab.com/owasp-blt/blt-toasty.git
   cd BLT-Toasty
   ```
2. **Install dependencies:**
   ```bash
   npm install       # Installs Wrangler
   uv sync           # Installs Python dependencies
   pre-commit install
   ```
3. **Start local sidecars (Presidio & FastEmbed):**
   ```bash
   docker compose up -d
   ```
4. **Run the local Cloudflare Worker:**
   ```bash
   npx wrangler dev
   ```

For full details, please refer to the `CONTRIBUTING.md` and the documentation in the `docs/` folder.
