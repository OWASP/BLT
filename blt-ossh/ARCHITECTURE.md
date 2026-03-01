# BLT-OSSH Architecture

This project follows a clean, scalable architecture inspired by NestJS, organized for maintainability and extensibility.

## 📁 Project Structure

```
src/
├── main.py                 # Application entry point
├── routers/                # Route handlers and endpoints
│   ├── __init__.py
│   └── api_router.py       # API route definitions
├── services/               # Business logic layer
│   ├── __init__.py
│   └── github_service.py   # GitHub API integration
├── models/                 # Data models and types
│   └── .gitkeep
├── middleware/             # Request/response middleware
│   └── .gitkeep
├── utils/                  # Utility functions and helpers
│   └── .gitkeep
├── config/                 # Configuration files
│   └── .gitkeep
└── pages/                  # HTML templates
    └── index.html
```

## 🏗️ Architecture Layers

### 1. Entry Point (`main.py`)
- **Purpose**: Application bootstrap and request routing
- **Responsibilities**:
  - Initialize routers and services
  - Route requests to appropriate handlers
  - Serve static HTML pages
  - Handle top-level errors

### 2. Routers (`routers/`)
- **Purpose**: HTTP request handling and response formatting
- **Responsibilities**:
  - Define API endpoints
  - Validate request data
  - Call appropriate services
  - Format responses
  - Handle HTTP-specific logic (status codes, headers)

### 3. Services (`services/`)
- **Purpose**: Business logic and external integrations
- **Responsibilities**:
  - Implement core business logic
  - Interact with external APIs (GitHub, etc.)
  - Process and transform data
  - Implement recommendation algorithms
  - Handle data validation

### 4. Models (`models/`)
- **Purpose**: Data structures and type definitions
- **Future Use**:
  - Define data models
  - Type hints and validation schemas
  - Data transfer objects (DTOs)

### 5. Middleware (`middleware/`)
- **Purpose**: Request/response processing pipeline
- **Future Use**:
  - Authentication and authorization
  - Request logging
  - CORS handling
  - Rate limiting

### 6. Utils (`utils/`)
- **Purpose**: Shared utility functions
- **Future Use**:
  - Helper functions
  - Data formatters
  - Common utilities

### 7. Config (`config/`)
- **Purpose**: Application configuration
- **Future Use**:
  - Environment-specific settings
  - API keys and secrets
  - Feature flags

## 🔄 Request Flow

```
1. Request → main.py (Entry Point)
2. main.py → routers/api_router.py (Route Handler)
3. api_router.py → services/github_service.py (Business Logic)
4. github_service.py → External API
5. Response ← (bubble back up through layers)
```

## 📝 Code Organization Principles

1. **Separation of Concerns**: Each layer has a specific responsibility
2. **Dependency Injection**: Services are injected into routers
3. **Scalability**: Easy to add new routes, services, or features
4. **Maintainability**: Clear structure makes code easy to understand
5. **Testability**: Layers can be tested independently

## 🚀 Adding New Features

### Adding a New API Endpoint
1. Create a new method in appropriate router (`routers/`)
2. Create/update service in `services/` for business logic
3. Update route handler in `main.py` if needed

### Adding a New Service
1. Create new service file in `services/`
2. Export it in `services/__init__.py`
3. Inject it into router or other services

### Adding Middleware
1. Create middleware function in `middleware/`
2. Apply it in `main.py` or specific routes

## 🔧 Best Practices

- Keep routers thin - delegate to services
- Keep services focused - single responsibility
- Use type hints for better code clarity
- Document public methods with docstrings
- Handle errors at appropriate layers
- Use async/await for I/O operations

## 📚 Further Reading

- [Cloudflare Workers Python Docs](https://developers.cloudflare.com/workers/languages/python/)
- [Clean Architecture Principles](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
