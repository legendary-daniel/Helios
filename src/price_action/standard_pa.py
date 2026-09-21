"""
Helios ML Trading System - Standard Price Action
Classic technical analysis: Candlestick patterns, S/R, trend lines, indicators
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class CandlePattern(Enum):
    """Candlestick pattern types"""
    # Bullish patterns
    HAMMER = "hammer"
    INVERTED_HAMMER = "inverted_hammer"
    BULLISH_ENGULFING = "bullish_engulfing"
    MORNING_STAR = "morning_star"
    THREE_WHITE_SOLDIERS = "three_white_soldiers"
    PIERCING_LINE = "piercing_line"
    BULLISH_PIN_BAR = "bullish_pin_bar"
    BULLISH_INSIDE_BAR = "bullish_inside_bar"
    
    # Bearish patterns
    SHOOTING_STAR = "shooting_star"
    BEARISH_ENGULFING = "bearish_engulfing"
    EVENING_STAR = "evening_star"
    THREE_BLACK_CROWS = "three_black_crows"
    DARK_CLOUD_COVER = "dark_cloud_cover"
    BEARISH_PIN_BAR = "bearish_pin_bar"
    BEARISH_INSIDE_BAR = "bearish_inside_bar"
    
    # Neutral
    DOJI = "doji"
    SPINNING_TOP = "spinning_top"

class PatternDirection(Enum):
    """Pattern direction"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"

@dataclass
class CandleSignal:
    """Single candlestick pattern signal"""
    pattern: str
    direction: str
    strength: float  # 0-1
    index: int
    price: float

@dataclass
class SupportResistance:
    """Support or Resistance zone"""
    price: float
    type: str  # 'support' or 'resistance'
    strength: int  # Number of touches
    is_dynamic: bool  # Whether it's based on trend line

