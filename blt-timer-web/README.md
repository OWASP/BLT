# BLT Timer Web

BLT Timer Web is a focused web application for recording manual work logs.

Start a timer, pause or resume it in the browser, save the completed work with useful context, and review or export your own history.

## Product scope

- Email, username, and password accounts.
- HttpOnly session cookies.
- Browser-managed start, pause, resume, and stop timer controls.
- Manual work logs with title, notes, project, and reference URL.
- Daily, weekly, and monthly totals.
- CSV and JSON exports.
- Cloudflare D1 storage.

The product stores only account records, hashed session tokens, and work logs that a user chooses to save.

## Architecture

```text
Browser HTML, CSS, and JavaScript
  - localStorage for an active timer
  - cookie-authenticated API requests
          |
          v
Cloudflare Python Worker
  - account and session API
  - work-log, stats, and export API
          |
          v
Cloudflare D1
  - users
  - auth_sessions
  - work_logs
```

## API

```text
GET  /health

POST /api/auth/register
POST /api/auth/login
POST /api/auth/logout
GET  /api/me

GET    /api/logs
POST   /api/logs
GET    /api/logs/:id
PATCH  /api/logs/:id
DELETE /api/logs/:id

GET /api/stats?range=today|week|month
GET /api/export.csv
GET /api/export.json
```

See [the detailed API guide](docs/README.md) for request formats and response behavior.

## Local development

Prerequisites are Python 3.11 or newer and Wrangler 3 or newer.

```bash
python -m unittest discover tests -v
python -m py_compile src/auth.py src/worker.py

cp .env.example .dev.vars
python -c "import secrets; print('SESSION_SECRET=' + secrets.token_urlsafe(48))"
# Copy the generated SESSION_SECRET value into .dev.vars.

./migrate.sh dev
npx wrangler dev
```

## Database schema

`migrations/0001_initial.sql` is the clean baseline for a new database.

It defines only the `users`, `auth_sessions`, and `work_logs` tables.

## Deployment

Create a new empty D1 database, copy the database name and ID printed by Wrangler into `wrangler.toml`, set the production session secret, apply the baseline migration, and deploy.

```bash
npx wrangler login
npx wrangler d1 create blt-timer-web
# Copy the returned database name and ID into wrangler.toml.
npx wrangler secret put SESSION_SECRET --env production
./deploy.sh
```

## Documentation

- [API reference](docs/README.md)
- [Setup guide](docs/SETUP.md)
- [Privacy and data handling](docs/PRIVACY.md)

## License

MIT License.
