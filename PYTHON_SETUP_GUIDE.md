# Python Server Setup Guide

## Current Status
✅ Core framework installed (FastAPI, WebSocket)  
❌ ML dependencies missing (ta, lightgbm, talib)

## Quick Start Options

### Option 1: Minimal Server (Works Now)
Install only essential dependencies:
```bash
uv pip install ta lightgbm
```
Then start server:
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)" && python src/helios_server.py
```

### Option 2: Full Server (Complete ML Features)
Install all dependencies:
```bash
uv pip install -r requirements.txt
```
This includes all ML libraries, technical analysis, and advanced features.

### Option 3: Gradual Setup
Start with basic server, then add features incrementally:
1. Install minimal dependencies
2. Test basic server functionality
3. Add advanced ML libraries as needed

## What the Server Provides
- 📊 **Web Dashboard** at http://localhost:8765
- 🔌 **WebSocket API** for real-time communication
- 📈 **Market data processing**
- 🤖 **ML model integration**
- 📱 **REST API endpoints**

## Testing the Server
Once dependencies are installed:
1. Start server: `export PYTHONPATH="${PYTHONPATH}:$(pwd)" && python src/helios_server.py`
2. Open browser: http://localhost:8765
3. Check for "Helios ML Trading System" dashboard

## Troubleshooting
If server won't start:
1. Check Python path: `echo $PYTHONPATH`
2. Verify dependencies: `python -c "import fastapi, uvicorn; print('OK')"`
3. Check logs for specific import errors
