# Pilot checklist

Controlled demo of the **shipped** spine. Do not demo legacy discovery/Web3 scanners.

## Local smoke

```bash
python3 local_dev/serve.py
# optional (real BLT convert). If down, convert uses stub via NG_BLT_STUB_FALLBACK.
python3 local_dev/blt_api_stub.py
```

- [ ] Open http://127.0.0.1:8787/triage.html (localhost auto-token `triage-token`)
- [ ] `GET /api/health` is 200
- [ ] `.venv/bin/python local_dev/send_finding.py` → Refresh → new finding
- [ ] Detail: Evidence (encrypted-at-rest badge), Fix, Disclose, Events, Status
- [ ] Convert to issue (BLT stub or real API)
- [ ] Export CSV + PDF
- [ ] `python3 scripts/detect_export.py --url https://example.com`
- [ ] Flutter: `cd client && flutter test && flutter run -d macos`
  - Scan example.com → Sign & send → history Open triage (`?finding=`)

## Staging

- [ ] `wrangler secret put` for `NG_SENDER_SECRETS`, `NG_ORG_API_TOKENS`, `NG_PAYLOAD_KEYS`
- [ ] Rotate demo tokens before any external org
- [ ] Cookie forwarded (OAuth session works after GitHub login)
- [ ] CORS origin matches the hosted UI
- [ ] `AUTHENTICATE_READ_ENDPOINTS=true` for non-demo orgs
- [ ] Optional: `NG_EVENTS_WEBHOOK_URL` + secret; cron retries pending (`*/5 * * * *`)
- [ ] Optional: R2 `EVIDENCE` binding for attachment blobs

## Do not pitch

Autonomous CT / GitHub / blockchain scanners, WHOIS outreach, Web3 monitors — those routes return sample/stub data.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Blank / offline triage | Use **http://127.0.0.1:8787/triage.html** (not `file://`, not proposal-vinamra copy) |
| `serve.py` won't start | Port 8787 in use: `lsof -i :8787` then kill old Python or use another machine |
| `flutter run -d macos` fails | Install **Xcode** from App Store, then `sudo xcode-select -s /Applications/Xcode.app/Contents/Developer` |
| No Xcode | `cd client && flutter run -d chrome --web-port=8888` |
| Client API DOWN | Server must run first; base URL `http://127.0.0.1:8787` |
| `send_finding.py` crypto error | Use `.venv/bin/python local_dev/send_finding.py` or `pip install cryptography` |

One-liner helper: `./scripts/run-local.sh` from repo root.
