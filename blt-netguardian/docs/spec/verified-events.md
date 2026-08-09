# Verified events (`ng-event-1`)

Outbox events for downstream consumers (Rewards, RepoTrust). Emitted on convert-to-issue and resolution; optionally delivered via signed webhook.

## Storage

Table: `events_outbox` (created in `migrations/0002_ingest_core.sql`).

| Column | Notes |
|--------|-------|
| `id` | Event id |
| `org_id` | Org scope |
| `event_type` | `finding.converted` \| `finding.resolved` |
| `dedupe_key` | Unique per org: `{event_type}:{finding_id}` |
| `payload_json` | Versioned payload (`ng-event-1`) |
| `status` | `pending` \| `delivered` \| `skipped` \| `failed` |
| `attempts` | Webhook delivery attempts |
| `last_error` | Last delivery error (truncated) |

## Payload

```json
{
  "version": "ng-event-1",
  "event_type": "finding.converted",
  "cve_id": "CVE-2024-1234",
  "cve_score": 7.5,
  "rule_id": "http.missing-hsts",
  "severity": "high",
  "org_id": "org-demo",
  "target": "https://example.com",
  "finding_id": "f1",
  "issue_id": "blt-123",
  "created_at": 1720000000,
  "dedupe_key": "finding.converted:f1"
}
```

## Emission points

1. **Convert to Issue** (`POST /api/findings/{id}/convert-to-issue`) → `finding.converted` (idempotent on re-convert).
2. **Resolution** (`PATCH /api/findings/{id}` with `status=wontfix`) → `finding.resolved`.

## Read API

- `GET /api/events` — org-scoped list (`event_type`, `finding_id`, `status`, `limit`, `offset`)
- `GET /api/events/{id}` — org-scoped detail

Auth: same org Bearer tokens as triage (`NG_ORG_API_TOKENS`).

## Webhook delivery

Optional env secrets:

- `NG_EVENTS_WEBHOOK_URL`
- `NG_EVENTS_WEBHOOK_SECRET` (64-char hex or UTF-8 string)

Request:

```http
POST {NG_EVENTS_WEBHOOK_URL}
Content-Type: application/json
X-NetGuardian-Signature: sha256=<hmac-sha256-hex of body>
X-NetGuardian-Event-Id: <event id>
X-NetGuardian-Event-Type: finding.converted
```

Body is a compact, sorted-keys JSON envelope:

```json
{
  "created_at": 1720000000,
  "dedupe_key": "finding.converted:f1",
  "event_type": "finding.converted",
  "id": "evt-1",
  "org_id": "org-demo",
  "payload": { "...": "ng-event-1 fields" }
}
```

Behavior:

- No URL configured → status `skipped` (event still queryable).
- URL set but secret missing → `failed`.
- HTTP 2xx → `delivered`.
- Other / transport error → stay `pending` until `attempts >= 5`, then `failed`.

NetGuardian does **not** implement downstream scoring — only emit + document consumption.
