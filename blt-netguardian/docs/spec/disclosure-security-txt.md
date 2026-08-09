# Disclosure helpers (`security.txt`)

RFC 9116 `security.txt` discovery for finding targets, used to hint contact/policy during convert-to-issue and triage.

## Endpoint

`GET /api/findings/{id}/disclosure`

Returns:

```json
{
  "finding_id": "f1",
  "disclosure": {
    "found": true,
    "source_url": "https://example.com/.well-known/security.txt",
    "contacts": ["mailto:security@example.com"],
    "policy": ["https://example.com/security"],
    "convert_hint": "Disclose via mailto:security@example.com",
    "fields": { "Contact": ["mailto:security@example.com"] }
  }
}
```

## Lookup order

1. `{origin}/.well-known/security.txt`
2. `{origin}/security.txt`

Uses Workers JS `fetch` in production and urllib locally. Parser is pure and offline-testable.
