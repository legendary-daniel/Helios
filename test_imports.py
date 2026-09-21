#!/usr/bin/env python3
"""
Test script to verify all imports are working correctly
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test all critical imports"""
    print("🧪 Testing Helios ML Trading System imports...")
    print(f"📁 Project root: {project_root}")
    print(f"🐍 Python path: {sys.path[0]}")
    print()
    
    tests = []
    
    # Test 1: Config import
    try:
        from config.config import config
        print("✅ Config import successful")
        tests.append(True)
    except Exception as e:
        print(f"❌ Config import failed: {e}")
        tests.append(False)
    
    # Test 2: Data Processor
    try:
        from src.data_processor import DataProcessor
        print("✅ DataProcessor import successful")
        tests.append(True)
    except Exception as e:
        print(f"❌ DataProcessor import failed: {e}")
        tests.append(False)
    
    # Test 3: ML Models
    try:
        from src.ml_models import ModelFactory
        print("✅ ML Models import successful")
        tests.append(True)
    except Exception as e:
        print(f"❌ ML Models import failed: {e}")
        tests.append(False)
    
    # Test 4: Trading Strategies
    try:
        from src.trading_strategies import TrendFollowingStrategy
        print("✅ Trading Strategies import successful")
        tests.append(True)
    except Exception as e:
        print(f"❌ Trading Strategies import failed: {e}")
        tests.append(False)
    
    # Test 5: Meta Learning
    try:
        from src.meta_learning import MetaLearningEngine
        print("✅ Meta Learning import successful")
        tests.append(True)
    except Exception as e:
        print(f"❌ Meta Learning import failed: {e}")
        tests.append(False)
    
    # Test 6: MT5 Interface
    try:
        from src.mt5_interface import MT5Interface
        print("✅ MT5 Interface import successful")
        tests.append(True)
    except Exception as e:
        print(f"❌ MT5 Interface import failed: {e}")
        tests.append(False)
    
    # Test 7: Main System
    try:
        from src.helios_system import HeliosTradingSystem
        print("✅ Helios System import successful")
        tests.append(True)
    except Exception as e:
        print(f"❌ Helios System import failed: {e}")
        tests.append(False)
    
    # Test 8: Server
    try:
        from src.helios_server import app
        print("✅ Helios Server import successful")
        tests.append(True)
    except Exception as e:
        print(f"❌ Helios Server import failed: {e}")
        tests.append(False)
    
    print()
    print("📊 Test Results:")
    passed = sum(tests)
    total = len(tests)
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 All imports working! System is ready to run.")
        print("\n🚀 Next steps:")
        print("1. Run: python src/helios_server.py")
        print("2. Open browser to: http://localhost:8765")
        print("3. Copy deployed/HeliosML_EA.mq5 to MT5 Experts folder")
        return True
    else:
        print("\n⚠️  Some imports failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    test_imports()