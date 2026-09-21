#!/bin/bash
# Helios ML Trading System - Quick Start Script

echo "🚀 Helios ML Trading System - Quick Start"
echo "=========================================="

# Check if we're in the right directory
if [ ! -f "config/config.json" ]; then
    echo "❌ Error: Please run this script from the helios-ml-trading-system directory"
    echo "Current directory: $(pwd)"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Run import test
echo "🧪 Testing imports..."
python test_imports.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ All tests passed! Starting Helios Server..."
    echo ""
    echo "🌐 The web dashboard will be available at: http://localhost:8765"
    echo "⚠️  Remember to:"
    echo "   1. Edit config/config.json with your MT5 credentials"
    echo "   2. Copy deployed/HeliosML_EA.mq5 to MT5 Experts folder"
    echo "   3. Start MetaTrader 5 and attach the EA"
    echo ""
    
    # Start the server
    python src/helios_server.py
else
    echo "❌ Import tests failed. Please fix the errors before running."
    exit 1
fi