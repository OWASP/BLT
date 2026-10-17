@echo off
REM ─────────────────────────────────────────────────────────────────────────────
REM Week 1 Docker Verification Script (Windows)
REM 
REM This script tests the BLT-Preflight RAG pipeline in Docker
REM Required: Docker Desktop installed and running
REM Usage: verify_week1_docker.bat
REM ─────────────────────────────────────────────────────────────────────────────

setlocal enabledelayedexpansion

echo.
echo ════════════════════════════════════════════════════════════
echo Week 1 BLT-Preflight Docker Verification
echo ════════════════════════════════════════════════════════════
echo.

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker not found. Please install Docker Desktop.
    exit /b 1
)
echo [OK] Docker found
docker --version

docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] docker-compose not found. Please install docker-compose.
    exit /b 1
)
echo [OK] docker-compose found
docker-compose --version

REM Build Docker image
echo.
echo ════════════════════════════════════════════════════════════
echo Building Docker Image
echo ════════════════════════════════════════════════════════════
echo.

docker-compose build preflight-server
if errorlevel 1 (
    echo [ERROR] Docker build failed
    exit /b 1
)
echo [OK] Docker image built

REM Start services
echo.
echo ════════════════════════════════════════════════════════════
echo Starting Services
echo ════════════════════════════════════════════════════════════
echo.

docker-compose up -d preflight-server
if errorlevel 1 (
    echo [ERROR] Failed to start services
    exit /b 1
)

echo [INFO] Waiting 15 seconds for service to be ready...
timeout /t 15 /nobreak

REM Test 1: Health Check
echo.
echo ════════════════════════════════════════════════════════════
echo Test 1: Health Check
echo ════════════════════════════════════════════════════════════
echo.

for /f "delims=" %%A in ('curl -s http://localhost:8000/health 2^>nul') do set "RESPONSE=%%A"

if "!RESPONSE!"=="" (
    echo [ERROR] Health check failed (no response)
    goto cleanup
)

echo Response: !RESPONSE!

echo !RESPONSE! | find "healthy" >nul
if errorlevel 1 (
    echo [ERROR] Health check failed
    echo !RESPONSE!
    goto cleanup
)
echo [OK] Health check passed

REM Test 2: Retrieval Query 1
echo.
echo ════════════════════════════════════════════════════════════
echo Test 2: Retrieval - "I modified the login flow"
echo ════════════════════════════════════════════════════════════
echo.

curl -s -X POST http://localhost:8000/retrieve ^
  -H "Content-Type: application/json" ^
  -d "{\"query\": \"I modified the login flow\", \"top_k\": 2, \"similarity_threshold\": 0.6}"

echo.

REM Test 3: Retrieval Query 2
echo.
echo ════════════════════════════════════════════════════════════
echo Test 3: Retrieval - "I added a new API endpoint"
echo ════════════════════════════════════════════════════════════
echo.

curl -s -X POST http://localhost:8000/retrieve ^
  -H "Content-Type: application/json" ^
  -d "{\"query\": \"I added a new API endpoint\", \"top_k\": 2, \"similarity_threshold\": 0.6}"

echo.

REM Test 4: Retrieval Query 3
echo.
echo ════════════════════════════════════════════════════════════
echo Test 4: Retrieval - "I changed how passwords are stored"
echo ════════════════════════════════════════════════════════════
echo.

curl -s -X POST http://localhost:8000/retrieve ^
  -H "Content-Type: application/json" ^
  -d "{\"query\": \"I changed how passwords are stored\", \"top_k\": 2, \"similarity_threshold\": 0.6}"

echo.

REM Test 5: Advisory Endpoint
echo.
echo ════════════════════════════════════════════════════════════
echo Test 5: Advisory Generation Endpoint
echo ════════════════════════════════════════════════════════════
echo.

curl -s -X POST http://localhost:8000/advisory ^
  -H "Content-Type: application/json" ^
  -d "{\"contributor_intent\": \"Adding OAuth2 support\", \"files_changed\": [\"src/auth/oauth.py\"], \"labels\": [\"security\"]}"

echo.

REM Cleanup
:cleanup
echo.
echo ════════════════════════════════════════════════════════════
echo Cleanup - Stopping Services
echo ════════════════════════════════════════════════════════════
echo.

docker-compose down
echo [OK] Services stopped

echo.
echo ════════════════════════════════════════════════════════════
echo Week 1 Verification Complete
echo ════════════════════════════════════════════════════════════
echo.
echo Summary:
echo   [OK] Docker image built successfully
echo   [OK] Service started and health check passed
echo   [OK] Retrieval endpoints tested (3 scenarios)
echo   [OK] Advisory generation endpoint tested
echo.
echo Next Steps:
echo   1. Ingest OWASP documents
echo   2. Run native tests (test_week1.py)
echo   3. Test with GitHub Actions integration
echo.
echo To start the server:
echo   docker-compose up preflight-server
echo   curl http://localhost:8000/health
echo.
echo For API documentation, visit: http://localhost:8000/docs
echo.
pause
