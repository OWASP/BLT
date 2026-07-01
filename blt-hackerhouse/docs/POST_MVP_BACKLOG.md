# Post-MVP Backlog — BLT-Hackerhouse

*Features removed, deferred, or postponed from the MVP scope.*

---

## Removed: Mentorship (Out of Scope for MVP)

| Original ID | Feature | Reason |
|-------------|---------|--------|
| F34 | Mentor Lifecycle Projection | Mentorship tracking out of scope per project context update. |
| FR36 | Display mentor lifecycle projection | Removed with F34. |
| — | Mentor Office (Floor 3 room) | Room replaced with "Release Management Room" in MVP. |
| — | Strategy War Room (Floor 3 room) | Room removed entirely from MVP. |
| — | `mentor_assigned` event type | Event type removed. |
| — | `mentor_handoff` event type | Event type removed. |

---

## Deferred: Slack Integration (Optional — Requirements Unvalidated)

| Original ID | Feature | Reason |
|-------------|---------|--------|
| F02 | Slack Events Ingestion | Requirements not validated. Deferred until Slack integration is confirmed needed. |
| F07 | Slack Event Normalizer | Depends on F02. |
| F35 | Slack Exponential Backoff Retries | Depends on F02. |
| FR2 | Slack event callback verification | Deferred with F02. |
| FR9 | Slack event mapping to workflow signals | Deferred with F02/F07. |

**Re-add criteria**: BLT maintainers confirm Slack integration is required and define which Slack events map to which rooms.

---

## Deferred: Frontend (Provided Separately)

| Original ID | Feature | Reason |
|-------------|---------|--------|
| F26 | Three-Floor SVG/Canvas Renderer | Frontend architecture will be provided separately. Backend should not depend on frontend decisions. |
| F27 | Room Occupancy Display | Frontend feature. |
| F28 | Dirty Region Redraw | Frontend optimization. |
| F29 | Avatar Debouncing (5s) | Frontend feature. |
| F30 | Activity Feed (UI rendering) | Frontend feature. Backend provides `/activity` API (VF14 in MVP). |
| F31 | Leaderboard Panel (UI) | Frontend feature. Backend provides `/leaderboard` API and WebSocket updates (VF11, VF16 in MVP). |
| F32 | Maintainer Visibility Panel (UI) | Frontend feature. Backend provides `/status` API (VF15 in MVP). |
| F44 | Maintainer Identity Confirmation Flow (UI overlay) | Frontend feature. Backend sends `identity_flag` WebSocket messages (VF11 in MVP). |
| FR17 | Avatar cap of 12 per room with +N counter | Frontend rendering rule. |
| FR18 | Dirty region redraw | Frontend optimization. |
| FR19 | 5-second debounce on avatar movement | Frontend debounce logic. |
| FR29 | Three-floor house layout rendering | Frontend feature. |
| FR30 | Five rooms per floor display | Frontend feature. |
| FR31 | Room occupancy counts per room (visual) | Frontend feature. |
| FR33 | Activity feed payloads (UI) | Frontend feature. |
| FR34 | Maintainer visibility panel (UI) | Frontend feature. |

---

## Deferred: Testing Suite

| Original ID | Feature | Reason |
|-------------|---------|--------|
| F39 | Unit Tests (pytest) | Post-MVP. MVP delivers working pipeline; tests are a separate phase (Week 10 in proposal). |
| F40 | Integration Tests | Post-MVP (Week 10). |
| F41 | Load Tests (locust — 200 clients, 50 events/min) | Post-MVP (Week 10). |

---

## Deferred: Deployment & Documentation

| Original ID | Feature | Reason |
|-------------|---------|--------|
| F42 | Docker Compose Deployment | Post-MVP (Week 11 in proposal). Backend can run directly with `uvicorn` during development. |
| F43 | Contributor Documentation (new adapters) | Post-MVP (Week 11). |

---

## Deferred: Non-Functional / Reliability Enhancements

These were already marked as "Future" in the original feature inventory (Weeks 9-11). They remain post-MVP.

| Original ID | Feature | Notes |
|-------------|---------|-------|
| F37 (was GitHub) | Gap Detection for Events | Included in MVP as VF19 (updated for GitLab). *Retained.* |
| F36 | Dead Letter Handling | Included in MVP as VF20. *Retained.* |
| F38 | Health Endpoints | Included in MVP as VF17. *Retained.* |

---

## Deferred: Optional Scale Enhancement

| Item | Description | Reason |
|------|-------------|--------|
| Cloudflare Worker WebSocket fronting | Optional edge caching and geographic fan-out for WebSocket connections. | Not needed at MVP scale (50–200 contributors). Deployment-layer addition, not architectural change. |

---

## Deferred: Post-GSoC / Future Considerations

| Item | Description |
|------|-------------|
| Discord integration | Not in scope for MVP or GSoC. |
| Jira integration | Not in scope. |
| Historical replay / time travel | Explicitly listed as non-goal in proposal. |
| Authentication / access control | Explicitly listed as non-goal in proposal. |
| Contributor achievement badges / gamification | Explicitly listed as non-goal in proposal. |
| Avatar movement animations beyond state-driven positioning | Explicitly listed as non-goal in proposal. |
| COSMIC integrations | Isolated in adapters if added post-GSoC. Core pipeline is not COSMIC-dependent. |

---

## Backlog Summary

| Category | Count | Items |
|----------|-------|-------|
| Mentorship (removed) | 6 | F34, FR36, Mentor Office room, Strategy War Room room, 2 event types |
| Slack (deferred) | 5 | F02, F07, F35, FR2, FR9 |
| Frontend (deferred) | 16 | F26-F32, F44, FR17-FR19, FR29-FR31, FR33-FR34 |
| Testing (deferred) | 3 | F39, F40, F41 |
| Deployment (deferred) | 2 | F42, F43 |
| Future enhancements | 6 | Cloudflare Worker, Discord, Jira, auth, badges, animations |

**Total: 38 items in backlog.**
