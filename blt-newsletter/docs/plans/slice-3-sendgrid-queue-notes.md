# Slice 3 SendGrid and Queue Campaign Notes

## Summary

Slice 3 adds the BLT-Newsletter email delivery foundation:

- SendGrid Web API service without package dependency.
- BLT-branded newsletter email renderer.
- Admin test-send route.
- Campaign queue route.
- Campaign jobs API.
- Cloudflare Queue producer/consumer foundation.
- Dashboard wiring for jobs, send-test, and queue campaign actions.

## New files

- `src/email_service.py`
  - SendGrid Web API payload builder.
  - Workers `fetch()` sender with local urllib fallback.
  - Safe result object with retry/permanent failure flags.

- `src/email_templates.py`
  - BLT-branded newsletter email HTML.
  - Lightweight Markdown rendering.
  - Escaping for dynamic text and attributes.
  - Archive link and visible unsubscribe footer.

- `src/email_campaigns.py`
  - Send job record builder.
  - Delivery event record builder.
  - Queue message builder with IDs only, no raw email.

- `tests/test_email_campaign_backend.py`
  - Unit coverage for payload shape, template escaping/footer, D1-safe campaign records, and raw-email-free queue messages.

## Worker routes

Added in `src/entry.py`:

- `POST /api/admin/issues/:id/send-test`
- `POST /api/admin/issues/:id/send`
- `GET /api/admin/jobs`
- `GET /api/admin/jobs/:id`
- `POST /api/admin/jobs/:id/cancel`

Queue consumer:

- `async def queue(self, batch)`

## D1 methods added

- `list_active_subscribers`
- `find_subscriber_by_id`
- `mark_subscriber_sent`
- `insert_send_job`
- `list_send_jobs`
- `find_send_job_by_id`
- `update_send_job_status`
- `insert_delivery_event`
- `list_delivery_events_for_job`
- `increment_send_job_counts`

## Dashboard updates

`public/dashboard.html` now:

- loads campaign jobs from `/api/admin/jobs`
- renders campaign rows from API state
- opens campaign details from job state
- sends test email through `/api/admin/issues/:id/send-test`
- queues campaign sends through `/api/admin/issues/:id/send`
- keeps campaign recipient count based on active subscribers

## Queue behavior

Campaign queue route:

1. Loads issue.
2. Loads active subscribers.
3. Creates one `newsletter_send_jobs` row.
4. Creates one queued `newsletter_delivery_events` row per active subscriber.
5. If `NEWSLETTER_QUEUE` is bound, sends ID-only messages:

```json
{
  "job_id": "job_...",
  "issue_id": "issue_...",
  "delivery_event_id": "evt_...",
  "subscriber_id": "sub_..."
}
```

The message intentionally excludes raw email and full issue HTML.

## SendGrid configuration

Required before real sends:

- `SENDGRID_API_KEY`
- `SENDGRID_FROM_EMAIL`
- optional `SENDGRID_FROM_NAME`
- optional `PUBLIC_BASE_URL` or `SITE_URL` for email links

If SendGrid is missing, test-send returns a clear 503 configuration error and queue consumer retries messages.

## Verification

Passed locally:

```bash
python3 -m unittest tests.test_email_campaign_backend \
  tests.test_admin_backend.AdminWorkerRouteTests.test_worker_declares_sendgrid_campaign_and_job_routes \
  tests.test_admin_backend.AdminFrontendWiringTests.test_dashboard_send_test_and_campaign_controls_call_backend_apis \
  tests.test_worker_setup.WorkerSetupTests.test_wrangler_configures_python_worker_with_assets_binding -v

python3 -m unittest discover -s tests -v
PYTHONPYCACHEPREFIX=/private/tmp/blt-newsletter-pycache python3 -m py_compile src/*.py scripts/*.py
git diff --check
```

Wrangler local smoke:

- `GET /api/admin/setup/status` returned 200.
- unauthenticated `GET /api/admin/jobs` returned 401.
- `/dashboard` served with send-test/campaign/job rendering functions.
- Browser dashboard unauthenticated redirect produced no console errors.

## Known follow-ups

- Signed one-click GET unsubscribe/preference-center URL.
- CSRF protection for cookie-auth admin POSTs.
- SendGrid Event Webhook ingestion and suppression sync.
- Stronger retry/dead-letter policy for queue exhaustion.
- Email-at-rest encryption before production-scale campaigns.
