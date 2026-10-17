# Idea U — Unified Event-Driven Gamification Engine (350h)

**Repository:** OWASP/BLT-API

## Goal

Architect and implement a robust, event-driven engine to handle all reputation, scoring, and reward logic across the BLT ecosystem, decoupling it from core business logic using a Pub/Sub model and a double-entry ledger.

## Summary

As BLT scales with Projects B (Rewards), F (Reputation), and H (Growth), hardcoding reward logic into view functions (e.g., "awarding points inside the PR merge handler") creates brittle, unmaintainable code.

**Idea U** implements a dedicated **Gamification Service** that listens for localized platform events (e.g., `PR_MERGED`, `VULN_VERIFIED`, `REVIEW_COMPLETED`), processes them through a configurable **Rule Engine**, and records transactions in a **Double-Entry Ledger**. This ensures data consistency, prevents "infinite money" bugs, and allows maintainers to tweak the "Game Economy" (e.g., changing point values) without redeploying backend code.

---

## Deliverables

### 1. Event Bus Infrastructure

- **Pub/Sub Implementation:** Utilize Celery + Redis to create a reliable asynchronous event channel.
- **Event Schema:** Define a strict JSON schema for events (`event_id`, `source`, `timestamp`, `actor_id`, `payload`, `signature`) to ensure traceability.
- **Idempotency Layer:** Mechanism to ignore duplicate events (critical for financial/reward correctness).

### 2. Configurable Rule Engine

- **Logic decoupling:** A Strategy Pattern implementation that matches Events to Rewards.
- **Dynamic Configuration:** Support for YAML/JSON-based rules stored in the database:
  - _Example:_ `IF event == 'PR_MERGED' AND pr.labels contains 'security' THEN award 50 XP`.
- **Versioning:** Ability to version rules so historical points aren't recalculated when the economy changes.

### 3. Double-Entry Ledger System

- **Transactional Integrity:** Implementation of a `Ledger` model (`debit_account`, `credit_account`, `amount`, `reference_event_id`).
- **Auditability:** Every user point balance is a sum of ledger entries, ensuring zero discrepancy between "history" and "current balance".
- **Anti-Fraud:** Constraints to prevent negative balances (where applicable) or double-spending.

### 4. Integration Adapters

- **GitHub Listener:** A robust webhook handler that normalizes GitHub events (Issues, PRs, Reviews) into internal BLT Events.
- **Internal Hooks:** Python decorators (`@emit_event`) for other BLT services (e.g., NetGuardian) to trigger rewards easily.

### 5. Economy Admin Dashboard

- **Rule Editor:** UI for maintainers to create/edit scoring rules.
- **Transaction Log:** Searchable view of all ledger entries for audit.
- **Replay Tool:** Ability to safely replay events against new rules for testing (without committing transactions).

---

## Timeline (Week-by-Week)

### Phase 1: Architecture & Ledger Core (Weeks 1–4)

- **Week 1:** Design Event Schema and Ledger Data Model (SQLAlchemy/Django ORM).
- **Week 2:** Implement the Double-Entry Ledger Service with strict transactional locking.
- **Week 3:** Build the base "Event Bus" using Celery tasks and Redis.
- **Week 4:** Unit tests for concurrent transactions and idempotency (proving consistency).

### Phase 2: Rule Engine & Ingestion (Weeks 5–8)

- **Week 5:** Implement the Rule Engine (Parser & Matcher logic).
- **Week 6:** Adapt GitHub Webhooks to feed the Event Bus (Events: `pr.merged`, `issue.created`).
- **Week 7:** Create "Economy Configuration" models (storing rules in DB).
- **Week 8:** Integration testing: GitHub Webhook -> Event Bus -> Rule Match -> Ledger Entry.

### Phase 3: Integration & Dashboard (Weeks 9–12)

- **Week 9:** Refactor existing hardcoded reward points in BLT-API to use the new Engine.
- **Week 10:** Build the Admin Dashboard (Rule Editor & Ledger View).
- **Week 11:** Implement "Replay/Simulation" mode for testing new rules.
- **Week 12:** Performance tuning (batch processing events) and documentation.

### Phase 4: Polish & Scaling (Weeks 13–16)

- **Week 13:** Security review (ensure users can't spoof events).
- **Week 14:** E2E Testing with Projects B and F logic.
- **Week 15:** Final documentation (Architecture Decision Records, API docs).
- **Week 16:** Buffer for bug fixes and final handover.

---

## Benefits

- **Maintainability:** Business logic (GitHub interactions) serves only to _emit events_, not manage economy state.
- **Correctness:** Ledger system prevents math errors and "lost points" common in simple `user.score += 5` implementations.
- **Flexibility:** Maintainers can run "Double XP Weekends" or change point values on the fly by editing rules, not code.
- **Scalability:** The async Event Bus prevents the main API from slowing down during heavy activity.
