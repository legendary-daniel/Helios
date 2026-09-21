"""
Helios ML Trading System - Market Structure Analyzer
Detects market structure: swing points, BOS, CHoCH, trend bias
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class TrendDirection(Enum):
    """Market trend direction"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"

class StructureType(Enum):
    """Market structure types"""
    HIGHER_HIGH = "higher_high"      # Uptrend
    LOWER_LOW = "lower_low"          # Downtrend
    HIGHER_LOW = "higher_low"        # Potential reversal
    LOWER_HIGH = "lower_high"        # Potential reversal
    CONSOLIDATION = "consolidation"  # Range

@dataclass
class SwingPoint:
    """Represents a swing high or low"""
    index: int
    time: int
    price: float
    type: str  # 'high' or 'low'
    strength: int  # Number of candles on each side

@dataclass
class BOS:
    """Break of Structure"""
    type: str  # 'bullish' or 'bearish'
    start_index: int
    end_index: int
    start_price: float
    end_price: float
    broken_swing_index: int
    momentum: float  # Strength of the break

class MarketStructureMapper:
    """
    Analyzes market structure and identifies institutional patterns
    """
    
    def __init__(self, swing_window: int = 5):
        """
        Initialize the market structure mapper
        
        Args:
            swing_window: Number of candles to check on each side for swing points
        """
        self.swing_window = swing_window
        self.swing_points: List[SwingPoint] = []
        self.bos_list: List[BOS] = []
        self.trend_bias = TrendDirection.NEUTRAL
        self.structure_type = StructureType.CONSOLIDATION
        
    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        Perform complete market structure analysis
        
        Args:
            df: DataFrame with OHLC data (must have high, low, close, open columns)
            
        Returns:
            Dictionary with complete structure analysis
        """
        # Reset analysis
        self.swing_points = []
        self.bos_list = []
        
        # Find swing points
        self.swing_points = self.find_swing_points(df)
        
        # Identify BOS
        self.bos_list = self.identify_bos(df)
        
        # Get trend bias
        self.trend_bias = self.get_trend_bias()
        
        # Get structure type
        self.structure_type = self.get_structure_type()
        
        return self.get_analysis_result()
    
    def find_swing_points(self, df: pd.DataFrame) -> List[SwingPoint]:
        """
        Find swing highs and lows (fractal points)
        
        A swing high is surrounded by lower highs
        A swing low is surrounded by higher lows
        """
        swing_points = []
        
        if len(df) < self.swing_window * 2 + 1:
            return swing_points
        
        highs = df['high'].values
        lows = df['low'].values
        times = df['time'].values
        
        for i in range(self.swing_window, len(df) - self.swing_window):
            # Check for swing high
            is_swing_high = True
            for j in range(1, self.swing_window + 1:
                if highs[i] <= highs[i-j] or highs[i] <= highs[i+j]:
                    is_swing_high = False
                    break
            
            if is_swing_high:
                # Calculate strength (how many candles on each side)
                strength = self.swing_window
                swing_points.append(SwingPoint(
                    index=i,
                    time=int(times[i]),
                    price=float(highs[i]),
                    type='high',
                    strength=strength
                ))
            
            # Check for swing low
            is_swing_low = True
            for j in range(1, self.swing_window + 1):
                if lows[i] >= lows[i-j] or lows[i] >= lows[i+j]:
                    is_swing_low = False
                    break
            
            if is_swing_low:
                swing_points.append(SwingPoint(
                    index=i,
                    time=int(times[i]),
                    price=float(lows[i]),
                    type='low',
                    strength=strength
                ))
        
        self.swing_points = swing_points
        return swing_points
    
    def identify_bos(self, df: pd.DataFrame) -> List[BOS]:
        """
        Identify Break of Structure (BOS)
        
        BOS occurs when price breaks a previous swing point in the direction of the trend
        Important: BOS is based on CLOSE, not wick
        """
        bos_list = []
        
        if len(self.swing_points) < 2:
            return bos_list
        
        closes = df['close'].values
        highs = df['high'].values
        lows = df['low'].values
        
        # Get recent swing points
        recent_swings = self.swing_points[-10:]  # Last 10 swing points
        
        for i in range(1, len(recent_swings)):
            prev_swing = recent_swings[i-1]
            curr_swing = recent_swings[i]
            
            # Bullish BOS: Breaking above a previous swing high
            if prev_swing.type == 'high' and curr_swing.type == 'high':
                # Check if current close is above previous swing high
                if curr_swing.index < len(closes):
                    if closes[curr_swing.index] > prev_swing.price:
                        # Calculate momentum (how far broken)
                        momentum = (closes[curr_swing.index] - prev_swing.price) / prev_swing.price * 100
                        
                        bos_list.append(BOS(
                            type='bullish',
                            start_index=prev_swing.index,
                            end_index=curr_swing.index,
                            start_price=prev_swing.price,
                            end_price=closes[curr_swing.index],
                            broken_swing_index=prev_swing.index,
                            momentum=momentum
                        ))
            
            # Bearish BOS: Breaking below a previous swing low
            elif prev_swing.type == 'low' and curr_swing.type == 'low':
                if curr_swing.index < len(closes):
                    if closes[curr_swing.index] < prev_swing.price:
                        momentum = (prev_swing.price - closes[curr_swing.index]) / prev_swing.price * 100
                        
                        bos_list.append(BOS(
                            type='bearish',
                            start_index=prev_swing.index,
                            end_index=curr_swing.index,
                            start_price=prev_swing.price,
                            end_price=closes[curr_swing.index],
                            broken_swing_index=prev_swing.index,
                            momentum=momentum
                        ))
        
        self.bos_list = bos_list
        return bos_list
    
    def identify_choch(self, df: pd.DataFrame) -> Optional[BOS]:
        """
        Identify Change of Character (CHoCH)
        
        CHoCH is the first break of structure against the current trend
        It signals a potential trend reversal
        """
        if len(self.bos_list) < 2:
            return None
        
        # Get current trend direction
        trend = self.get_trend_bias()
        
        # Get recent BOS
        recent_bos = self.bos_list[-1]
        
        # If trend is bullish and we get a bearish BOS, it's CHoCH
        if trend == TrendDirection.BULLISH and recent_bos.type == 'bearish':
            return recent_bos
        
        # If trend is bearish and we get a bullish BOS, it's CHoCH
        if trend == TrendDirection.BEARISH and recent_bos.type == 'bullish':
            return recent_bos
        
        return None
    
    def get_trend_bias(self) -> TrendDirection:
        """
        Determine current trend bias based on structure
        """
        if len(self.swing_points) < 4:
            return TrendDirection.NEUTRAL
        
        # Get last 4 swing points
        recent = self.swing_points[-4:]
        
        # Higher highs and higher lows = Uptrend
        highs = [s for s in recent if s.type == 'high']
        lows = [s for s in recent if s.type == 'low']
        
        if len(highs) >= 2 and len(lows) >= 2:
            if highs[-1].price > highs[-2].price and lows[-1].price > lows[-2].price:
                return TrendDirection.BULLISH
            
            if highs[-1].price < highs[-2].price and lows[-1].price < lows[-2].price:
                return TrendDirection.BEARISH
        
        return TrendDirection.NEUTRAL
    
    def get_structure_type(self) -> StructureType:
        """Determine current structure type"""
        if len(self.swing_points) < 4:
            return StructureType.CONSOLIDATION
        
        recent = self.swing_points[-4:]
        
        highs = [s for s in recent if s.type == 'high']
        lows = [s for s in recent if s.type == 'low']
        
        if len(highs) >= 2 and len(lows) >= 2:
            if highs[-1].price > highs[-2].price and lows[-1].price > lows[-2].price:
                return StructureType.HIGHER_HIGH
            if highs[-1].price < highs[-2].price and lows[-1].price < lows[-2].price:
                return StructureType.LOWER_LOW
            if highs[-1].price > highs[-2].price and lows[-1].price < lows[-2].price:
                return StructureType.HIGHER_LOW
            if highs[-1].price < highs[-2].price and lows[-1].price > lows[-2].price:
                return StructureType.LOWER_HIGH
        
        return StructureType.CONSOLIDATION
    
    def get_recent_swing_high(self) -> Optional[SwingPoint]:
        """Get the most recent swing high"""
        highs = [s for s in self.swing_points if s.type == 'high']
        return highs[-1] if highs else None
    
    def get_recent_swing_low(self) -> Optional[SwingPoint]:
        """Get the most recent swing low"""
        lows = [s for s in self.swing_points if s.type == 'low']
        return lows[-1] if lows else None
    
    def get_analysis_result(self) -> Dict:
        """Get complete analysis as dictionary"""
        return {
            "trend_bias": self.trend_bias.value,
            "structure_type": self.structure_type.value,
            "swing_points": [
                {
                    "index": s.index,
                    "time": s.time,
                    "price": s.price,
                    "type": s.type,
                    "strength": s.strength
                }
                for s in self.swing_points[-10:]  # Last 10 swing points
            ],
            "bos": [
                {
                    "type": b.type,
                    "start_index": b.start_index,
                    "end_index": b.end_index,
                    "momentum": round(b.momentum, 4)
                }
                for b in self.bos_list[-5:]  # Last 5 BOS
            ],
            "recent_high": {
                "price": self.get_recent_swing_high().price,
                "index": self.get_recent_swing_high().index
            } if self.get_recent_swing_high() else None,
            "recent_low": {
                "price": self.get_recent_swing_low().price,
                "index": self.get_recent_swing_low().index
            } if self.get_recent_swing_low() else None
        }


def main():
    """Test the market structure analyzer"""
    import random
    
    # Generate sample data
    print("="*60)
    print("MARKET STRUCTURE ANALYZER TEST")
    print("="*60)
    
    # Create sample data with clear structure
    data = []
    base_price = 1.1000
    
    for i in range(200):
        # Create trending movement with swings
        if i < 50:
            # Uptrend
            base_price += 0.001
            trend = 1
        elif i < 100:
            # Downtrend
            base_price -= 0.001
            trend = -1
        else:
            # Consolidation
            trend = 0
        
        # Add some noise
        noise = random.uniform(-0.0005, 0.0005)
        
        high = base_price + abs(noise) + 0.001
        low = base_price - abs(noise) - 0.001
        close = base_price + noise
        open_price = base_price - noise/2
        
        data.append({
            "time": 1700000000 + i * 900,  # 15-minute candles
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "tick_volume": random.randint(100, 1000)
        })
    
    df = pd.DataFrame(data)
    
    # Run analysis
    print("\n📊 Analyzing market structure...")
    mapper = MarketStructureMapper(swing_window=5)
    result = mapper.analyze(df)
    
    print(f"\n🎯 Results:")
    print(f"  Trend Bias: {result['trend_bias']}")
    print(f"  Structure Type: {result['structure_type']}")
    print(f"  Swing Points Found: {len(result['swing_points'])}")
    print(f"  BOS Found: {len(result['bos'])}")
    
    print(f"\n📈 Recent Swing Points:")
    for sp in result['swing_points'][-5:]:
        print(f"  {sp['type'].upper()}: {sp['price']:.4f} (index: {sp['index']})")
    
    print(f"\n🔄 Recent BOS:")
    for bos in result['bos']:
        print(f"  {bos['type'].upper()}: {bos['momentum']:.2f}% momentum")
    
    print("\n✅ Market Structure Analyzer test complete!")


if __name__ == "__main__":
    main()
