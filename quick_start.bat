@echo off
REM Helios ML Trading System - Quick Start Script for Windows

echo 🚀 Helios ML Trading System - Quick Start
echo ==========================================

REM Check if we're in the right directory
if not exist "config\config.json" (
    echo ❌ Error: Please run this script from the helios-ml-trading-system directory
    echo Current directory: %CD%
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv" (
    echo 📦 Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo 🔄 Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo 📚 Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

REM Run import test
echo 🧪 Testing imports...
python test_imports.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ All tests passed! Starting Helios Server...
    echo.
    echo 🌐 The web dashboard will be available at: http://localhost:8765
    echo ⚠️  Remember to:
    echo    1. Edit config\config.json with your MT5 credentials
    echo    2. Copy deployed\HeliosML_EA.mq5 to MT5 Experts folder
    echo    3. Start MetaTrader 5 and attach the EA
    echo.
    
    REM Start the server
    python src\helios_server.py
) else (
    echo ❌ Import tests failed. Please fix the errors before running.
    pause
    exit /b 1
)

pause