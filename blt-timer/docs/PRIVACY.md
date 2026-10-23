# BLT Timer Web Privacy and Data Handling

BLT Timer Web records only the information needed to provide manual work logging.

## Data stored

- Account ID, username, email address, display name, and timezone.
- A one-way password hash.
- A hashed session token and session expiry metadata.
- Work-log title, notes, project, reference URL, timestamps, and duration when a user saves a log.

## Data not collected automatically

The application does not automatically capture interaction telemetry, screen content, code content, or provider activity.

The active timer remains in the browser's local storage until the user saves or discards it.

## Access and control

Each API request is authorized through an HttpOnly session cookie.

Users can edit or delete their own saved work logs in the dashboard.

Users can download their own work-log records as CSV or JSON.

## Storage and transport

Account, session, and work-log records are stored in Cloudflare D1.

Production requests should use HTTPS through the deployed Cloudflare Worker.

Session tokens are stored as hashes in D1 rather than as raw cookie values.

## Contact

For BLT Timer Web questions, use the project's normal contribution channel.
