# PDF export

Workers-safe finding reports generated with a pure-Python PDF 1.4 writer (no WeasyPrint / native deps).

## Endpoints

| Method | Path | Body |
|--------|------|------|
| GET | `/api/findings/export.pdf` | Multi-finding report (same filters as list/CSV) |
| GET | `/api/findings/{id}/export.pdf` | Single finding + redacted evidence snippet |

Auth: org Bearer token (same as triage reads).

### Collection filters (`/api/findings/export.pdf`)

Uses the shared list query parser (`parse_findings_query`):

| Param | Notes |
|-------|--------|
| `status` | Allowed triage statuses |
| `severity` | Severity filter |
| `cve_id` | Exact CVE id |
| `created_from` / `created_to` | Unix seconds |
| `triage_queue` | Boolean (`1`/`true`/`yes`) |
| `limit` / `offset` | Pagination (`limit` max 100) |
| `sort` / `order` | Same enums as `GET /api/findings` |

Invalid filters → `400` with `{"error":"invalid_query",...}` (same as list/CSV).

## Redaction policy

- Payload secrets (`password`, `token`, `api_key`, …) → `[REDACTED]` via `payload_redact`
- Finding metadata is sanitized before render: `target` drops URL credentials/query/fragment; free-text fields redact `token=` / `password=` style values and embedded URLs
- Encrypted-at-rest evidence is decrypted only when org key is available; ciphertext wrappers are never written into the PDF
- List export includes metadata only (no evidence bodies)

## Implementation notes

- `src/pdf_report.py` — layout + PDF serializer
- Suitable for Cloudflare Python Workers (stdlib only)
- UI: triage detail panel **Export PDF** button
