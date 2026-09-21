# Python Import Issues - Fix Guide

## 🚨 Current Issues Identified:

1. **LightGBM missing `libomp.dylib`** (macOS-specific)
2. **MetaTrader5 module not installed**
3. **MetaLearner → MetaLearningEngine** (wrong class name)
4. **Data processor import path issues**

## ✅ Step-by-Step Fixes:

### **Step 1: Install Missing System Libraries (macOS)**
```bash
# Install libomp for LightGBM (macOS only)
brew install libomp

# Verify installation
ls -la /opt/homebrew/opt/libomp/lib/
```

### **Step 2: Install Python Packages**
```bash
# Install MetaTrader5 (required for MT5 connection)
uv pip install MetaTrader5

# Reinstall LightGBM with proper dependencies
uv pip uninstall lightgbm
uv pip install lightgbm

# Install other missing dependencies
uv pip install -r requirements.txt
```

### **Step 3: Fix Import Path Issues**

The main issue is in `src/helios_system.py` line 26. Fix this:

**❌ WRONG:**
```python
from data_processor import DataProcessor
from ml_models import ModelFactory, EnsembleModel  
from meta_learning import MetaLearningEngine
```

**✅ CORRECT:**
```python
from src.data_processor import DataProcessor
from src.ml_models import ModelFactory, EnsembleModel
from src.meta_learning import MetaLearningEngine
```

### **Step 4: Fix MetaLearner Import**

In your test_imports.py file, change:
```python
# WRONG
from src.meta_learning import MetaLearner

# CORRECT  
from src.meta_learning import MetaLearningEngine
```

### **Step 5: Test Imports Again**
```bash
python test_imports.py
```

## 🐛 Common macOS Solutions:

### **LightGBM/libomp Issue:**
```bash
# If libomp still not found, try:
export OPENMP_ROOT_DIR=/opt/homebrew

# Or install from conda-forge:
conda install -c conda-forge lightgbm libomp
```

### **MetaTrader5 Installation:**
```bash
# Try alternative installation methods:
pip install MetaTrader5
# or
conda install -c conda-forge metatrader5
```

## 📝 Verification Checklist:
- [ ] libomp.dylib installed and accessible
- [ ] MetaTrader5 installed successfully
- [ ] All imports resolved in test_imports.py
- [ ] Python server can start without errors

## 🔧 If Still Having Issues:

1. **Restart your virtual environment:**
   ```bash
   deactivate
   source venv/bin/activate
   ```

2. **Clear cache and reinstall:**
   ```bash
   uv pip cache purge
   uv sync
   ```

3. **Check Python path:**
   ```python
   import sys
   print(sys.path)
   ```

## 🎯 Expected Result:
After fixes, `python test_imports.py` should show:
```
✅ Config import successful
✅ DataProcessor import successful  
✅ ML Models import successful
✅ Trading Strategies import successful
✅ Meta Learning import successful
✅ MT5 Interface import successful
✅ Helios System import successful
✅ Helios Server import successful

📊 Test Results:
✅ Passed: 8/8
❌ Failed: 0/8
```

Then you can run: `python src/helios_server.py` successfully!
