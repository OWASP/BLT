# Dedicated Dashboard Pages Design

## Goal

Replace the single long dashboard with a persistent dashboard sidebar and focused, authenticated pages for timer tracking, recent logs, history, and settings.

## Scope

The existing `/dashboard` URL remains the timer entry point after sign-in.

The application adds `/logs`, `/history`, and `/settings` as distinct static dashboard pages.

Every dashboard page displays the same application shell, including the BLT Timer brand, signed-in user identity, navigation, and logout control.

The current page is visually identified in the sidebar.

On desktop, the sidebar occupies the full viewport height and remains visible while page content scrolls.

On narrow screens, the sidebar becomes a compact horizontal navigation while retaining accessible labels and active state.

## Page Responsibilities

### Timer

The Timer page at `/dashboard` owns starting, pausing, resuming, and stopping an active work session.

It displays the existing daily and weekly statistics.

Stopping a session opens the save confirmation before the work log is created.

The timer state continues to use `localStorage` and remains active while the user navigates to another dashboard page.

### Recent Logs

The Recent Logs page at `/logs` displays the latest saved work logs as cards.

It supports creating a manual log, editing a log, and deleting a log.

Manual logging uses an editable form with start and end time controls instead of the current fixed thirty-minute default.

### History

The History page at `/history` owns the full work-log table.

It supports text search, date-range filtering, refreshing data, editing, deletion, CSV export, and JSON export.

### Settings

The Settings page at `/settings` displays account and privacy information.

It lets a signed-in user update the display name and timezone.

It provides export links and logout as account-level actions.

## Architecture

The frontend is split into a small shared dashboard shell module, common API and formatting helpers, and focused page modules.

Each static page declares its current page and loads the shared shell plus only the page behavior it needs.

The shell loads the authenticated user through `GET /api/me`, updates the header and sidebar identity, and redirects an unauthenticated visitor to `/login`.

Page modules request only the resources needed for their own view.

The Worker adds `PATCH /api/me` to update the current user’s display name and timezone after validating the payload.

The existing work-log and statistics endpoints remain unchanged.

## Data Flow and Failure Handling

The active timer remains in `localStorage` under the existing key and is never cleared by navigation.

The Timer page clears the active timer only after `POST /api/logs` succeeds.

Log edits and deletions refresh the current page data after a successful API response.

Settings updates refresh the visible user identity only after `PATCH /api/me` succeeds.

Forms retain their entered values when an API request fails.

Each page presents a specific, accessible error message and a retry control when its initial data request fails.

Destructive log deletion retains a confirmation step.

## Visual Direction

The application uses the existing BLT visual language.

The primary color remains BLT red `#dc2626`.

Pages use white surfaces, light gray backgrounds, quiet borders, and Inter typography.

The work does not introduce gradients.

The sidebar follows the approved reference with a compact brand block, icon-and-label navigation, red active indicator, a divider before account actions, and a circular user avatar.

## Verification

Automated tests cover the new profile update route, the dashboard page assets, route navigation, shared sidebar links, and the active-page markers.

The complete Python test suite and Python syntax checks must pass.

Browser verification covers authentication, timer state across navigation, saving a timer session, manual log creation, log edit and deletion, history filtering, settings update, logout, and the responsive navigation layout.
