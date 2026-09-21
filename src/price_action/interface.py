"""
Helios ML Trading System - Price Action Interface
Unified interface combining all price action modules
Integrates with MT5 EA and main trading system
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import json
from datetime import datetime

# Import price action modules
from .structure import MarketStructureMapper, TrendDirection
from .smc_core import SMCAnalyzer, FairValueGap, OrderBlock
from .standard_pa import PriceActionAnalyzer, CandleSignal


class HeliosPriceAction:
    """
    Unified Price Action Analysis Engine
    
    Combines:
    - Market Structure (swing points, BOS, trend)
    - SMC/ICT (FVGs, Order Blocks, Liquidity)
    - Standard PA (candlestick patterns, S/R)
    """
    
    def __init__(self, config: dict = None):
        """
        Initialize the price action engine
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        
        # Initialize components
        self.structure = MarketStructureMapper(
            swing_window=self.config.get('swing_window', 5)
        )
        
        self.smc = SMCAnalyzer(
            fvg_threshold_pips=self.config.get('fvg_threshold', 0.0010),
            ob_lookback=self.config.get('ob_lookback', 20)
        )
        
        self.standard_pa = PriceActionAnalyzer(
            lookback=self.config.get('lookback', 100),
            sr_tolerance=self.config.get('sr_tolerance', 0.0010)
        )
        
        # Analysis results cache
        self.last_analysis = None
        self.last_update = None
        
    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        Perform complete price action analysis
        
        Args:
            df: DataFrame with OHLC data (must have: time, open, high, low, close, tick_volume)
            
        Returns:
            Dictionary with complete analysis
        """
        # Ensure minimum data
        if len(df) < 50:
            return {
                "status": "error",
                "message": "Insufficient data. Need at least 50 candles.",
                "error": "data_insufficient"
            }
        
        # Run all analyses
        structure_result = self.structure.analyze(df)
        smc_result = self.smc.analyze(df)
        pa_result = self.standard_pa.analyze(df)
        
        # Get current price
        current_price = float(df['close'].iloc[-1])
        
        # Combine results
        analysis = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "current_price": current_price,
            
            # Market Structure
            "structure": {
                "trend_bias": structure_result['trend_bias'],
                "structure_type": structure_result['structure_type'],
                "swing_points": structure_result['swing_points'][-5:],
                "recent_bos": structure_result['bos'][-3:] if structure_result['bos'] else []
            },
            
            # SMC/ICT
            "smc": {
                "active_fvgs": smc_result['active_fvgs'],
                "fvgs": smc_result['fvgs'][-5:],
                "order_blocks": smc_result['order_blocks'][-5:],
                "liquidity_pools": smc_result['liquidity_pools'][-5:]
            },
            
            # Standard Price Action
            "price_action": {
                "patterns": pa_result['patterns'][-5:],
                "pattern_count": pa_result['pattern_count'],
                "support_levels": pa_result['support_levels'][:5],
                "resistance_levels": pa_result['resistance_levels'][:5],
                "trend": pa_result['trend']
            },
            
            # Unified Signal
            "signal": self._generate_unified_signal(df, structure_result, smc_result, pa_result)
        }
        
        self.last_analysis = analysis
        self.last_update = datetime.now()
        
        return analysis
    
    def _generate_unified_signal(self, df: pd.DataFrame, 
                                structure: Dict, 
                                smc: Dict, 
                                pa: Dict) -> Dict:
        """
        Generate unified trading signal from all analyses
        """
        current_price = float(df['close'].iloc[-1])
        
        # Count signals from each source
        bullish_score = 0
        bearish_score = 0
        reasons = []
        
        # 1. Market Structure
        trend = structure['trend_bias']
        if trend == "bullish":
            bullish_score += 2
            reasons.append(f"Structure: Uptrend ({trend})")
        elif trend == "bearish":
            bearish_score += 2
            reasons.append(f"Structure: Downtrend ({trend})")
        
        # Check for CHoCH (reversal signal)
        recent_bos = structure.get('bos', [])
        if recent_bos:
            last_bos = recent_bos[-1]
            if structure['trend_bias'] == "bullish" and last_bos['type'] == "bearish":
                bearish_score += 3
                reasons.append("Structure: Bearish BOS in uptrend (potential reversal)")
            elif structure['trend_bias'] == "bearish" and last_bos['type'] == "bullish":
                bullish_score += 3
                reasons.append("Structure: Bullish BOS in downtrend (potential reversal)")
        
        # 2. SMC Analysis
        active_fvgs = smc.get('active_fvgs', 0)
        if active_fvgs > 0:
            # Check for FVGs in direction of potential trade
            fvgs = smc.get('fvgs', [])
            for fvg in fvgs[:3]:
                if fvg['type'] == 'bullish' and fvg['bottom'] < current_price:
                    bullish_score += 1
                    reasons.append(f"SMC: Bullish FVG below price")
                elif fvg['type'] == 'bearish' and fvg['top'] > current_price:
                    bearish_score += 1
                    reasons.append(f"SMC: Bearish FVG above price")
        
        # 3. Standard Price Action
        pattern_count = pa.get('pattern_count', {})
        bullish_patterns = pattern_count.get('bullish', 0)
        bearish_patterns = pattern_count.get('bearish', 0)
        
        if bullish_patterns > bearish_patterns:
            diff = bullish_patterns - bearish_patterns
            bullish_score += min(diff, 3)
            reasons.append(f"PA: {diff} more bullish patterns")
        elif bearish_patterns > bullish_patterns:
            diff = bearish_patterns - bullish_patterns
            bearish_score += min(diff, 3)
            reasons.append(f"PA: {diff} more bearish patterns")
        
        # S/R alignment
        support_levels = pa.get('support_levels', [])
        resistance_levels = pa.get('resistance_levels', [])
        
        if support_levels:
            nearest_support = support_levels[0]['price']
            distance_pct = (current_price - nearest_support) / current_price
            if distance_pct < 0.015:  # Within 1.5%
                bullish_score += 1
                reasons.append(f"PA: Near support ({nearest_support:.5f})")
        
        if resistance_levels:
            nearest_resistance = resistance_levels[0]['price']
            distance_pct = (nearest_resistance - current_price) / current_price
            if distance_pct < 0.015:
                bearish_score += 1
                reasons.append(f"PA: Near resistance ({nearest_resistance:.5f})")
        
        # Determine final signal
        total_score = bullish_score + bearish_score
        
        if total_score == 0:
            confidence = 0.0
            direction = "neutral"
            decision = "WAIT"
        else:
            if bullish_score > bearish_score:
                confidence = (bullish_score - bearish_score) / total_score
                direction = "bullish"
            elif bearish_score > bullish_score:
                confidence = (bearish_score - bullish_score) / total_score
                direction = "bearish"
            else:
                confidence = 0.0
                direction = "neutral"
            
            if confidence >= 0.6:
                decision = "ENTRY"
            elif confidence >= 0.4:
                decision = "CAUTION"
            else:
                decision = "WAIT"
        
        # Calculate entry, stop loss, take profit
        entry = current_price
        stop_loss = None
        take_profit = None
        risk_reward = 0
        
        if direction == "bullish" and support_levels:
            stop_loss = support_levels[0]['price'] * 0.999  # Slightly below
            risk = current_price - stop_loss
            if resistance_levels:
                take_profit = resistance_levels[0]['price'] * 1.001
                reward = take_profit - current_price
                if risk > 0:
                    risk_reward = reward / risk
        
        elif direction == "bearish" and resistance_levels:
            stop_loss = resistance_levels[0]['price'] * 1.001
            risk = stop_loss - current_price
            if support_levels:
                take_profit = support_levels[0]['price'] * 0.999
                reward = current_price - take_profit
                if risk > 0:
                    risk_reward = reward / risk
        
        return {
            "decision": decision,
            "direction": direction,
            "confidence": round(confidence, 2),
            "bullish_score": bullish_score,
            "bearish_score": bearish_score,
            "reasons": reasons,
            "levels": {
                "entry": round(entry, 5),
                "stop_loss": round(stop_loss, 5) if stop_loss else None,
                "take_profit": round(take_profit, 5) if take_profit else None,
                "risk_reward": round(risk_reward, 2) if risk_reward > 0 else None
            }
        }
    
    def get_signal_for_ml_direction(self, df: pd.DataFrame, ml_direction: str) -> Dict:
        """
        Get price action confirmation for ML signal
        
        Args:
            df: Price data
            ml_direction: Direction from ML model ('bullish' or 'bearish')
            
        Returns:
            Signal with entry/stop levels
        """
        # Run analysis
        analysis = self.analyze(df)
        
        if analysis['status'] != 'success':
            return {
                "status": "error",
                "message": analysis.get('message', 'Analysis failed')
            }
        
        # Get PA confirmation
        pa_signal = self.standard_pa.get_trade_signal(df, ml_direction)
        
        # Get SMC setup
        smc_setup = self.smc.get_trade_setup(df, ml_direction)
        
        # Combine
        combined = {
            "status": "success",
            "ml_direction": ml_direction,
            "current_price": analysis['current_price'],
            
            # Structure alignment
            "structure_aligned": (
                analysis['structure']['trend_bias'] == ml_direction or
                analysis['signal']['direction'] == ml_direction
            ),
            
            # Pattern alignment
            "pattern_aligned": pa_signal['decision'] in ['ENTRY', 'CAUTION'],
            "pa_confidence": pa_signal['confidence'],
            
            # SMC setup
            "smc_zones": smc_setup.get('entry_zones', []),
            "smc_confidence": smc_setup.get('confidence', 0),
            
            # Combined confidence
            "combined_confidence": (
                analysis['signal']['confidence'] * 0.4 +
                pa_signal['confidence'] * 0.3 +
                smc_setup.get('confidence', 0) * 0.3
            ),
            
            # Recommended levels
            "recommendation": self._combine_levels(ml_direction, pa_signal, smc_setup),
            
            # Full analysis
            "full_signal": analysis['signal'],
            "pattern_analysis": pa_signal,
            "reasons": analysis['signal']['reasons'] + pa_signal.get('reasons', [])
        }
        
        return combined
    
    def _combine_levels(self, direction: str, pa_signal: Dict, smc_setup: Dict) -> Dict:
        """Combine entry/stop levels from PA and SMC"""
        
        if direction == "bullish":
            # Entry: Use nearest of PA support or SMC FVG/OB
            entries = []
            
            if pa_signal.get('nearest_support'):
                entries.append(pa_signal['nearest_support'])
            
            for zone in smc_setup.get('entry_zones', []):
                entries.append(zone.get('entry'))
            
            if entries:
                entry = min(entries)
            else:
                entry = None
            
            # Stop loss: Use lowest support or SMC stop
            stops = []
            if pa_signal.get('stop_loss'):
                stops.append(pa_signal['stop_loss'])
            for zone in smc_setup.get('entry_zones', []):
                if zone.get('stop'):
                    stops.append(zone['stop'])
            
            stop_loss = min(stops) if stops else None
            
        else:  # bearish
            entries = []
            
            if pa_signal.get('nearest_resistance'):
                entries.append(pa_signal['nearest_resistance'])
            
            for zone in smc_setup.get('entry_zones', []):
                entries.append(zone.get('entry'))
            
            if entries:
                entry = max(entries)
            else:
                entry = None
            
            stops = []
            if pa_signal.get('stop_loss'):
                stops.append(pa_signal['stop_loss'])
            for zone in smc_setup.get('entry_zones', []):
                if zone.get('stop'):
                    stops.append(zone['stop'])
            
            stop_loss = max(stops) if stops else None
        
        return {
            "entry": round(entry, 5) if entry else None,
            "stop_loss": round(stop_loss, 5) if stop_loss else None
        }
    
    def get_json_output(self, df: pd.DataFrame, ml_direction: str = None) -> str:
        """
        Get analysis as JSON string (for MT5 integration)
        
        Args:
            df: Price data
            ml_direction: Optional ML direction
            
        Returns:
            JSON string
        """
        if ml_direction:
            result = self.get_signal_for_ml_direction(df, ml_direction)
        else:
            result = self.analyze(df)
        
        return json.dumps(result, indent=2)


def create_pa_engine(config: dict = None) -> HeliosPriceAction:
    """
    Factory function to create price action engine
    
    Args:
        config: Configuration dictionary
        
    Returns:
        HeliosPriceAction instance
    """
    return HeliosPriceAction(config)


# Example usage
if __name__ == "__main__":
    import random
    
    print("="*60)
    print("HELIOS PRICE ACTION ENGINE TEST")
    print("="*60)
    
    # Create sample data
    data = []
    base_price = 1.1000
    
    for i in range(200):
        base_price += random.uniform(-0.001, 0.001)
        
        high = base_price + random.uniform(0.0005, 0.002)
        low = base_price - random.uniform(0.0005, 0.002)
        close = base_price + random.uniform(-0.0005, 0.0005)
        open_price = base_price + random.uniform(-0.0003, 0.0003)
        
        data.append({
            "time": 1700000000 + i * 900,
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "tick_volume": random.randint(100, 1000)
        })
    
    df = pd.DataFrame(data)
    
    # Initialize engine
    print("\n🚀 Initializing Price Action Engine...")
    pa_engine = HeliosPriceAction()
    
    # Run analysis
    print("📊 Running analysis...")
    result = pa_engine.analyze(df)
    
    print(f"\n🎯 Analysis Results:")
    print(f"  Status: {result['status']}")
    print(f"  Current Price: {result['current_price']:.5f}")
    print(f"  Trend: {result['structure']['trend_bias']}")
    print(f"  Active FVGs: {result['smc']['active_fvgs']}")
    
    print(f"\n📈 Trading Signal:")
    signal = result['signal']
    print(f"  Decision: {signal['decision']}")
    print(f"  Direction: {signal['direction']}")
    print(f"  Confidence: {signal['confidence']:.2f}")
    print(f"  Bullish Score: {signal['bullish_score']}")
    print(f"  Bearish Score: {signal['bearish_score']}")
    
    if signal['levels']['entry']:
        print(f"\n📊 Trade Levels:")
        print(f"  Entry: {signal['levels']['entry']}")
        print(f"  Stop Loss: {signal['levels']['stop_loss']}")
        print(f"  Take Profit: {signal['levels']['take_profit']}")
        print(f"  Risk/Reward: {signal['levels']['risk_reward']}")
    
    print(f"\n📝 Reasons:")
    for reason in signal['reasons'][:5]:
        print(f"  - {reason}")
    
    # Test with ML direction
    print("\n" + "="*60)
    print("TEST WITH ML DIRECTION")
    print("="*60)
    
    ml_result = pa_engine.get_signal_for_ml_direction(df, "bullish")
    
    print(f"\n🎯 ML Confirmation Results:")
    print(f"  ML Direction: {ml_result['ml_direction']}")
    print(f"  Structure Aligned: {ml_result['structure_aligned']}")
    print(f"  Pattern Aligned: {ml_result['pattern_aligned']}")
    print(f"  Combined Confidence: {ml_result['combined_confidence']:.2f}")
    
    print(f"\n📊 Recommendation:")
    rec = ml_result['recommendation']
    print(f"  Entry: {rec['entry']}")
    print(f"  Stop Loss: {rec['stop_loss']}")
    
    print("\n✅ Price Action Engine test complete!")
