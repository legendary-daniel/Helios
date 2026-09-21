# 🔧 Step-by-Step Guide: Fix "No module named 'config'" Error in VS Code

## 🎯 **Problem**
The Python server can't find the `config` module due to incorrect import paths.

## 📋 **Step-by-Step Solution**

### **Step 1: Open Terminal in VS Code**
1. Open VS Code
2. Open the `helios-ml-trading-system` folder
3. Press `Ctrl+`` (backtick) or go to `Terminal → New Terminal`
4. Verify you're in the correct directory:
   ```bash
   pwd
   # Should show: .../helios-ml-trading-system
   ```

### **Step 2: Check Virtual Environment**
1. In VS Code terminal, ensure virtual environment is activated:
   ```bash
   which python
   # Should show path to your venv
   ```
2. If not activated, activate it:
   ```bash
   source venv/bin/activate  # macOS/Linux
   # OR
   venv\Scripts\activate     # Windows
   ```

### **Step 3: Install Required Dependencies**
```bash
# Install all required packages
pip install -r requirements.txt

# If you get errors, install individually:
pip install numpy pandas scikit-learn tensorflow lightgbm xgboost
pip install MetaTrader5 fastapi uvicorn websockets python-multipart
pip install ta plotly chart.js openpyxl
```

### **Step 4: Fix Import Path Issues**

#### **Option A: Create a proper Python package structure**

**Step 4.1: Add `__init__.py` files**
Create these empty files in VS Code:

1. **Create**: `src/__init__.py`
   ```python
   # Empty file
   ```

2. **Create**: `config/__init__.py`
   ```python
   """Configuration package"""
   ```

#### **Option B: Use PYTHONPATH (Recommended)**

**Step 4.1: Set PYTHONPATH Environment Variable**

**For macOS/Linux users:**
1. In VS Code terminal, run:
   ```bash
   export PYTHONPATH="${PYTHONPATH}:$(pwd)"
   python src/helios_server.py
   ```

2. **Permanent fix**: Add to your shell profile:
   ```bash
   echo 'export PYTHONPATH="${PYTHONPATH}:/path/to/helios-ml-trading-system"' >> ~/.zshrc
   source ~/.zshrc
   ```

**For Windows users:**
1. In VS Code terminal, run:
   ```cmd
   set PYTHONPATH=%PYTHONPATH%;C:\path\to\helios-ml-trading-system
   python src/helios_server.py
   ```

#### **Option C: Modify imports in source files**

**Step 4.1: Fix helios_server.py**
In VS Code, open `src/helios_server.py` and change line 24-28:

**Current (broken):**
```python
# Add src directory to path
sys.path.append(str(Path(__file__).parent / "src"))

# Import Helios components
try:
    from config import config
    from helios_system import HeliosTradingSystem
```

**Fixed:**
```python
# Add project root to Python path
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import Helios components
try:
    from config.config import config
    from helios_system import HeliosTradingSystem
```

**Step 4.2: Fix helios_system.py**
Open `src/helios_system.py` and add these lines at the top:

```python
# Add project root to path
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import all system components
from config.config import config
from data_processor import DataProcessor
from ml_models import ModelFactory, EnsembleModel
```

**Step 4.3: Fix all other source files**
For each file in `src/` folder, add this at the top:

```python
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
```

### **Step 5: Run the Server**

#### **Method 1: From VS Code Terminal**
```bash
# Make sure you're in the right directory
cd /path/to/helios-ml-trading-system

# Run the server
python src/helios_server.py
```

#### **Method 2: Using python -m**
```bash
python -m uvicorn src.helios_server:app --host 0.0.0.0 --port 8765 --reload
```

#### **Method 3: Create a startup script**
Create `run_server.sh` (macOS/Linux):
```bash
#!/bin/bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
python src/helios_server.py
```

Make executable:
```bash
chmod +x run_server.sh
./run_server.sh
```

### **Step 6: Test in VS Code**

1. **Create a test file**: `test_imports.py`
   ```python
   import sys
   from pathlib import Path
   
   # Add project root
   project_root = Path(__file__).parent
   sys.path.insert(0, str(project_root))
   
   # Test imports
   try:
       from config.config import config
       print("✅ Config import successful")
       
       from helios_system import HeliosTradingSystem
       print("✅ Helios system import successful")
       
       print("🎉 All imports working!")
       
   except ImportError as e:
       print(f"❌ Import error: {e}")
   ```

2. **Run the test**: `python test_imports.py`

### **Step 7: VS Code Configuration**

#### **Option A: Add to settings.json**
1. Press `Cmd+Shift+P` (Mac) or `Ctrl+Shift+P` (Windows)
2. Type "Preferences: Open Settings (JSON)"
3. Add:
   ```json
   {
     "python.defaultInterpreterPath": "./venv/bin/python",
     "python.terminal.activateEnvironment": true
   }
   ```

#### **Option B: Create launch.json**
1. Go to `Run and Debug` tab in VS Code
2. Click "create a launch.json file"
3. Add:
   ```json
   {
     "version": "0.2.0",
     "configurations": [
       {
         "name": "Run Helios Server",
         "type": "python",
         "request": "launch",
         "program": "${workspaceFolder}/src/helios_server.py",
         "console": "integratedTerminal",
         "cwd": "${workspaceFolder}",
         "env": {
           "PYTHONPATH": "${workspaceFolder}"
         }
       }
     ]
   }
   ```

### **Step 8: Quick Commands Reference**

```bash
# Check Python path
python -c "import sys; print(sys.path)"

# Check project structure
find . -name "*.py" | head -10

# Run with debug
python -m pdb src/helios_server.py

# Install missing packages
pip install package_name --upgrade
```

### **Step 9: Verify Success**

If everything is working, you should see:
```
INFO: Started server process [12345]
INFO: Waiting for application startup.
INFO: Application startup complete.
INFO: Uvicorn running on http://0.0.0.0:8765 (Press CTRL+C to quit)
```

Then open your browser to `http://localhost:8765`

### **🚨 Common Issues & Solutions**

**Issue**: "ModuleNotFoundError: No module named 'config'"
**Solution**: Check that `PYTHONPATH` includes your project root directory

**Issue**: "ImportError: attempted relative import"
**Solution**: Use absolute imports by adding project root to sys.path

**Issue**: Virtual environment not activating in VS Code
**Solution**: Set Python interpreter in VS Code (Ctrl+Shift+P → "Python: Select Interpreter")

**Issue**: Dependencies not installed
**Solution**: 
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### **📞 If Still Having Issues**

1. **Restart VS Code** completely
2. **Check file permissions** on scripts
3. **Verify directory structure** matches expected paths
4. **Use absolute paths** for testing
5. **Check VS Code Python extension** is installed

This should resolve the import error! The key is ensuring Python can find all modules by setting the correct PYTHONPATH.