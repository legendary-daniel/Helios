"""
Helios AI Trading System - Complete AI-Powered Trading

This package provides AI-enhanced trading capabilities including:
- Market Structure Analysis
- Smart Money Concepts (FVG, Order Blocks)
- Pattern Recognition
- Regime Detection
- Risk Management
- Dynamic S/R Levels

All using FREE open-source tools:
- scikit-learn
- pandas
- numpy

Usage:
    from helios_ai import HeliosAITrading
    
    ai = HeliosAITrading()
    analysis = ai.analyze_market(ohlc_data)
    signal = ai.generate_signal(ohlc_data, ml_direction='bullish')
"""

from .core import AIBaseModel, FeatureEngineer, ModelStore, create_ai_pipeline
from .main import HeliosAITrading, create_helios_ai

# Import all modules
from .modules import (
    StructureAI,
    FVGAI,
    OBValidationAI,
    PatternRecognitionAI,
    RegimeDetectionAI,
    RiskManagementAI,
    DynamicLevelsAI
)

__all__ = [
    # Core
    'AIBaseModel',
    'FeatureEngineer',
    'ModelStore',
    'create_ai_pipeline',
    
    # Main
    'HeliosAITrading',
    'create_helios_ai',
    
    # Modules
    'StructureAI',
    'FVGAI',
    'OBValidationAI',
    'PatternRecognitionAI',
    'RegimeDetectionAI',
    'RiskManagementAI',
    'DynamicLevelsAI'
]

__version__ = '1.0.0'
__author__ = 'Helios AI Team'

# Quick start
def quick_start():
    """Quick start guide"""
    print("""
🚀 HELIOS AI TRADING SYSTEM - QUICK START
==========================================

1. Import the system:
   from helios_ai import HeliosAITrading

2. Create AI instance:
   ai = HeliosAITrading()

3. Analyze market:
   analysis = ai.analyze_market(ohlc_dataframe)

4. Generate signal:
   signal = ai.generate_signal(ohlc_dataframe, ml_direction='bullish')

5. Execute trade:
   print(f"Entry: {signal['entry']}, SL: {signal['stop_loss']}")

Requirements:
   pip install pandas numpy scikit-learn

For more: See HELIOS_AI_GUIDE.md
    """)
