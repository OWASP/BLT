# Detection MVP (W9)

First real detector packs. Everything before this slice produced findings from
fixtures or the seed script; this is the path a live scan actually takes:

```
detector pack  →  DetectionFinding  →  ztr-finding-1 envelope  →  POST /api/ingest  →  triage UI
```

Detection is **not** privileged. It authenticates with the same HMAC sender
credentials and posts to the same endpoint any third-party scanner uses, so
there is one trust boundary to reason about rather than two.

## Modules

| Module | Responsibility |
|--------|----------------|
| `src/detect/normalize.py` | `DetectionFinding` → `ztr-finding-1` payload; severity + fingerprint rules |
| `src/detect/http_headers.py` | OWASP Secure Headers checks over a fetched response |
| `src/detect/semgrep.py` | Parses a `semgrep --json` report into findings |
| `scripts/detect_export.py` | Fetches/reads input, signs envelopes, submits them |

### Detectors are pure functions

`scan_headers()` takes an already-fetched `(status, headers)` pair and
`scan_semgrep_results()` takes an already-parsed report. Network calls and
subprocess invocation live only in the CLI. The rules are therefore
deterministic and unit-testable with no sockets and no Semgrep binary in CI.

## Deterministic fingerprints

`fingerprint = "fp-" + sha256(rule_id \0 target \0 locator)[:32]`

Nothing time-varying feeds the hash, so re-scanning an unfixed target yields the
same fingerprint and `process_ingest` **merges** into the existing finding
instead of creating a row per scan. Parts are NUL-joined so `("a", "bc")` cannot
collide with `("ab", "c")`.

The envelope `nonce` is still random per submission — replay protection is
per-request, deduplication is per-issue. These are separate concerns.

`locator` is what makes two findings distinct within one target:

| Detector | `locator` | Effect |
|----------|-----------|--------|
| HTTP headers | header name (`Content-Security-Policy`) | one finding per header per URL |
| Semgrep | `path:line` (`src/db.py:42`) | one finding per call site; moved code re-fingerprints |

## Severity normalization

Detectors use their own scales; the store and UI rank five levels
(`critical`/`high`/`medium`/`low`/`info`). Unknown values degrade to `info`
rather than raising, so a new Semgrep registry value cannot fail a whole scan.

| Semgrep | NetGuardian |
|---------|-------------|
| `ERROR` / `HIGH` | `high` |
| `WARNING` / `MEDIUM` | `medium` |
| `INFO` / `LOW` | `low` |
| `CRITICAL` | `critical` |

## Header rules

| Rule | Severity | Notes |
|------|----------|-------|
| `http.missing-hsts` | high | HTTPS targets only — meaningless over plain HTTP |
| `http.weak-hsts-max-age` | medium | `max-age` under 15552000 (180 days) |
| `http.missing-csp` | medium | |
| `http.unsafe-csp-directive` | medium | `unsafe-inline` / `unsafe-eval` present |
| `http.missing-clickjacking-protection` | medium | Only when *both* `X-Frame-Options` and CSP `frame-ancestors` are absent |
| `http.insecure-cookie-flags` | high / medium | `high` when `Secure` is missing |
| `http.missing-x-content-type-options` | low | |
| `http.server-version-disclosure` | low | Only when the value contains a version number |
| `http.missing-referrer-policy` | info | |

Responses with status ≥ 400 are skipped: error pages routinely omit hardening
headers and would report issues that say nothing about the real application.

## Usage

```bash
# Preview only — no submission, no credentials needed
python scripts/detect_export.py --url https://example.com --dry-run

# Header checks, submitted to the local dev server
python local_dev/serve.py &
python scripts/detect_export.py --url https://example.com

# Semgrep report for a repo
semgrep --config auto --json --output sg.json
python scripts/detect_export.py --semgrep-json sg.json --target github.com/owasp-blt/blt

# Remote target: demo keys are loopback-only, so credentials are required
python scripts/detect_export.py --url https://example.com \
  --base-url https://blt-netguardian.example.workers.dev \
  --secret-hex "$NG_SECRET" --payload-key-b64 "$NG_PAYLOAD_KEY"
```

Payloads are AES-256-GCM encrypted by default; `--plaintext` stores them
readable, which is useful when inspecting rows during development.

Sample run against a live URL:

```
[http] https://example.com -> HTTP 200, 11 headers

5 finding(s) normalized:
  [high    ] http.missing-hsts  fp-befbeac0452fe85bd507ec1b10c4fa3a
  [medium  ] http.missing-csp  fp-96c1e94ac8f24e992e2b0c4b8b98d30d
  [medium  ] http.missing-clickjacking-protection  fp-e22f40028134ca79747d0cd33ea3862a
  [low     ] http.missing-x-content-type-options  fp-708b295a03c059687a72c613799d6048
  [info    ] http.missing-referrer-policy  fp-9b7746064c48e7ffc1d09869adf2dd1b

created=5 merged=0 duplicate=0 failed=0
```

Re-running the same scan reports `created=0 merged=5`.

## Header casing fix

Building the first real client surfaced an ingest bug: `get_request_header()`
looked headers up by exact key, but HTTP field names are case-insensitive
(RFC 7230 §3.2). `urllib.request` capitalizes them, so it sent
`X-blt-body-digest` and ingest rejected the request with `digest_mismatch` —
for a header the client had in fact sent. The lookup now falls back to a
case-insensitive match. Regression coverage is in
`tests/test_ingest_worker.py::test_handle_ingest_accepts_any_digest_header_casing`.

## Tests

| File | Covers |
|------|--------|
| `tests/test_detect_normalize.py` | severity mapping, fingerprint determinism and collision resistance, payload shape |
| `tests/test_detect_http_headers.py` | every header rule, both positive and negative |
| `tests/test_detect_semgrep.py` | report parsing, malformed input, severity scales, truncation |
| `tests/test_detect_e2e.py` | detection → signed envelope → ingest → triage list; re-scan merge; encrypted evidence not readable at rest |
