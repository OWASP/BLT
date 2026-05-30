# Architecture

This document describes the architecture of the BLT NetGuardian Client.

## Overview

The BLT NetGuardian Client is a Flutter application that provides a user interface for interacting with the NetGuardian security platform. It follows a clean architecture pattern with clear separation of concerns.

## Architecture Layers

### 1. Presentation Layer (UI)

**Location**: `lib/screens/` and `lib/widgets/`

The presentation layer consists of Flutter widgets that render the user interface. It uses the Provider pattern for state management.

#### Screens

- `HomeScreen`: Main navigation container
- `DashboardScreen`: Statistics and overview
- `TasksScreen`: Task management interface
- `TargetsScreen`: Target management interface
- `ResultsScreen`: Results and vulnerabilities display

### 2. State Management Layer

**Location**: `lib/providers/`

The state management layer uses the Provider package to manage application state and coordinate between the UI and business logic layers.

#### Providers

- `AppProvider`: Application-level state (initialization, configuration)
- `TaskProvider`: Task state management
- `TargetProvider`: Target state management
- `ResultProvider`: Result and vulnerability state management

### 3. Business Logic Layer

**Location**: `lib/services/`

The business logic layer contains the core application logic, including task deduplication, caching, and coordination between components.

#### Services

- `TaskManager`: Task queue management with deduplication
- `TargetManager`: Target registration and management
- `ResultManager`: Result ingestion and vulnerability tracking

### 4. Data Layer

**Location**: `lib/services/api_service.dart` and `lib/models/`

The data layer handles API communication and data models.

#### API Service

- `ApiService`: HTTP client for Cloudflare Worker API
  - Task endpoints
  - Target endpoints
  - Result endpoints

#### Models

- `Task`: Task data model with serialization
- `Target`: Target data model with serialization
- `AgentResult`: Result data model with serialization
- `Vulnerability`: Vulnerability data model with serialization

## Data Flow

```
┌─────────────────────────────────────────────────────┐
│                   Presentation Layer                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │ Tasks UI │  │Targets UI│  │Results UI│          │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘          │
└───────┼─────────────┼─────────────┼─────────────────┘
        │             │             │
┌───────┼─────────────┼─────────────┼─────────────────┐
│       │    State Management Layer │                  │
│  ┌────▼────┐  ┌────▼────┐  ┌─────▼───┐             │
│  │  Task   │  │ Target  │  │ Result  │             │
│  │Provider │  │Provider │  │Provider │             │
│  └────┬────┘  └────┬────┘  └────┬────┘             │
└───────┼────────────┼────────────┼──────────────────┘
        │            │            │
┌───────┼────────────┼────────────┼──────────────────┐
│       │   Business Logic Layer  │                   │
│  ┌────▼────┐  ┌───▼─────┐ ┌────▼─────┐            │
│  │  Task   │  │ Target  │ │  Result  │            │
│  │ Manager │  │ Manager │ │ Manager  │            │
│  └────┬────┘  └────┬────┘ └────┬─────┘            │
└───────┼────────────┼───────────┼───────────────────┘
        │            │           │
        └────────────┼───────────┘
                     │
┌────────────────────▼──────────────────────────────┐
│               Data Layer                          │
│  ┌─────────────────────────────────────────────┐ │
│  │           API Service (HTTP Client)         │ │
│  └──────────────────┬──────────────────────────┘ │
│                     │                             │
│  ┌──────────────────▼──────────────────────────┐ │
│  │    Cloudflare Worker API Endpoints          │ │
│  │  • /api/tasks/*                              │ │
│  │  • /api/targets/*                            │ │
│  │  • /api/results/*                            │ │
│  └──────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────┘
```

## Key Features Implementation

### Task Deduplication

Task deduplication is implemented in `TaskManager`:

1. Generate hash from task type, target, and parameters
2. Store hashes in a Set for O(1) lookup
3. Check hash before queueing new tasks
4. Throw `DuplicateTaskException` if duplicate detected

```dart
String _generateTaskHash(String type, String target, Map<String, dynamic> parameters) {
  final sortedParams = SplayTreeMap<String, dynamic>.from(parameters);
  return '$type:$target:${sortedParams.toString()}';
}
```

### Local Caching

Each manager maintains a local cache:

- `TaskManager`: Caches tasks by ID and tracks hashes
- `TargetManager`: Caches targets by ID and tracks URLs
- `ResultManager`: Caches results by ID

Caching reduces API calls and improves performance.

### State Management

The application uses Provider for state management:

1. Providers wrap managers and expose state to UI
2. `notifyListeners()` triggers UI updates
3. `Consumer` widgets rebuild when state changes

### Error Handling

Error handling is implemented at multiple levels:

1. **API Level**: `ApiException` for HTTP errors
2. **Manager Level**: `DuplicateTaskException`, `DuplicateTargetException`
3. **Provider Level**: Error messages stored in provider state
4. **UI Level**: Error display and retry mechanisms

## API Endpoints

### Task Endpoints

- `POST /api/tasks/queue` - Queue new task
- `GET /api/tasks` - List tasks (with optional status filter)
- `GET /api/tasks/:id` - Get task details

### Target Endpoints

- `POST /api/targets/register` - Register new target
- `GET /api/targets` - List targets (with optional isActive filter)
- `GET /api/targets/:id` - Get target details
- `DELETE /api/targets/:id` - Deactivate target

### Result Endpoints

- `POST /api/results/ingest` - Ingest agent results
- `GET /api/results` - List results (with optional taskId filter)
- `GET /api/results/:id` - Get result details

## Design Patterns

### Repository Pattern

Managers act as repositories, providing a clean API for data access and hiding implementation details.

### Observer Pattern

Providers use the observer pattern to notify listeners of state changes.

### Singleton Pattern

`ApiService` instances are created once per initialization and reused.

### Factory Pattern

Models use factory constructors for JSON deserialization.

## Testing Strategy

### Unit Tests

- Model serialization/deserialization
- Manager business logic
- Deduplication algorithms

### Widget Tests

- Screen rendering
- User interactions
- State updates

### Integration Tests

- End-to-end workflows
- API communication
- Error handling

## Security Considerations

1. **API Communication**: All API calls use HTTPS
2. **Error Messages**: Sensitive data not exposed in error messages
3. **Input Validation**: Parameters validated before API calls
4. **State Management**: Providers isolate state and prevent direct mutations

## Performance Optimizations

1. **Local Caching**: Reduces API calls
2. **Lazy Loading**: Data loaded on demand
3. **Pagination**: Support for paginated API responses
4. **Debouncing**: Prevents excessive API calls

## Future Enhancements

1. **Offline Support**: Queue tasks offline and sync later
2. **Push Notifications**: Real-time updates for task completion
3. **Advanced Filtering**: More sophisticated query capabilities
4. **Export/Import**: Save and restore configurations
5. **Multi-tenancy**: Support for multiple organizations
6. **Analytics**: Usage tracking and reporting