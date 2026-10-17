# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-12-12

### Added

#### Core Features
- Complete Flutter client application for BLT NetGuardian platform
- Task queue management with automatic deduplication
- Target registration and management system
- Agent result ingestion and processing
- Job state management and tracking
- Vulnerability dashboard with severity filtering

#### API Integration
- RESTful API client for Cloudflare Worker endpoints
- Task queueing endpoints (`POST /api/tasks/queue`, `GET /api/tasks`)
- Target registration endpoints (`POST /api/targets/register`, `GET /api/targets`)
- Result ingestion endpoints (`POST /api/results/ingest`, `GET /api/results`)
- Proper error handling and exception management

#### Data Models
- `Task` model with status tracking and serialization
- `Target` model with type classification
- `AgentResult` model with findings and vulnerabilities
- `Vulnerability` model with severity levels and CVE/CWE support
- Support for multiple task types (Web2, Web3, Static Analysis, Contract Scanning)

#### Services
- `ApiService` - HTTP client with proper headers and error handling
- `TaskManager` - Task management with deduplication logic
- `TargetManager` - Target registration with URL tracking
- `ResultManager` - Result ingestion and vulnerability aggregation

#### State Management
- Provider-based state management
- `AppProvider` - Application-level state
- `TaskProvider` - Task state with statistics
- `TargetProvider` - Target state with filtering
- `ResultProvider` - Result and vulnerability state

#### User Interface
- `HomeScreen` - Main navigation with bottom bar
- `DashboardScreen` - Statistics overview with real-time metrics
- `TasksScreen` - Task management with filtering and creation
- `TargetsScreen` - Target management with type selection
- `ResultsScreen` - Results and vulnerabilities with tabs
- Material Design 3 with dark theme support
- Responsive layout for different screen sizes

#### Task Deduplication
- Hash-based deduplication algorithm
- Parameter-sorted hash generation for consistency
- Duplicate detection before API calls
- Option to skip deduplication when needed

#### Error Handling
- Custom exceptions (`DuplicateTaskException`, `DuplicateTargetException`, `ApiException`)
- User-friendly error messages
- Retry mechanisms in UI
- Proper error propagation through layers

#### Documentation
- Comprehensive README with setup instructions
- API documentation with endpoint details
- Architecture documentation with diagrams
- Contributing guidelines
- Example code and configuration
- Code documentation and comments

#### Testing
- Unit tests for models
- Unit tests for task manager
- Test infrastructure setup
- Mock HTTP client for testing

#### Configuration
- Environment-based configuration support
- Configurable API base URL
- Flutter lints configuration
- Git ignore rules for Flutter projects

### Technical Details

#### Dependencies
- `flutter`: SDK
- `http`: ^1.1.0 - HTTP client
- `provider`: ^6.1.1 - State management
- `shared_preferences`: ^2.2.2 - Local storage
- `uuid`: ^4.2.2 - UUID generation
- `intl`: ^0.19.0 - Internationalization

#### Development Dependencies
- `flutter_test`: SDK - Testing framework
- `flutter_lints`: ^3.0.0 - Linting rules

#### Project Structure
```
lib/
├── models/              # Data models
├── services/            # Business logic
├── providers/           # State management
├── screens/             # UI screens
└── main.dart            # Entry point

test/
├── models/              # Model tests
└── services/            # Service tests

example/
├── api_examples.md      # Usage examples
└── config_example.dart  # Configuration examples
```

#### Supported Platforms
- Android
- iOS
- Web
- Windows
- macOS
- Linux

### Notes
- This is the initial release of the BLT NetGuardian Client
- The Cloudflare Worker API is in a separate repository
- Future versions will add offline support and push notifications

[1.0.0]: https://github.com/OWASP-BLT/BLT-NetGuardian-Client/releases/tag/v1.0.0