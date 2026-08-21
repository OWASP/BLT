# Quickstart — install, crawl, triage

End-to-end path for the **shipped** spine (not legacy discovery stubs).

## 1. Local API + triage UI

From the repo root:

```bash
python3 local_dev/serve.py
```

- Health: http://127.0.0.1:8787/api/health  
- Triage: http://127.0.0.1:8787/triage.html (demo token `triage-token` on loopback)  
- Home: http://127.0.0.1:8787/

## 2. Flutter client

Needs [Flutter](https://flutter.dev/docs/get-started/install) on PATH.

```bash
cd client
flutter pub get
flutter run -d macos          # preferred for crawl (no browser CORS)
# or: flutter run -d chrome --web-port=8888
```

In the app:

1. API base URL → `http://127.0.0.1:8787` (local) or your Worker origin  
2. Leave demo sender fields, or paste org-issued keys  
3. Enable **Distributed crawl**  
4. Seed URL (e.g. `https://owasp.org/`) → **Start crawl**  
5. Watch the shared domain grid (pending / scanning / scanned)  
6. **Stop crawl** → select findings → **Sign & send selected**  
7. **Open triage** (or refresh the triage tab)

Pinned Start/Stop stay at the top; findings/domain lists are capped so the UI stays usable during a long crawl.

## 3. What the crawl does

```
seed → POST /api/domains (submit hosts)
     → POST /api/domains/claim (lease)
     → client fetches pages + extracts hosts + header-scans
     → POST /api/domains (new hosts) + complete/fail
     → next claim
```

The Worker coordinates the queue in D1. **Clients** do all third-party fetches.

## 4. Staging Worker

Example staging:

https://blt-netguardian.preethampujari395.workers.dev/

```bash
# apply D1 migrations + deploy (personal account)
./scripts/deploy-staging.sh
```

Point the client API base URL at that origin. Demo org: `org-demo` / HMAC `736563726574` / token `triage-token`.

Production OWASP host (when deployed there): https://netguardian.owaspblt.org/

## 5. Access model

| Role | Does |
|------|------|
| Site owner | Registers org → receives HMAC + payload + triage keys → issues keys to researchers |
| Researcher | Runs Flutter client with those keys → crawl/scan with permission → sends findings |
| Triage operator | Reviews queue in `triage.html`, status / fix / disclose / convert to BLT issue |

Downloading the client without org keys is not enough against a real deployment.

## More

- Pilot checklist: [`pilot-checklist.md`](pilot-checklist.md)  
- Flutter details: [`flutter-client.md`](flutter-client.md)  
- Client packaging: [`client-packaging.md`](client-packaging.md)  
- Detection rules: [`detection-mvp.md`](detection-mvp.md)  
