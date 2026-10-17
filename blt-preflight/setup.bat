@echo off
REM BLT-Preflight Native Installation Script for Windows

echo ======================================
echo BLT-Preflight Advisory System Setup
echo ======================================
echo.

REM Check for Python 3
echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.9 or higher from https://www.python.org
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Found Python %PYTHON_VERSION%

REM Create virtual environment
echo.
echo Creating virtual environment...
if exist venv (
    echo Virtual environment already exists. Removing...
    rmdir /s /q venv
)

python -m venv venv
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment.
    exit /b 1
)

call venv\Scripts\activate.bat
echo [OK] Virtual environment created and activated

REM Upgrade pip
echo.
echo Upgrading pip...
python -m pip install --upgrade pip setuptools wheel
if errorlevel 1 (
    echo [ERROR] Failed to upgrade pip.
    exit /b 1
)
echo [OK] pip upgraded

REM Install dependencies
echo.
echo Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    exit /b 1
)
echo [OK] Dependencies installed

REM Create necessary directories
echo.
echo Creating directories...
if not exist "knowledge_base\owasp_corpus" mkdir knowledge_base\owasp_corpus
if not exist "chroma_db" mkdir chroma_db
if not exist "logs" mkdir logs
echo [OK] Directories created

REM Initialize knowledge base
echo.
echo Initializing knowledge base...
python -m src.advisory_engine.rag.retrieval
if errorlevel 1 (
    echo [WARNING] Knowledge base initialization had issues, but continuing...
)
echo [OK] Knowledge base initialization complete

echo.
echo ======================================
echo [OK] Setup Complete!
echo ======================================
echo.
echo To start the server, run:
echo   venv\Scripts\activate.bat
echo   python -m uvicorn src.advisory_server:app --host 0.0.0.0 --port 8000
echo.
echo To test the API, visit:
echo   http://localhost:8000/docs
echo.
echo To check server health, use:
echo   curl http://localhost:8000/health
echo.

pause
