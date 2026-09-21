# MT5 EA Compilation Fix Guide

## Issue Analysis
The Expert Advisor has several compilation errors that need to be fixed:

### 1. Missing Include Files
- `WebRequest.mqh` - Not found in standard MT5 library
- `Json.mqh` - Not found in standard MT5 library

### 2. Parameter Mismatches
- `HistoryDealGetDouble()` function calls have incorrect parameter count
- Some variable declarations issues

## Solutions

### Solution 1: Fix Missing Include Files

MT5 doesn't have built-in WebRequest and JSON libraries by default. You need to either:

1. **Download and install the missing libraries** (recommended):
   - Download `WebRequest.mqh` from MQL5 community
   - Download `Json.mqh` from MQL5 community
   - Place them in your MT5 `MQL5/Include/` folder

2. **Alternative: Remove dependencies and simplify code** (quick fix)

### Solution 2: Parameter Fixes

The `HistoryDealGetDouble()` function calls need correct parameters.

## Step-by-Step Fix Process

### Option A: Quick Fix (Remove Complex Dependencies)

1. **Replace the Expert Advisor file** with a simplified version that removes WebRequest and JSON dependencies
2. This version will work but won't have WebSocket connectivity initially
3. You can add WebSocket functionality later with proper libraries

### Option B: Full Fix (Install Missing Libraries)

1. Download `WebRequest.mqh` and `Json.mqh` from MQL5 community
2. Place them in `C:\Program Files\MetaTrader 5\MQL5\Include\`
3. Keep the current EA code
4. Compile again

### Recommended Action

<!-- I'll create a simplified version of the EA that removes the problematic dependencies and fixes the parameter issues. -->
