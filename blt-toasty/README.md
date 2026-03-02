# Toasty - AI-Powered GitHub PR Assistant

# 1. Architecture Overview (Cloudflare Native)

## High-Level System Design

![Image](https://developers.cloudflare.com/_astro/diagram.DEMTm7TJ_Z29E9sM.svg)

![Image](https://raw.githubusercontent.com/InternetFreedomFoundation/internetfreedom.in/main/Iff-JamStack.png)

![Image](https://www.tenupsoft.com/images/blogs/Edge_Computing_Main_Image_Blog.webp)

![Image](https://dl.acm.org/cms/attachment/html/10.1145/3437378.3444367/assets/html/images/acsw21-27-fig1.jpg)

### Core Flow

1. GitHub sends webhook → Cloudflare Worker
2. Worker validates signature
3. Worker fetches PR data from GitHub API
4. Worker sends structured context to AI agent
5. Worker stores results in Cloudflare storage
6. Worker posts AI review back to GitHub
7. Dashboard reads data from Cloudflare storage

---

# 2. Cloudflare-Based System Components

---

## 1. GitHub Repository

* Emits webhook events:

  * pull_request (opened, synchronize)
  * issue_comment (created)
* Sends events to Cloudflare Worker endpoint

---

## 2. Cloudflare Python Worker (Core Engine)

Replaces Django backend.

Responsibilities:

* Webhook validation
* Event routing
* PR metadata extraction
* GitHub API communication
* AI agent orchestration
* Posting comments back to GitHub
* Conversation tracking
* Security scanning triggers
* Priority score computation

Key Cloudflare features used:

* **Workers (Python runtime)**
* **KV (lightweight metadata storage)**
* **Durable Objects (conversation state & locking)**
* **D1 (structured relational data)**
* **R2 (optional diff storage for large PRs)**
* **Queues (async AI processing)**

---

## 3. AI Agent Service

Can be:

* External LLM API (OpenAI / Anthropic)
* Self-hosted inference
* Cloudflare AI (optional future enhancement)

Responsibilities:

* Smart prioritization scoring
* Code review analysis
* Security scanning
* Comment generation
* Thread summarization

---

## 4. Cloudflare Storage Design

### D1 (Relational Database)

Stores:

* PR metadata
* Priority scores
* Security findings
* AI analysis logs
* Repository configuration

### Durable Objects

Stores:

* Active PR conversation context
* Thread history
* Summaries for long threads
* Concurrency-safe PR locks

### KV

Stores:

* Lightweight cache
* Quick priority lookups
* Rate limiting counters

### R2 (Optional)

Stores:

* Large diffs
* Snapshot archives

---

## 5. Frontend Dashboard

Options:

* Cloudflare Pages
* Worker-rendered dashboard
* SPA consuming Worker API

Features:

* Prioritized PR list
* AI score visualization
* Security alerts
* Trend analysis
* Filtering & search
* Customizable scoring weights

---

# 3. Feature TODO List (Consolidated Master List)

Below is a complete feature checklist for implementation.

---

# A. Core Webhook System

* [ ] Create Cloudflare Python Worker project
* [ ] Configure GitHub webhook endpoint
* [ ] Implement HMAC SHA256 signature validation
* [ ] Implement event type router:

  * pull_request
  * issue_comment
* [ ] Add structured logging
* [ ] Implement rate limiting
* [ ] Add error handling & retry logic
* [ ] Add webhook replay protection

---

# B. GitHub API Integration

* [ ] Fetch PR metadata
* [ ] Fetch changed files
* [ ] Fetch diffs
* [ ] Fetch commit history
* [ ] Fetch CI/test results
* [ ] Fetch review history
* [ ] Fetch repository activity metrics
* [ ] Post PR comments
* [ ] Reply to specific comment threads
* [ ] Tag maintainers for critical alerts

---

# C. AI Agent Core Capabilities

---

## 1. Smart Prioritization

* [ ] Build rule-based scoring engine:

  * Lines changed
  * File count
  * Dependency changes
  * Test failures
  * Security flags
  * Contributor reputation
  * Time open
* [ ] Normalize scores
* [ ] Add repository activity weighting
* [ ] Add dependency graph impact scoring
* [ ] Generate LLM-based explanation of priority
* [ ] Allow customizable scoring weights
* [ ] Store priority score in D1
* [ ] Cache priority ranking in KV
* [ ] Expose ranking API endpoint

---

## 2. Intelligent Code Review

* [ ] Chunk large diffs for token efficiency
* [ ] Generate structured review prompt
* [ ] Detect:

  * Bugs
  * Code smells
  * Performance issues
  * Anti-patterns
  * Missing tests
* [ ] Add confidence score to findings
* [ ] Format structured GitHub-friendly markdown output
* [ ] Post automated review summary
* [ ] Support inline code suggestions
* [ ] Add auto-summary for long PRs
* [ ] Track false positives

---

## 3. Security Analysis

* [ ] Integrate OWASP Top 10 detection patterns
* [ ] Map findings to CWE categories
* [ ] Flag:

  * Injection risks
  * XSS
  * Auth bypass
  * Unsafe deserialization
  * Dependency vulnerabilities
* [ ] Add severity levels (Low / Medium / High / Critical)
* [ ] Add real-time critical alerts
* [ ] Implement false positive thresholding
* [ ] Log security findings in D1
* [ ] Create security dashboard view

---

## 4. Multi-Turn Conversation Support

* [ ] Store comment threads in Durable Objects
* [ ] Track:

  * AI comments
  * Developer replies
* [ ] Implement conversation summarization when token limit grows
* [ ] Support contextual AI responses
* [ ] Prevent duplicate responses
* [ ] Add mention-based triggers (e.g., @ai-reviewer)
* [ ] Allow manual re-analysis command
* [ ] Add conversation history compression

---

# D. AI Efficiency & Cost Optimization

* [ ] Implement diff chunking
* [ ] Add conversation summarization
* [ ] Cache previous AI responses
* [ ] Avoid reprocessing unchanged diffs
* [ ] Add token usage logging
* [ ] Add usage quotas per repository
* [ ] Implement async processing with Cloudflare Queues

---

# E. Data Storage & Schema

* [ ] Design D1 schema for:

  * Repositories
  * Pull Requests
  * Priority Scores
  * Security Findings
  * AI Analyses
  * Configuration settings
* [ ] Implement Durable Object for PR conversation state
* [ ] Add indexing for fast dashboard queries
* [ ] Implement backup/export capability

---

# F. Dashboard Features

* [ ] Create PR overview page
* [ ] Display:

  * Priority score
  * Security score
  * Quality score
* [ ] Visual priority ranking
* [ ] Filter by:

  * Severity
  * Contributor
  * Age
  * Score
* [ ] Add trend visualization
* [ ] Add explanation tooltips
* [ ] Add customizable ranking weights UI
* [ ] Add repository configuration panel
* [ ] Add AI confidence indicators
* [ ] Add PR detail page:

  * Full AI review
  * Security findings
  * Conversation history

---

# G. Scalability & Performance

* [ ] Stress test large repositories
* [ ] Optimize cold start time
* [ ] Use edge caching for dashboard
* [ ] Implement concurrency control via Durable Objects
* [ ] Add queue-based async AI processing
* [ ] Benchmark response time (<30 seconds goal)
* [ ] Add timeout handling for AI calls
* [ ] Add fallback behavior if AI fails

---

# H. Security & Compliance

* [ ] Encrypt GitHub tokens (Cloudflare Secrets)
* [ ] Validate webhook signatures
* [ ] Implement rate limiting
* [ ] Add abuse protection
* [ ] Implement audit logs
* [ ] Secure D1 access controls
* [ ] Prevent prompt injection attacks
* [ ] Add output sanitization before posting to GitHub

---

# I. DevOps & Deployment

* [ ] Set up Wrangler configuration
* [ ] Configure environments (dev/staging/prod)
* [ ] Add CI pipeline
* [ ] Add automated testing:

  * Webhook tests
  * Signature tests
  * PR simulation tests
* [ ] Add logging & monitoring
* [ ] Add analytics for AI performance
* [ ] Implement error alerting

---

# J. Advanced Enhancements (Future-Ready)

* [ ] Auto-merge recommendation system
* [ ] Risk prediction model
* [ ] Contributor behavior analytics
* [ ] Repository health score
* [ ] Auto-label PRs
* [ ] Dependency upgrade suggestions
* [ ] ML-based anomaly detection
* [ ] Cross-repository prioritization
* [ ] Multi-repository dashboard
* [ ] Slack/Discord integration
* [ ] Cloudflare AI native model migration

---

# Final Deliverable

A fully serverless, edge-native AI GitHub assistant running entirely on:

* Cloudflare Python Workers
* Durable Objects
* D1
* KV
* Queues
* Pages (Dashboard)

That:

* Automatically reviews pull requests
* Intelligently prioritizes tasks
* Detects security vulnerabilities
* Participates in discussions
* Scales globally at the edge
* Minimizes latency and infrastructure overhead

