# BLT NetGuardian Client

A Flutter client application for the BLT NetGuardian security platform. This client interfaces with Cloudflare Worker APIs to coordinate security scans, vulnerability detection, and monitoring across Web2, Web3, and smart contract ecosystems.

## Features

- **Task Queue Management**: Queue and monitor security scanning tasks
- **Target Registration**: Register and manage scan targets (websites, smart contracts, APIs, repositories)
- **Agent Result Ingestion**: Receive and process results from various security agents
- **Job State Management**: Track task states with real-time updates
- **Task Deduplication**: Automatically prevent duplicate scan tasks
- **Vulnerability Dashboard**: View and filter discovered vulnerabilities
- **Multi-Agent Support**: Coordinate Web2 crawlers, Web3 monitors, static analyzers, contract scanners, and volunteer agents

## Architecture

The client interfaces with the following Cloudflare Worker API endpoints:

### Task Queue Endpoints
- `POST /api/tasks/queue` - Queue a new task
- `GET /api/tasks` - List all tasks (with optional status filter)
- `GET /api/tasks/:id` - Get specific task details

### Target Registration Endpoints
- `POST /api/targets/register` - Register a new scan target
- `GET /api/targets` - List all targets (with optional isActive filter)
- `GET /api/targets/:id` - Get specific target details
- `DELETE /api/targets/:id` - Deactivate a target

### Agent Result Ingestion Endpoints
- `POST /api/results/ingest` - Submit agent scan results
- `GET /api/results` - List all results (with optional taskId filter)
- `GET /api/results/:id` - Get specific result details

## Project Structure

```
lib/
├── models/              # Data models
│   ├── task.dart       # Task and TaskStatus models
│   ├── target.dart     # Target and TargetType models
│   └── agent_result.dart # AgentResult and Vulnerability models
├── services/           # Business logic layer
│   ├── api_service.dart      # HTTP API client
│   ├── task_manager.dart     # Task management with deduplication
│   ├── target_manager.dart   # Target management
│   └── result_manager.dart   # Result and vulnerability management
├── providers/          # State management
│   ├── app_provider.dart     # App-level state
│   ├── task_provider.dart    # Task state
│   ├── target_provider.dart  # Target state
│   └── result_provider.dart  # Result state
├── screens/            # UI screens
│   ├── home_screen.dart      # Main navigation
│   ├── dashboard_screen.dart # Statistics dashboard
│   ├── tasks_screen.dart     # Task management
│   ├── targets_screen.dart   # Target management
│   └── results_screen.dart   # Results and vulnerabilities
└── main.dart           # Application entry point
```

## Getting Started

### Prerequisites

- Flutter SDK (3.0.0 or later)
- Dart SDK (3.0.0 or later)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/OWASP-BLT/BLT-NetGuardian-Client.git
cd BLT-NetGuardian-Client
```

2. Install dependencies:
```bash
flutter pub get
```

3. Run the application:
```bash
flutter run
```

### Configuration

On first launch, you'll be prompted to configure the API endpoint:

1. Enter your Cloudflare Worker API base URL (e.g., `https://api.netguardian.example.com`)
2. Click "Connect" to initialize the client

You can change the API endpoint later via the Settings button in the app bar.

## Usage

### Queueing Tasks

1. Navigate to the "Tasks" tab
2. Click the "+" button
3. Enter task type (e.g., `web2Crawler`, `web3Monitor`, `staticAnalyzer`, `contractScanner`, `volunteerAgent`)
4. Enter the target URL
5. Click "Queue"

Tasks are automatically deduplicated based on type, target, and parameters.

### Registering Targets

1. Navigate to the "Targets" tab
2. Click the "+" button
3. Enter the target URL
4. Select the target type (Website, Smart Contract, API, or Repository)
5. Click "Register"

### Viewing Results

1. Navigate to the "Results" tab
2. View the "Results" sub-tab for agent scan results
3. View the "Vulnerabilities" sub-tab for discovered vulnerabilities
4. Filter by severity, agent type, or task

### Dashboard

The Dashboard tab provides real-time statistics:
- Task counts by status
- Target counts by type and status
- Result counts by processing state
- Vulnerability counts by severity

## Task Types

The client supports the following task types:

- **web2Crawler**: Traditional web application crawling and scanning
- **web3Monitor**: Web3/blockchain monitoring and analysis
- **staticAnalyzer**: Static code analysis
- **contractScanner**: Smart contract security scanning
- **volunteerAgent**: Community-contributed security agents

## Task Deduplication

The client automatically prevents duplicate tasks using a hash-based system:
- Hash is computed from: `type:target:parameters`
- Duplicate tasks are rejected with `DuplicateTaskException`
- Cache is maintained locally and synced with the server

## Development

### Running Tests

```bash
flutter test
```

### Linting

```bash
flutter analyze
```

### Building

For production builds:

```bash
# Android
flutter build apk

# iOS
flutter build ios

# Web
flutter build web

# Desktop
flutter build windows
flutter build macos
flutter build linux
```

## Dependencies

- `http`: HTTP client for API communication
- `provider`: State management
- `shared_preferences`: Local data persistence
- `uuid`: Unique identifier generation
- `intl`: Internationalization support

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Security

This client is part of the OWASP BLT (Bug Logging Tool) project. If you discover a security vulnerability, please report it through the OWASP BLT platform.

## Support

For issues, questions, or contributions, please visit:
- [GitHub Issues](https://github.com/OWASP-BLT/BLT-NetGuardian-Client/issues)
- [OWASP BLT Project](https://owasp.org/www-project-bug-logging-tool/)

## Acknowledgments

- OWASP Foundation
- BLT Community Contributors
- Flutter and Dart teams