class PriceActionAnalyzer:
    """
    Standard Price Action Analysis
    """
    
    def __init__(self, 
                 lookback: int = 100,
                 sr_tolerance: float = 0.0010,  # 10 pips for forex
                 pattern_threshold: float = 0.5):
        """
        Initialize Price Action Analyzer
        
        Args:
            lookback: Number of candles to analyze
            sr_tolerance: Tolerance for S/R detection (price units)
            pattern_threshold: Minimum strength for pattern detection
        """
        self.lookback = lookback
        self.sr_tolerance = sr_tolerance
        self.pattern_threshold = pattern_threshold
        
        self.patterns: List[CandleSignal] = []
        self.support_levels: List[SupportResistance] = []
        self.resistance_levels: List[SupportResistance] = []
        
    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        Perform complete price action analysis
        
        Args:
            df: DataFrame with OHLC data
            
        Returns:
            Dictionary with complete analysis
        """
        # Reset
        self.patterns = []
        self.support_levels = []
        self.resistance_levels = []
        
        # Find candlestick patterns
        self.patterns = self.identify_candlestick_patterns(df)
        
        # Find support and resistance
        self.support_levels, self.resistance_levels = self.find_support_resistance(df)
        
        # Find recent trend
        trend = self.identify_trend(df)
        
        return self.get_analysis_result(trend)
    
    def identify_candlestick_patterns(self, df: pd.DataFrame) -> List[CandleSignal]:
        """
        Identify common candlestick patterns
        """
        signals = []
        
        if len(df) < 3:
            return signals
        
        opens = df['open'].values
        highs = df['high'].values
        lows = df['low'].values
        closes = df['close'].values
        
        for i in range(2, min(self.lookback, len(df))):
            # Calculate candle properties
            body = abs(closes[i] - opens[i])
            upper_wick = highs[i] - max(closes[i], opens[i])
            lower_wick = min(closes[i], opens[i]) - lows[i]
            total_range = highs[i] - lows[i]
            
            if total_range == 0:
                continue
                
            body_ratio = body / total_range
            upper_wick_ratio = upper_wick / total_range
            lower_wick_ratio = lower_wick / total_range
            
            # Bullish Pin Bar (Hammer-like)
            # Small body at top, long lower wick
            if (lower_wick_ratio > 0.6 and 
                body_ratio < 0.3 and 
                upper_wick_ratio < 0.1):
                signals.append(CandleSignal(
                    pattern="HAMMER",
                    direction="bullish",
                    strength=lower_wick_ratio,
                    index=i,
                    price=lows[i]
                ))
            
            # Bearish Pin Bar (Shooting Star)
            # Small body at bottom, long upper wick
            elif (upper_wick_ratio > 0.6 and 
                  body_ratio < 0.3 and 
                  lower_wick_ratio < 0.1):
                signals.append(CandleSignal(
                    pattern="SHOOTING_STAR",
                    direction="bearish",
                    strength=upper_wick_ratio,
                    index=i,
                    price=highs[i]
                ))
            
            # Bullish Engulfing
            elif (i >= 1 and 
                  closes[i-1] < opens[i-1] and  # Previous bearish
                  closes[i] > opens[i] and      # Current bullish
                  closes[i] > opens[i-1] and    # Engulfs previous
                  opens[i] < closes[i-1]):
                signals.append(CandleSignal(
                    pattern="BULLISH_ENGULFING",
                    direction="bullish",
                    strength=0.8,
                    index=i,
                    price=opens[i]
                ))
            
            # Bearish Engulfing
            elif (i >= 1 and 
                  closes[i-1] > opens[i-1] and  # Previous bullish
                  closes[i] < opens[i] and      # Current bearish
                  closes[i] < opens[i-1] and    # Engulfs previous
                  opens[i] > closes[i-1]):
                signals.append(CandleSignal(
                    pattern="BEARISH_ENGULFING",
                    direction="bearish",
                    strength=0.8,
                    index=i,
                    price=opens[i]
                ))
            
            # Doji (equal wicks, small body)
            elif body_ratio < 0.1 and upper_wick_ratio > 0.3 and lower_wick_ratio > 0.3:
                signals.append(CandleSignal(
                    pattern="DOJI",
                    direction="neutral",
                    strength=0.5,
                    index=i,
                    price=closes[i]
                ))
            
            # Morning Star (3-candle reversal)
            elif (i >= 2 and
                  closes[i-2] < opens[i-2] and  # Bearish first
                  body_ratio < 0.2 and          # Small second
                  closes[i] > opens[i] and      # Bullish third
                  closes[i] > (opens[i-2] + closes[i-2])/2):  # Above midpoint
                signals.append(CandleSignal(
                    pattern="MORNING_STAR",
                    direction="bullish",
                    strength=0.7,
                    index=i,
                    price=closes[i]
                ))
            
            # Evening Star (3-candle reversal)
            elif (i >= 2 and
                  closes[i-2] > opens[i-2] and  # Bullish first
                  body_ratio < 0.2 and          # Small second
                  closes[i] < opens[i] and      # Bearish third
                  closes[i] < (opens[i-2] + closes[i-2])/2):  # Below midpoint
                signals.append(CandleSignal(
                    pattern="EVENING_STAR",
                    direction="bearish",
                    strength=0.7,
                    index=i,
                    price=closes[i]
                ))
        
        return signals
    
    def find_support_resistance(self, df: pd.DataFrame) -> Tuple[List[SupportResistance], List[SupportResistance]]:
        """
        Find support and resistance levels
        """
        support = []
        resistance = []
        
        if len(df) < 10:
            return support, resistance
        
        highs = df['high'].values
        lows = df['low'].values
        
        # Find swing highs (resistance)
        swing_highs = []
        for i in range(5, len(df) - 5):
            is_high = True
            for j in range(1, 6):
                if highs[i] <= highs[i-j] or highs[i] <= highs[i+j]:
                    is_high = False
                    break
            if is_high:
                swing_highs.append(highs[i])
        
        # Find swing lows (support)
        swing_lows = []
        for i in range(5, len(df) - 5):
            is_low = True
            for j in range(1, 6):
                if lows[i] >= lows[i-j] or lows[i] >= lows[i+j]:
                    is_low = False
                    break
            if is_low:
                swing_lows.append(lows[i])
        
        # Cluster similar levels
        resistance = self.cluster_levels(swing_highs, "resistance")
        support = self.cluster_levels(swing_lows, "support")
        
        self.support_levels = support
        self.resistance_levels = resistance
        
        return support, resistance
    
    def cluster_levels(self, levels: List[float], level_type: str) -> List[SupportResistance]:
        """
        Cluster similar price levels together
        """
        if not levels:
            return []
        
        clusters = []
        tolerance = self.sr_tolerance
        
        for level in levels:
            # Check if it belongs to existing cluster
            found_cluster = False
            for cluster in clusters:
                if abs(level - cluster.price) <= tolerance:
                    cluster.strength += 1
                    found_cluster = True
                    break
            
            # Create new cluster
            if not found_cluster:
                clusters.append(SupportResistance(
                    price=level,
                    type=level_type,
                    strength=1,
                    is_dynamic=False
                ))
        
        # Sort by strength
        clusters.sort(key=lambda x: x.strength, reverse=True)
        
        return clusters[:10]  # Return top 10
    
    def identify_trend(self, df: pd.DataFrame) -> Dict:
        """
        Identify current trend using multiple methods
        """
        if len(df) < 20:
            return {"direction": "neutral", "strength": 0}
        
        closes = df['close'].values
        
        # Method 1: Higher Highs / Higher Lows
        recent_highs = []
        recent_lows = []
        
        for i in range(10, len(closes) - 10):
            # Simple high/low detection
            window = 5
            if i > window and i < len(closes) - window:
                if closes[i] > max(closes[i-window:i]) and closes[i] > max(closes[i+1:i+window+1]):
                    recent_highs.append(closes[i])
                if closes[i] < min(closes[i-window:i]) and closes[i] < min(closes[i+1:i+window+1]):
                    recent_lows.append(closes[i])
        
        # Determine trend
        if len(recent_highs) >= 2 and len(recent_lows) >= 2:
            if recent_highs[-1] > recent_highs[-2] and recent_lows[-1] > recent_lows[-2]:
                direction = "bullish"
                strength = min(len(recent_highs) / 5.0, 1.0)
            elif recent_highs[-1] < recent_highs[-2] and recent_lows[-1] < recent_lows[-2]:
                direction = "bearish"
                strength = min(len(recent_highs) / 5.0, 1.0)
            else:
                direction = "neutral"
                strength = 0.3
        else:
            direction = "neutral"
            strength = 0.3
        
        return {"direction": direction, "strength": strength}
    
    def find_nearest_support(self, price: float) -> Optional[float]:
        """Find nearest support level below price"""
        valid_levels = [s.price for s in self.support_levels if s.price < price]
        return min(valid_levels) if valid_levels else None
    
    def find_nearest_resistance(self, price: float) -> Optional[float]:
        """Find nearest resistance level above price"""
        valid_levels = [r.price for r in self.resistance_levels if r.price > price]
        return min(valid_levels) if valid_levels else None
    
    def calculate_vwap(self, df: pd.DataFrame) -> float:
        """
        Calculate Volume Weighted Average Price
        """
        if 'tick_volume' not in df.columns or len(df) == 0:
            return df['close'].iloc[-1] if len(df) > 0 else 0
        
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        volume = df['tick_volume']
        
        vwap = (typical_price * volume).sum() / volume.sum()
        return float(vwap)
    
    def get_trade_signal(self, df: pd.DataFrame, ml_direction: str) -> Dict:
        """
        Get trading signal combining patterns, S/R, and ML direction
        
        Args:
            df: DataFrame with price data
            ml_direction: Direction from ML model ('bullish' or 'bearish')
            
        Returns:
            Dictionary with trading recommendation
        """
        current_price = df['close'].iloc[-1]
        
        # Get recent patterns
        recent_patterns = self.patterns[-5:] if len(self.patterns) >= 5 else self.patterns
        
        # Calculate pattern sentiment
        bullish_patterns = sum(1 for p in recent_patterns if p.direction == "bullish")
        bearish_patterns = sum(1 for p in recent_patterns if p.direction == "bearish")
        
        # Get S/R
        nearest_support = self.find_nearest_support(current_price)
        nearest_resistance = self.find_nearest_resistance(current_price)
        
        # Get trend
        trend = self.identify_trend(df)
        
        # Calculate confluence
        confluence_score = 0.0
        reasons = []
        
        # ML Direction
        if ml_direction == "bullish":
            confluence_score += 0.3
            reasons.append(f"ML Signal: BULLISH")
        else:
            confluence_score += 0.3
            reasons.append(f"ML Signal: BEARISH")
        
        # Pattern alignment
        if ml_direction == "bullish" and bullish_patterns > bearish_patterns:
            confluence_score += 0.2
            reasons.append(f"Pattern Alignment: {bullish_patterns} bullish patterns")
        elif ml_direction == "bearish" and bearish_patterns > bullish_patterns:
            confluence_score += 0.2
            reasons.append(f"Pattern Alignment: {bearish_patterns} bearish patterns")
        
        # Trend alignment
        if trend['direction'] == ml_direction:
            confluence_score += 0.2 * trend['strength']
            reasons.append(f"Trend Alignment: {trend['direction']} ({trend['strength']:.1f})")
        
        # S/R position
        if ml_direction == "bullish" and nearest_support:
            distance_to_support = (current_price - nearest_support) / current_price
            if distance_to_support < 0.02:  # Within 2%
                confluence_score += 0.2
                reasons.append(f"Near Support: {nearest_support:.5f}")
        elif ml_direction == "bearish" and nearest_resistance:
            distance_to_resistance = (nearest_resistance - current_price) / current_price
            if distance_to_resistance < 0.02:
                confluence_score += 0.2
                reasons.append(f"Near Resistance: {nearest_resistance:.5f}")
        
        # Final decision
        if confluence_score >= 0.6:
            decision = "ENTRY"
            stop_loss = nearest_support if ml_direction == "bullish" else nearest_resistance
        elif confluence_score >= 0.4:
            decision = "CAUTION"
            stop_loss = nearest_support if ml_direction == "bullish" else nearest_resistance
        else:
            decision = "WAIT"
            stop_loss = None
        
        return {
            "decision": decision,
            "confidence": confluence_score,
            "ml_direction": ml_direction,
            "current_price": current_price,
            "stop_loss": stop_loss,
            "nearest_support": nearest_support,
            "nearest_resistance": nearest_resistance,
            "bullish_patterns": bullish_patterns,
            "bearish_patterns": bearish_patterns,
            "trend": trend,
            "reasons": reasons
        }
    
    def get_analysis_result(self, trend: Dict = None) -> Dict:
        """Get complete analysis as dictionary"""
        if trend is None:
            trend = {"direction": "neutral", "strength": 0}
        
        # Get recent patterns
        recent = self.patterns[-10:] if len(self.patterns) >= 10 else self.patterns
        
        return {
            "patterns": [
                {
                    "pattern": p.pattern,
                    "direction": p.direction,
                    "strength": p.strength,
                    "index": p.index
                }
                for p in recent
            ],
            "pattern_count": {
                "bullish": len([p for p in self.patterns if p.direction == "bullish"]),
                "bearish": len([p for p in self.patterns if p.direction == "bearish"]),
                "neutral": len([p for p in self.patterns if p.direction == "neutral"])
            },
            "support_levels": [
                {"price": s.price, "strength": s.strength}
                for s in self.support_levels[:5]
            ],
            "resistance_levels": [
                {"price": r.price, "strength": r.strength}
                for r in self.resistance_levels[:5]
            ],
            "trend": trend
        }


def main():
    """Test Price Action Analyzer"""
    import random
    
    print("="*60)
    print("PRICE ACTION ANALYZER TEST")
    print("="*60)
    
    # Create sample data
    data = []
    base_price = 1.1000
    
    for i in range(200):
        base_price += random.uniform(-0.001, 0.001)
        
        high = base_price + random.uniform(0.0005, 0.002)
        low = base_price - random.uniform(0.0005, 0.002)
        
        # Create some patterns
        if i == 50:
            # Hammer
            open_price = base_price
            close_price = base_price + 0.0008
            high = base_price + 0.0015
            low = base_price - 0.0002
        elif i == 100:
            # Shooting star
            open_price = base_price
            close_price = base_price - 0.0008
            high = base_price + 0.0002
            low = base_price - 0.0015
        else:
            close_price = base_price + random.uniform(-0.0005, 0.0005)
            open_price = base_price + random.uniform(-0.0005, 0.0005)
        
        data.append({
            "time": 1700000000 + i * 900,
            "open": open_price,
            "high": high,
            "low": low,
            "close": close_price,
            "tick_volume": random.randint(100, 1000)
        })
    
    df = pd.DataFrame(data)
    
    # Run analysis
    print("\n📊 Analyzing price action...")
    pa = PriceActionAnalyzer()
    result = pa.analyze(df)
    
    print(f"\n🎯 Results:")
    print(f"  Patterns Found: {len(result['patterns'])}")
    print(f"  Bullish: {result['pattern_count']['bullish']}, Bearish: {result['pattern_count']['bearish']}")
    print(f"  Support Levels: {len(result['support_levels'])}")
    print(f"  Resistance Levels: {len(result['resistance_levels'])}")
    print(f"  Trend: {result['trend']}")
    
    print(f"\n📈 Recent Patterns:")
    for p in result['patterns'][:5]:
        print(f"  {p['pattern']}: {p['direction']} ({p['strength']:.2f})")
    
    print(f"\n📊 Trade Signal (ML: bullish):")
    signal = pa.get_trade_signal(df, "bullish")
    print(f"  Decision: {signal['decision']}")
    print(f"  Confidence: {signal['confidence']:.2f}")
    print(f"  Support: {signal['nearest_support']}")
    print(f"  Resistance: {signal['nearest_resistance']}")
    
    print("\n✅ Price Action Analyzer test complete!")


if __name__ == "__main__":
    main()
