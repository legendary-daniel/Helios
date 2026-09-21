#!/usr/bin/env python3
"""
Test script for Helios Price Action System
Tests all price action modules: Structure, SMC, Standard PA, Interface
"""

import sys
from pathlib import Path
import pandas as pd
import random

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(Path(__file__).parent))


def create_sample_data(base_price: float = 1.1000, candles: int = 200) -> pd.DataFrame:
    """Create sample OHLC data for testing"""
    data = []
    
    for i in range(candles):
        # Create some trending movement
        if i < 50:
            base_price += 0.0005  # Uptrend
        elif i < 100:
            base_price -= 0.0005  # Downtrend
        elif i < 150:
            base_price += 0.0003  # Weak uptrend
        else:
            base_price += random.uniform(-0.0005, 0.0005)  # Consolidation
        
        # Add some noise
        noise = random.uniform(-0.0002, 0.0002)
        
        high = base_price + abs(noise) + 0.001
        low = base_price - abs(noise) - 0.001
        close = base_price + noise
        open_price = base_price - noise/2
        
        # Create some patterns
        if i == 30:
            # Hammer (bullish pin bar)
            high = base_price + 0.0003
            low = base_price - 0.0015
            close = base_price + 0.0005
        elif i == 80:
            # Shooting star (bearish pin bar)
            high = base_price + 0.0015
            low = base_price - 0.0003
            close = base_price - 0.0005
        elif i == 120:
            # Bullish engulfing
            open_price = base_price - 0.0008
            close = base_price + 0.0010
        
        data.append({
            "time": 1700000000 + i * 900,
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "tick_volume": random.randint(100, 1000)
        })
    
    return pd.DataFrame(data)


