# BLT NetGuardian Client Screenshots

## Application Overview

The BLT NetGuardian Client is a Flutter application with a modern Material Design 3 interface that provides a comprehensive dashboard for security scanning and vulnerability management.

## Main Interface

### Navigation Structure
The application features a bottom navigation bar with four main sections:

1. **Dashboard** (Home Icon)
   - Real-time statistics and metrics
   - Task counts by status (Pending, Running, Completed, Failed)
   - Target counts by type (Website, Smart Contract, API, Repository)
   - Result counts by processing state
   - Vulnerability counts by severity (Critical, High, Medium, Low)

2. **Tasks** (List Icon)
   - View all security scanning tasks
   - Filter tasks by status
   - Queue new tasks with the floating action button (+)
   - Task cards showing:
     - Task type (web2Crawler, web3Monitor, etc.)
     - Target URL
     - Status with color-coded indicators
     - Timestamps

3. **Targets** (Target Icon)
   - Manage scan targets
   - View registered targets by type
   - Register new targets with the floating action button (+)
   - Target cards displaying:
     - URL/Address
     - Target type
     - Active/Inactive status

4. **Results** (Chart Icon)
   - Two sub-tabs: Results and Vulnerabilities
   - **Results Tab**: Agent scan results with processing status
   - **Vulnerabilities Tab**: Discovered vulnerabilities with:
     - Severity badges (color-coded)
     - Vulnerability titles and descriptions
     - Agent type that discovered them
     - Timestamps

## Configuration Dialog

On first launch, users see a configuration dialog:
- Input field for API base URL
- Default: `https://api.netguardian.example.com`
- "Connect" button to initialize the client
- Settings icon in app bar to reconfigure later

## Color Scheme

- **Primary Color**: Blue (Material Design 3)
- **Theme Support**: Light and Dark modes (follows system preferences)
- **Status Indicators**:
  - Pending: Orange
  - Running: Blue
  - Completed: Green
  - Failed: Red
- **Severity Indicators**:
  - Critical: Red
  - High: Orange
  - Medium: Yellow
  - Low: Blue

## Key Features Visible in UI

1. **Floating Action Buttons**: Present in Tasks and Targets screens for quick addition
2. **Pull-to-Refresh**: Available on all list screens
3. **Filtering**: Dropdown filters for status and type
4. **Empty States**: Helpful messages when no data is available
5. **Loading States**: Progress indicators during data fetch
6. **Error Handling**: User-friendly error messages via SnackBars

## Technical Details

- **Framework**: Flutter 3.0+
- **Design**: Material Design 3
- **State Management**: Provider pattern
- **Responsive**: Adapts to different screen sizes

## Note

To see the actual application running, execute:
```bash
flutter run
```

For web preview:
```bash
flutter run -d chrome
```

---

*Screenshots will be added once the application is deployed to a device or emulator.*