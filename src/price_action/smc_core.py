"""
Helios ML Trading System - SMC Core Analyzer
Smart Money Concepts: Fair Value Gaps, Order Blocks, Liquidity Sweeps
Based on ICT (Inner Circle Trader) methodology
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class FVGType(Enum):
    """Fair Value Gap types"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"

class FVGStatus(Enum):
    """FVG mitigation status"""
    UNMITIGATED = "unmitigated"
    PARTIALLY_MITIGATED = "partially_mitigated"
    MITIGATED = "mitigated"

class OBType(Enum):
    """Order Block types"""
    BULLISH = "bullish"
    BEARISH = "bearish"

class LiquidityType(Enum):
    """Liquidity pool types"""
    EQUAL_HIGHS = "equal_highs"      # Double top
    EQUAL_LOWS = "equal_lows"        # Double bottom
    SWING_HIGH = "swing_high"        # Recent swing high
    SWING_LOW = "swing_low"          # Recent swing low

@dataclass
class FairValueGap:
    """Fair Value Gap (Imbalance)"""
    index: int
    type: str  # 'bullish' or 'bearish'
    top: float
    bottom: float
    mid: float  # Midpoint (common entry area)
    size: float  # Gap size in price
    created_at: int  # Candle index when created
    status: str  # 'unmitigated', 'partially_mitigated', 'mitigated'

@dataclass
class OrderBlock:
    """Order Block - institutional trading zone"""
    index: int
    type: str  # 'bullish' or 'bearish'
    start_price: float
    end_price: float
    midpoint: float
    size: float
    created_at: int
    is_valid: bool  # Whether it's still valid
    associated_fvg: bool  # Whether it has an associated FVG

@dataclass
class LiquidityPool:
    """Liquidity Pool (equal highs/lows)"""
    type: str
    price: float
    indices: List[int]  # Indices where this level exists
    strength: int  # Number of touches
    is_swept: bool  # Whether liquidity has been taken