def test_market_structure():
    """Test Market Structure module"""
    print("\n" + "="*60)
    print("TESTING: Market Structure")
    print("="*60)
    
    try:
        from src.price_action.structure import MarketStructureMapper
        
        df = create_sample_data()
        
        mapper = MarketStructureMapper(swing_window=5)
        result = mapper.analyze(df)
        
        print(f"\n✅ Results:")
        print(f"  Trend Bias: {result['trend_bias']}")
        print(f"  Structure Type: {result['structure_type']}")
        print(f"  Swing Points: {len(result['swing_points'])}")
        print(f"  BOS Events: {len(result['bos'])}")
        
        if result['swing_points']:
            print(f"\n📈 Recent Swing Points:")
            for sp in result['swing_points'][-3:]:
                print(f"  {sp['type'].upper()}: {sp['price']:.5f}")
        
        print("\n✅ Market Structure: PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Market Structure: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def test_smc():
    """Test SMC module"""
    print("\n" + "="*60)
    print("TESTING: SMC (Smart Money Concepts)")
    print("="*60)
    
    try:
        from src.price_action.smc_core import SMCAnalyzer
        
        df = create_sample_data()
        
        analyzer = SMCAnalyzer(fvg_threshold_pips=0.0005)
        result = analyzer.analyze(df)
        
        print(f"\n✅ Results:")
        print(f"  FVGs Found: {len(result['fvgs'])}")
        print(f"  Active FVGs: {result['active_fvgs']}")
        print(f"  Order Blocks: {len(result['order_blocks'])}")
        print(f"  Liquidity Pools: {len(result['liquidity_pools'])}")
        
        if result['fvgs']:
            print(f"\n📈 Recent FVGs:")
            for fvg in result['fvgs'][:3]:
                print(f"  {fvg['type'].upper()}: {fvg['bottom']:.5f} - {fvg['top']:.5f}")
        
        # Test trade setup
        setup = analyzer.get_trade_setup(df, "bullish")
        print(f"\n📊 Trade Setup (Bullish):")
        print(f"  Entry Zones: {len(setup['entry_zones'])}")
        
        print("\n✅ SMC Module: PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ SMC Module: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def test_standard_pa():
    """Test Standard Price Action module"""
    print("\n" + "="*60)
    print("TESTING: Standard Price Action")
    print("="*60)
    
    try:
        from src.price_action.standard_pa import PriceActionAnalyzer
        
        df = create_sample_data()
        
        analyzer = PriceActionAnalyzer()
        result = analyzer.analyze(df)
        
        print(f"\n✅ Results:")
        print(f"  Patterns Found: {len(result['patterns'])}")
        print(f"  Bullish: {result['pattern_count']['bullish']}")
        print(f"  Bearish: {result['pattern_count']['bearish']}")
        print(f"  Support Levels: {len(result['support_levels'])}")
        print(f"  Resistance Levels: {len(result['resistance_levels'])}")
        print(f"  Trend: {result['trend']}")
        
        # Test trade signal
        signal = analyzer.get_trade_signal(df, "bullish")
        print(f"\n📊 Trade Signal (Bullish):")
        print(f"  Decision: {signal['decision']}")
        print(f"  Confidence: {signal['confidence']:.2f}")
        
        print("\n✅ Standard PA: PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Standard PA: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def test_interface():
    """Test unified interface"""
    print("\n" + "="*60)
    print("TESTING: Price Action Interface")
    print("="*60)
    
    try:
        from src.price_action.interface import HeliosPriceAction
        
        df = create_sample_data()
        
        # Initialize engine
        pa = HeliosPriceAction()
        
        # Run complete analysis
        print("\n📊 Running complete analysis...")
        result = pa.analyze(df)
        
        print(f"\n✅ Analysis Results:")
        print(f"  Status: {result['status']}")
        print(f"  Current Price: {result['current_price']:.5f}")
        print(f"  Trend: {result['structure']['trend_bias']}")
        
        # Show signal
        signal = result['signal']
        print(f"\n📈 Trading Signal:")
        print(f"  Decision: {signal['decision']}")
        print(f"  Direction: {signal['direction']}")
        print(f"  Confidence: {signal['confidence']:.2f}")
        
        if signal['levels']['entry']:
            print(f"\n📊 Trade Levels:")
            print(f"  Entry: {signal['levels']['entry']}")
            print(f"  Stop Loss: {signal['levels']['stop_loss']}")
            print(f"  Take Profit: {signal['levels']['take_profit']}")
        
        # Test ML confirmation
        print("\n" + "-"*40)
        print("Testing ML Direction Confirmation...")
        
        ml_result = pa.get_signal_for_ml_direction(df, "bullish")
        
        print(f"\n📊 ML Confirmation:")
        print(f"  ML Direction: {ml_result['ml_direction']}")
        print(f"  Structure Aligned: {ml_result['structure_aligned']}")
        print(f"  Pattern Aligned: {ml_result['pattern_aligned']}")
        print(f"  Combined Confidence: {ml_result['combined_confidence']:.2f}")
        
        rec = ml_result['recommendation']
        print(f"\n📋 Recommendation:")
        print(f"  Entry: {rec['entry']}")
        print(f"  Stop Loss: {rec['stop_loss']}")
        
        print("\n✅ Interface: PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Interface: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def test_performance():
    """Test performance with larger dataset"""
    print("\n" + "="*60)
    print("PERFORMANCE TEST")
    print("="*60)
    
    try:
        from src.price_action.interface import HeliosPriceAction
        import time
        
        # Create larger dataset
        print("\n📊 Creating 1000 candles...")
        df = create_sample_data(candles=1000)
        
        # Initialize
        pa = HeliosPriceAction()
        
        # Time the analysis
        print("⏱️  Running analysis on 1000 candles...")
        start_time = time.time()
        
        result = pa.analyze(df)
        
        elapsed = time.time() - start_time
        
        print(f"\n⏱️  Performance:")
        print(f"  Time: {elapsed*1000:.1f}ms")
        print(f"  Status: {result['status']}")
        
        if elapsed < 1.0:
            print("\n✅ Performance: PASSED (< 1 second)")
            return True
        else:
            print(f"\n⚠️  Performance: SLOW ({elapsed:.1f}s)")
            return False
        
    except Exception as e:
        print(f"\n❌ Performance Test: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("="*60)
    print("HELIOS PRICE ACTION SYSTEM - TEST SUITE")
    print("="*60)
    print(f"Testing with sample data...")
    
    results = []
    
    # Run tests
    results.append(("Market Structure", test_market_structure()))
    results.append(("SMC Module", test_smc()))
    results.append(("Standard PA", test_standard_pa()))
    results.append(("Interface", test_interface()))
    results.append(("Performance", test_performance()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST RESULTS SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {name:20s}: {status}")
    
    print(f"\n📊 Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Price Action System ready.")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
