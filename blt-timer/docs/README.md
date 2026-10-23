# BLT Timer Web API Reference

BLT Timer Web provides a small cookie-authenticated API for manual work logging.

All JSON requests use `Content-Type: application/json`.

Authenticated browser requests include the session cookie automatically.

## Health

```text
GET /health
```

Returns a JSON object with the service status and current timestamp.

## Authentication

### Register

```text
POST /api/auth/register
```

```json
{
  "username": "blt-contributor",
  "email": "contributor@example.test",
  "password": "a-password-with-eight-characters"
}
```

The response creates the account and sets an HttpOnly session cookie.

### Login

```text
POST /api/auth/login
```

```json
{
  "login": "contributor@example.test",
  "password": "a-password-with-eight-characters"
}
```

`login` accepts either the account email or username.

### Current user and logout

```text
GET  /api/me
POST /api/auth/logout
```

`GET /api/me` returns the account resolved from the session cookie.

`POST /api/auth/logout` invalidates the current session and clears its cookie.

## Work logs

```text
GET    /api/logs
POST   /api/logs
GET    /api/logs/:id
PATCH  /api/logs/:id
DELETE /api/logs/:id
```

Create a log with the following JSON fields.

```json
{
  "title": "Review timer implementation",
  "notes": "Checked the timer and saved the completed work.",
  "project": "BLT Timer Web",
  "referenceUrl": "https://example.test/work-item",
  "source": "web",
  "startTime": 1760000000000,
  "endTime": 1760001800000,
  "durationSeconds": 1800
}
```

`title`, `startTime`, and `endTime` are required.

The Worker derives `durationSeconds` from the timestamps when it is omitted.

List requests support `limit`, `project`, `start`, `end`, and `q` query parameters.

Every work-log route is scoped to the account in the session cookie.

## Statistics and export

```text
GET /api/stats?range=today|week|month
GET /api/export.csv
GET /api/export.json
```

Statistics include the selected range, saved-log count, total duration, and average duration.

Both exports include only the current user's work logs.

## Errors

Malformed requests return JSON errors with status `400`.

Unauthenticated requests return `401`.

Unknown or inaccessible work logs return `404`.
