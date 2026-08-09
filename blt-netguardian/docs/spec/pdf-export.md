# PDF export

Workers-safe finding reports generated with a pure-Python PDF 1.4 writer (no WeasyPrint / native deps).

## Endpoints

| Method | Path | Body |
|--------|------|------|
| GET | `/api/findings/export.pdf` | Multi-finding report (same filters as list/CSV) |
| GET | `/api/findings/{id}/export.pdf` | Single finding + redacted evidence snippet |

Auth: org Bearer token (same as triage reads).

## Redaction policy

- Payload secrets (`password`, `token`, `api_key`, …) → `[REDACTED]` via `payload_redact`
- Encrypted-at-rest evidence is decrypted only when org key is available; ciphertext wrappers are never written into the PDF
- List export includes metadata only (no evidence bodies)

## Implementation notes

- `src/pdf_report.py` — layout + PDF serializer
- Suitable for Cloudflare Python Workers (stdlib only)
- UI: triage detail panel **Export PDF** button
