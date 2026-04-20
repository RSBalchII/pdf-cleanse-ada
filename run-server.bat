@echo off
REM PDF ADA Processor - Web Server Launcher with Auto-Setup

echo ================================================
echo PDF ADA Processor - AutoTagging Tool
echo ================================================

echo Checking for Node.js...
where node >nul 2>nul
if errorlevel neq 0 (
    echo ERROR: Node.js not found!
    echo Please install Node.js from https://www.nodejs.io/
    pause
    exit /b
)

echo Checking virtual environment...
if exist .venv\Scripts\python.exe (
    echo Using cached Python environment (.venv) ...
) else (
    echo Creating new virtual environment for Python dependencies...
    python -m venv .venv
    pip install -r requirements.txt
)

echo Starting server on http://localhost:3456...
node server.js