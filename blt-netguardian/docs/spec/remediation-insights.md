# Remediation insights

Static “why this matters” + markdown fix guidance keyed by `rule_id`, with optional CVE advisory links.

## API

`GET /api/findings/{id}` includes:

```json
{
  "remediation": {
    "rule_id": "http.missing-hsts",
    "why": "...",
    "markdown": "### Fix\n...",
    "owasp_links": ["https://..."],
    "cve_links": ["https://nvd.nist.gov/vuln/detail/CVE-..."]
  }
}
```

## Lookup order

1. Exact `rule_id` fragment (`src/remediation/fragments.py`)
2. Prefix defaults (`http.*`, `semgrep.*`)
3. Generic OWASP Top Ten fallback

## Safety

- Fragments are trusted static content authored in-repo (not scanner/user input).
- Triage UI escapes markdown before inserting into the DOM (no raw HTML render).