class SMCAnalyzer:
    """
    Smart Money Concepts Analyzer
    Detects institutional trading patterns
    """
    
    def __init__(self, fvg_threshold_pips: float = 0.0010, 
                 ob_lookback: int = 20):
        """
        Initialize SMC Analyzer
        
        Args:
            fvg_threshold_pips: Minimum size for FVG detection (in price units)
            ob_lookback: Number of candles to look back for order blocks
        """
        self.fvg_threshold = fvg_threshold_pips
        self.ob_lookback = ob_lookback
        self.fvgs: List[FairValueGap] = []
        self.order_blocks: List[OrderBlock] = []
        self.liquidity_pools: List[LiquidityPool] = []
        
    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        Perform complete SMC analysis
        
        Args:
            df: DataFrame with OHLC data
            
        Returns:
            Dictionary with complete SMC analysis
        """
        # Reset
        self.fvgs = []
        self.order_blocks = []
        self.liquidity_pools = []
        
        # Find FVGs
        self.fvgs = self.find_fvgs(df)
        
        # Find Order Blocks
        self.order_blocks = self.find_order_blocks(df)
        
        # Find Liquidity Pools
        self.liquidity_pools = self.find_liquidity_pools(df)
        
        # Update mitigation status
        self.update_fvg_mitigation(df)
        
        return self.get_analysis_result()
    
    def find_fvgs(self, df: pd.DataFrame) -> List[FairValueGap]:
        """
        Find Fair Value Gaps (Imbalances)
        
        A FVG is a 3-candle pattern where:
        - Bullish FVG: Low[i-2] > High[i] (gap up)
        - Bearish FVG: High[i-2] < Low[i] (gap down)
        
        The gap should be unfilled (price hasn't returned to it)
        """
        fvgs = []
        
        if len(df) < 3:
            return fvgs
        
        highs = df['high'].values
        lows = df['low'].values
        closes = df['close'].values
        
        for i in range(2, len(df)):
            # Bullish FVG: Previous candle's low is above current candle's high
            # This shows strong buying pressure (gap up)
            if lows[i-2] > highs[i]:
                gap_size = lows[i-2] - highs[i]
                
                if gap_size >= self.fvg_threshold:  # Minimum size threshold
                    fvg = FairValueGap(
                        index=i,
                        type='bullish',
                        top=lows[i-2],  # Top of gap
                        bottom=highs[i],  # Bottom of gap
                        mid=(lows[i-2] + highs[i]) / 2,
                        size=gap_size,
                        created_at=i,
                        status='unmitigated'
                    )
                    fvgs.append(fvg)
            
            # Bearish FVG: Previous candle's high is below current candle's low
            # This shows strong selling pressure (gap down)
            elif highs[i-2] < lows[i]:
                gap_size = lows[i] - highs[i-2]
                
                if gap_size >= self.fvg_threshold:
                    fvg = FairValueGap(
                        index=i,
                        type='bearish',
                        top=lows[i],  # Top of gap (current low)
                        bottom=highs[i-2],  # Bottom of gap (prev high)
                        mid=(lows[i] + highs[i-2]) / 2,
                        size=gap_size,
                        created_at=i,
                        status='unmitigated'
                    )
                    fvgs.append(fvg)
        
        self.fvgs = fvgs
        return fvgs
    
    def update_fvg_mitigation(self, df: pd.DataFrame):
        """
        Update FVG mitigation status based on current price
        
        An FVG is mitigated when price enters and trades through it
        """
        if len(df) < 1:
            return
            
        current_price = df['close'].iloc[-1]
        
        for fvg in self.fvgs:
            if fvg.status == 'mitigated':
                continue
            
            if fvg.type == 'bullish':
                # Bullish FVG is mitigated when price drops below the bottom
                if current_price < fvg.bottom:
                    fvg.status = 'mitigated'
                # Check partial mitigation (price entered but didn't fill)
                elif current_price < fvg.mid:
                    fvg.status = 'partially_mitigated'
            
            elif fvg.type == 'bearish':
                # Bearish FVG is mitigated when price rises above the top
                if current_price > fvg.top:
                    fvg.status = 'mitigated'
                elif current_price > fvg.mid:
                    fvg.status = 'partially_mitigated'
    
    def find_order_blocks(self, df: pd.DataFrame) -> List[OrderBlock]:
        """
        Find Order Blocks
        
        An Order Block is the last candle before a strong move (FVG + BOS)
        Bullish OB: Bearish candle before bullish sequence
        Bearish OB: Bullish candle before bearish sequence
        """
        order_blocks = []
        
        if len(df) < 10:
            return order_blocks
        
        closes = df['close'].values
        opens = df['open'].values
        highs = df['high'].values
        lows = df['low'].values
        
        # Look for strong moves (check recent price action)
        for i in range(self.ob_lookback, len(df) - 5):
            # Look at next 5 candles for strong move
            start_price = closes[i]
            
            # Check for bullish move (5 consecutive higher closes)
            bullish_move = True
            for j in range(1, 5):
                if i + j >= len(closes):
                    bullish_move = False
                    break
                if closes[i + j] <= closes[i + j - 1]:
                    bullish_move = False
                    break
            
            if bullish_move:
                # This could be a bullish order block - find the last bearish candle
                for k in range(i - 1, max(0, i - 5), -1):
                    if closes[k] < opens[k]:  # Bearish candle
                        # Calculate OB range
                        ob_top = highs[k]
                        ob_bottom = lows[k]
                        ob_size = ob_top - ob_bottom
                        
                        # Only add if significant size
                        if ob_size > self.fvg_threshold:
                            order_blocks.append(OrderBlock(
                                index=k,
                                type='bullish',
                                start_price=ob_top,
                                end_price=ob_bottom,
                                midpoint=(ob_top + ob_bottom) / 2,
                                size=ob_size,
                                created_at=k,
                                is_valid=True,
                                associated_fvg=False  # Will be updated if FVG found
                            ))
                        break
            
            # Check for bearish move (5 consecutive lower closes)
            bearish_move = True
            for j in range(1, 5):
                if i + j >= len(closes):
                    bearish_move = False
                    break
                if closes[i + j] >= closes[i + j - 1]:
                    bearish_move = False
                    break
            
            if bearish_move:
                # This could be a bearish order block - find the last bullish candle
                for k in range(i - 1, max(0, i - 5), -1):
                    if closes[k] > opens[k]:  # Bullish candle
                        ob_top = highs[k]
                        ob_bottom = lows[k]
                        ob_size = ob_top - ob_bottom
                        
                        if ob_size > self.fvg_threshold:
                            order_blocks.append(OrderBlock(
                                index=k,
                                type='bearish',
                                start_price=ob_top,
                                end_price=ob_bottom,
                                midpoint=(ob_top + ob_bottom) / 2,
                                size=ob_size,
                                created_at=k,
                                is_valid=True,
                                associated_fvg=False
                            ))
                        break
        
        self.order_blocks = order_blocks
        return order_blocks
    
    def find_liquidity_pools(self, df: pd.DataFrame, tolerance: float = 0.0005) -> List[LiquidityPool]:
        """
        Find Liquidity Pools (Equal Highs/Lows)
        
        These are areas where institutions may have pending orders
        """
        pools = []
        
        if len(df) < 10:
            return pools
        
        highs = df['high'].values
        lows = df['low'].values
        closes = df['close'].values
        
        # Find equal highs (within tolerance)
        high_prices = []
        for i in range(len(highs) - 1):
            if abs(highs[i] - highs[i+1]) <= tolerance:
                # Found equal highs - check if there are more
                level = highs[i]
                indices = [i, i+1]
                
                # Look for more touches
                for j in range(i+2, len(highs)):
                    if abs(highs[j] - level) <= tolerance:
                        indices.append(j)
                
                if len(indices) >= 2:
                    pools.append(LiquidityPool(
                        type='equal_highs',
                        price=level,
                        indices=indices,
                        strength=len(indices),
                        is_swept=False
                    ))
        
        # Find equal lows
        for i in range(len(lows) - 1):
            if abs(lows[i] - lows[i+1]) <= tolerance:
                level = lows[i]
                indices = [i, i+1]
                
                for j in range(i+2, len(lows)):
                    if abs(lows[j] - level) <= tolerance:
                        indices.append(j)
                
                if len(indices) >= 2:
                    pools.append(LiquidityPool(
                        type='equal_lows',
                        price=level,
                        indices=indices,
                        strength=len(indices),
                        is_swept=False
                    ))
        
        # Check if liquidity is swept (price wicks through but closes back)
        current_price = closes[-1]
        
        for pool in pools:
            if pool.type == 'equal_highs':
                # Check if price swept above this level
                if current_price > pool.price * (1 + tolerance):
                    pool.is_swept = True
            elif pool.type == 'equal_lows':
                if current_price < pool.price * (1 - tolerance):
                    pool.is_swept = True
        
        self.liquidity_pools = pools
        return pools
    
    def get_active_fvgs(self) -> List[FairValueGap]:
        """Get unmitigated FVGs"""
        return [fvg for fvg in self.fvgs if fvg.status != 'mitigated']
    
    def get_valid_order_blocks(self) -> List[OrderBlock]:
        """Get valid (recent) order blocks"""
        # Order blocks are valid for about 4-8 candles after formation
        current_index = len(self.order_blocks[0].__dict__) if self.order_blocks else 0
        valid_blocks = []
        
        for ob in self.order_blocks:
            age = current_index - ob.index if hasattr(ob, 'index') else 0
            if age < 10:  # Within 10 candles
                valid_blocks.append(ob)
        
        return valid_blocks
    
    def get_trade_setup(self, df: pd.DataFrame, direction: str) -> Dict:
        """
        Get recommended trade setup based on SMC analysis
        
        Args:
            df: DataFrame with current price data
            direction: 'bullish' or 'bearish' (from ML signal)
            
        Returns:
            Dictionary with entry, stop loss, and invalidation levels
        """
        current_price = df['close'].iloc[-1]
        
        setup = {
            "direction": direction,
            "current_price": current_price,
            "entry_zones": [],
            "stop_loss": None,
            "invalidation": None,
            "confidence": 0.0
        }
        
        if direction == "bullish":
            # Look for bullish FVGs below current price (untouched)
            active_fvgs = [fvg for fvg in self.get_active_fvgs() 
                         if fvg.type == 'bullish' and fvg.bottom < current_price]
            
            for fvg in active_fvgs[:2]:  # Take top 2
                setup["entry_zones"].append({
                    "type": "FVG",
                    "entry": fvg.mid,
                    "stop": fvg.bottom,
                    "reason": "Buy at FVG mid, stop below FVG bottom"
                })
            
            # Look for bullish order blocks
            valid_obs = [ob for ob in self.get_valid_order_blocks() 
                        if ob.type == 'bullish' and ob.start_price < current_price]
            
            for ob in valid_obs[:2]:
                setup["entry_zones"].append({
                    "type": "ORDER_BLOCK",
                    "entry": ob.midpoint,
                    "stop": ob.end_price,
                    "reason": "Buy at OB midpoint, stop below OB"
                })
            
            # Set stop loss to nearest support (swing low or liquidity)
            if self.liquidity_pools:
                lows = [lp.price for lp in self.liquidity_pools if lp.type in ['equal_lows', 'swing_low']]
                if lows:
                    setup["stop_loss"] = min(lows)
                    setup["invalidation"] = min(lows) - (current_price - min(lows))
        
        elif direction == "bearish":
            # Look for bearish FVGs above current price
            active_fvgs = [fvg for fvg in self.get_active_fvgs() 
                         if fvg.type == 'bearish' and fvg.top > current_price]
            
            for fvg in active_fvgs[:2]:
                setup["entry_zones"].append({
                    "type": "FVG",
                    "entry": fvg.mid,
                    "stop": fvg.top,
                    "reason": "Sell at FVG mid, stop above FVG top"
                })
            
            # Look for bearish order blocks
            valid_obs = [ob for ob in self.get_valid_order_blocks() 
                        if ob.type == 'bearish' and ob.start_price > current_price]
            
            for ob in valid_obs[:2]:
                setup["entry_zones"].append({
                    "type": "ORDER_BLOCK",
                    "entry": ob.midpoint,
                    "stop": ob.start_price,
                    "reason": "Sell at OB midpoint, stop above OB"
                })
            
            # Set stop loss to nearest resistance
            if self.liquidity_pools:
                highs = [lp.price for lp in self.liquidity_pools if lp.type in ['equal_highs', 'swing_high']]
                if highs:
                    setup["stop_loss"] = max(highs)
                    setup["invalidation"] = max(highs) + (max(highs) - current_price)
        
        # Calculate confidence based on number of setups
        setup["confidence"] = min(len(setup["entry_zones"]) * 0.3, 0.9)
        
        return setup
    
    def get_analysis_result(self) -> Dict:
        """Get complete analysis as dictionary"""
        return {
            "fvgs": [
                {
                    "type": fvg.type,
                    "top": fvg.top,
                    "bottom": fvg.bottom,
                    "mid": fvg.mid,
                    "size": fvg.size,
                    "status": fvg.status,
                    "index": fvg.index
                }
                for fvg in self.fvgs[-10:]  # Last 10 FVGs
            ],
            "active_fvgs": len(self.get_active_fvgs()),
            "order_blocks": [
                {
                    "type": ob.type,
                    "midpoint": ob.midpoint,
                    "size": ob.size,
                    "index": ob.index
                }
                for ob in self.order_blocks[-10:]
            ],
            "liquidity_pools": [
                {
                    "type": lp.type,
                    "price": lp.price,
                    "strength": lp.strength,
                    "is_swept": lp.is_swept
                }
                for lp in self.liquidity_pools[-10:]
            ]
        }


def main():
    """Test the SMC Analyzer"""
    import random
    
    print("="*60)
    print("SMC ANALYZER TEST")
    print("="*60)
    
    # Create sample data with clear patterns
    data = []
    base_price = 1.1000
    
    for i in range(200):
        # Create some FVG patterns
        if 50 <= i <= 55:
            # Create bullish FVG at i=52
            if i == 52:
                base_price += 0.010  # Big gap up
            else:
                base_price += random.uniform(-0.001, 0.002)
        elif 100 <= i <= 105:
            # Create bearish FVG
            if i == 102:
                base_price -= 0.008  # Big gap down
            else:
                base_price += random.uniform(-0.002, 0.001)
        else:
            base_price += random.uniform(-0.001, 0.001)
        
        high = base_price + random.uniform(0.0005, 0.002)
        low = base_price - random.uniform(0.0005, 0.002)
        close = base_price + random.uniform(-0.0005, 0.0005)
        open_price = base_price - random.uniform(-0.0003, 0.0003)
        
        data.append({
            "time": 1700000000 + i * 900,
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "tick_volume": random.randint(100, 1000)
        })
    
    df = pd.DataFrame(data)
    
    # Run analysis
    print("\n📊 Analyzing SMC patterns...")
    analyzer = SMCAnalyzer(fvg_threshold_pips=0.0010)
    result = analyzer.analyze(df)
    
    print(f"\n🎯 Results:")
    print(f"  FVGs Found: {len(result['fvgs'])}")
    print(f"  Active FVGs: {result['active_fvgs']}")
    print(f"  Order Blocks: {len(result['order_blocks'])}")
    print(f"  Liquidity Pools: {len(result['liquidity_pools'])}")
    
    print(f"\n📈 Recent FVGs:")
    for fvg in result['fvgs'][:5]:
        print(f"  {fvg['type'].upper()}: {fvg['bottom']:.4f} - {fvg['top']:.4f} ({fvg['status']})")
    
    print(f"\n📊 Trade Setup (Bullish):")
    setup = analyzer.get_trade_setup(df, "bullish")
    print(f"  Entry Zones: {len(setup['entry_zones'])}")
    for zone in setup['entry_zones']:
        print(f"    - {zone['type']}: Entry {zone['entry']:.4f}, Stop {zone['stop']:.4f}")
    
    print("\n✅ SMC Analyzer test complete!")


if __name__ == "__main__":
    main()
