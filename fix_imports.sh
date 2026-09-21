#!/bin/bash
# Quick Fix Script for Helios ML Trading System Python Dependencies

echo "🔧 Helios ML Trading System - Quick Fix Script"
echo "=============================================="

# Check if we're on macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "🍎 Detected macOS - Installing macOS-specific fixes..."
    
    # Check if Homebrew is installed
    if ! command -v brew &> /dev/null; then
        echo "❌ Homebrew not found. Installing Homebrew first..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    
    # Install libomp for LightGBM
    echo "📦 Installing libomp for LightGBM..."
    brew install libomp
    
    # Verify libomp installation
    if [ -f "/opt/homebrew/opt/libomp/lib/libomp.dylib" ]; then
        echo "✅ libomp installed successfully"
    else
        echo "⚠️  libomp may need manual setup"
    fi
else
    echo "🖥️  Non-macOS detected - skipping macOS-specific fixes"
fi

echo ""
echo "🐍 Installing Python packages..."

# Install MetaTrader5
echo "📡 Installing MetaTrader5..."
uv pip install MetaTrader5

# Reinstall LightGBM to ensure proper dependencies
echo "🤖 Reinstalling LightGBM..."
uv pip uninstall lightgbm -y
uv pip install lightgbm

# Install other dependencies
echo "📚 Installing remaining dependencies..."
uv pip install -r requirements.txt

echo ""
echo "🧪 Testing imports..."
python test_imports.py

echo ""
echo "✨ Fix script completed!"
echo ""
echo "If imports still fail, try:"
echo "1. Restart virtual environment: deactivate && source venv/bin/activate"
echo "2. Run this script again"
echo "3. Check PYTHON_FIX_GUIDE.md for detailed solutions"
