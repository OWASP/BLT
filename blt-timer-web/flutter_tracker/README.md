# Flutter Activity Tracker

> A native Linux desktop application (part of the Fresh project) that provides real-time keyboard & mouse activity tracking, visual dashboards, daily summaries, and optional server integration — all with strict privacy guarantees.

## Table of Contents
1. [Project Summary](#project-summary)
2. [Features](#features)
3. [Architecture](#architecture)
4. [Setup & Installation](#setup--installation)
5. [Usage](#usage)
6. [Integration Guide](#integration-guide)
7. [Performance](#performance)
8. [Dependencies](#dependencies)
9. [Privacy & Security](#privacy--security)
10. [Troubleshooting](#troubleshooting)
11. [Future Enhancements](#future-enhancements)
12. [Contributing](#contributing)
13. [License & Acknowledgments](#license--acknowledgments)

---

## Project Summary

The tracker is a Flutter desktop application using a native X11/XInput2 C library for low‑overhead event capture. It displays live charts, real-time counters, and cumulative daily stats while keeping all raw input private (aggregate counts only). Designed to be compact and optionally push anonymized activity summaries to the Fresh backend.

## Features

### Real-time Tracking
- Keyboard key press counting (per second/minute + daily total)
- Mouse movement distance aggregation
- Scroll wheel step tracking (direction-agnostic total)
- Left & right click counts and rates

### Visual Dashboard
- Real-time stat cards & compact chips
- Per-second & cumulative charts (keys, clicks, scroll, mouse distance)
- 60-second rolling history with smooth updates
- Centered bar visualization for scroll activity

### Daily Summaries
- Persistent totals (keys, mouse distance, clicks, scroll steps)
- Manual reset button; auto-save intervals

### Integration (Optional)
- Session start/end + streaming activity payloads to Fresh Worker
- Configurable `apiUrl`, `userId`, `projectId`

### Privacy
- No keystroke contents, no mouse coordinates, no window/app names, no screenshots
- Aggregate numeric metrics only

## Architecture

```
flutter_tracker/
├── lib/
│   ├── main.dart                # UI entry point & dashboard
│   ├── activity_service.dart    # Polling, aggregation & rate computation
│   ├── native_tracker.dart      # FFI bindings to C layer
│   ├── storage_service.dart     # Local persistence (daily/history)
│   ├── tracker_integration.dart # Optional API integration
│   └── ...                      # Additional helpers
├── linux/
│   ├── activity_tracker.c       # X11/XInput2 raw event capture
│   ├── activity_tracker.h       # Native interface
│   ├── build.sh                 # Builds shared library
│   └── libactivity_tracker.so   # Output artifact
├── README.md                    # (This file)
├── SETUP.md                     # Detailed setup steps
├── INTEGRATION.md               # API usage & payload formats
└── PROJECT_SUMMARY.md           # Extended narrative & roadmap
```

### Data Flow
X11 Events → Native C Aggregation → FFI Poll (10ms) → ActivityService (1s updates) → UI Widgets / Charts → (Optional) HTTP POST to Fresh backend.

## Setup & Installation

### System Requirements
- Linux (X11; Wayland supported via XWayland fallback)
- Flutter SDK ≥ 3.0
- Packages: `libx11-dev libxtst-dev libxi-dev build-essential`

### Quick Install
```bash
sudo apt-get update
sudo apt-get install -y libx11-dev libxtst-dev libxi-dev build-essential
```

### Flutter Environment
```bash
git clone https://github.com/flutter/flutter.git -b stable
export PATH="$PATH:$HOME/flutter/bin"
flutter doctor
flutter config --enable-linux-desktop
```

### Build & Run (Manual)
```bash
cd flutter_tracker/linux
./build.sh
cd ..
flutter pub get
flutter run -d linux
```

## Usage
1. Launch the app (`flutter run -d linux` or packaged build).
2. Observe real-time counters & charts updating each second.
3. Use reset control to clear daily aggregates.
4. (Optional) Configure integration to push session data to Fresh backend.

## Integration Guide

Add dependency:
```yaml
dependencies:
	http: ^1.1.0
```

Initialize in `main.dart`:
```dart
_integration = TrackerIntegration(
	apiUrl: 'https://your-worker.workers.dev',
	userId: 'user-123',
	projectId: 'project-456',
);
await _integration.startSession();
// on each update:
_integration.sendActivityData(data);
```

API endpoints:
- `POST /api/sessions/start`
- `POST /api/activity`
- `POST /api/sessions/end`

Example payload:
```json
{
	"sessionId": "uuid",
	"userId": "user-123",
	"projectId": "project-456",
	"activity": { "keyboard": { "keyCount": 150 }, "mouse": { "distance": 2500.5 } },
	"timestamp": "2025-11-22T12:34:56.789Z"
}
```

## Performance
- CPU: <1% typical
- Memory: ~50–80MB
- Event Poll: 10ms cycle
- UI Update: 1 Hz (per-second aggregation)
- Chart Animations: Smooth at desktop refresh rates

## Dependencies
System: `libx11-dev`, `libxi-dev`, `libxtst-dev`, `build-essential`
Flutter Packages: `fl_chart`, `shared_preferences`, `intl`, `ffi`, `http`

## Privacy & Security
Tracked: counts (keys, clicks), distances, aggregated scroll, timestamps.
Not Tracked: keystroke content, cursor positions, window titles, screenshots, network usage.
All data local unless integration enabled; HTTPS for outbound requests.

## Troubleshooting
| Issue | Solution |
|-------|----------|
| Cannot open display | Ensure X11 session: `echo $DISPLAY` |
| X Input extension missing | `sudo apt-get install xinput` |
| Native library not found | Run `linux/build.sh` |
| Permission denied | Verify user can access X display |

More detail in `SETUP.md`.

## Future Enhancements
- Wayland native backend
- System tray quick stats
- Extended time ranges & historical analytics
- Weekly/monthly reports & goal tracking
- Dark mode & theming
- CSV/JSON export
- App context breakdown
- Focus / break reminders

## Contributing
1. Maintain privacy boundaries (no raw input storage).
2. Keep CPU overhead minimal.
3. Update docs when adding metrics or integration points.
4. Test across multiple distros and X11 setups.

## License & Acknowledgments
Licensed under MIT (see root project license). Thanks to Flutter, fl_chart, X.Org, and the OWASP-BLT community.

---
Combined from: `README.md`, `SETUP.md`, `INTEGRATION.md`, `PROJECT_SUMMARY.md`. Last updated: 2025-11-22.
