"""
Helios AI Trading System - Main Integration Module
Combines all AI components into unified trading system
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class HeliosAITrading:
    """
    Unified AI Trading System
    Combines all AI components for intelligent trading
    """
    
    def __init__(self, config: dict = None):
        """
        Initialize Helios AI Trading
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        
        # Initialize all AI components
        from .modules import (
            StructureAI, FVGAI, OBValidationAI,
            PatternRecognitionAI, RegimeDetectionAI,
            RiskManagementAI, DynamicLevelsAI
        )
        
        # Initialize components
        use_ai = self.config.get('use_ai', True)
        
        self.structure = StructureAI(use_ai=use_ai)
        self.fvg = FVGAI(use_ai=use_ai)
        self.order_block = OBValidationAI(use_ai=use_ai)
        self.pattern = PatternRecognitionAI(use_ai=use_ai)
        self.regime = RegimeDetectionAI(use_ai=use_ai)
        self.risk = RiskManagementAI(use_ai=use_ai)
        self.levels = DynamicLevelsAI(use_ai=use_ai)
        
        # State
        self.current_regime = None
        self.current_volatility = 0.0
        self.last_analysis = None
        
    def analyze_market(self, df: pd.DataFrame) -> Dict:
        """
        Perform complete market analysis with AI
        
        Args:
            df: OHLCV data
            
        Returns:
            Complete analysis dictionary
        """
        logger.info("Starting AI market analysis...")
        
        # 1. Detect Market Regime
        regime_result = self.regime.detect_regime(df)
        self.current_regime = regime_result['regime']
        
        # 2. Analyze Structure
        swing_points = []
        for i in range(20, len(df) - 20):
            is_swing, confidence = self.structure.is_swing_point(df, i, window=5)
            if is_swing:
                swing_points.append({
                    'index': i,
                    'type': 'high' if df['high'].iloc[i] > df['close'].iloc[i] else 'low',
                    'price': df['high'].iloc[i] if df['high'].iloc[i] > df['close'].iloc[i] else df['low'].iloc[i],
                    'confidence': confidence
                })
        
        # 3. Find FVGs
        fvg_analysis = self.fvg.analyze_fvgs(df)
        
        # 4. Find Order Blocks
        ob_analysis = self.order_block.analyze_order_blocks(df)
        
        # 5. Detect Patterns
        patterns = self.pattern.detect_patterns(df)
        
        # 6. Find S/R Levels
        sr_levels = self.levels.find_support_resistance(df)
        
        # 7. Calculate Volatility
        returns = df['close'].pct_change()
        self.current_volatility = returns.iloc[-20:].std()
        
        # 8. Predict Trend
        trend = self.structure.predict_trend(df)
        
        # Combine into unified score
        analysis = {
            'regime': regime_result,
            'trend': trend,
            'swing_points': swing_points[-10:],
            'fvgs': fvg_analysis[:5],
            'order_blocks': ob_analysis[:5],
            'patterns': patterns[-10:],
            'support_resistance': sr_levels,
            'volatility': self.current_volatility,
            'current_price': float(df['close'].iloc[-1])
        }
        
        self.last_analysis = analysis
        
        return analysis
    
    def generate_signal(self, 
                      df: pd.DataFrame,
                      ml_direction: str = None,
                      account_balance: float = 10000) -> Dict:
        """
        Generate trading signal with AI
        
        Args:
            df: OHLCV data
            ml_direction: Optional ML signal direction
            account_balance: Account balance for position sizing
            
        Returns:
            Trading signal dictionary
        """
        # Analyze market first
        if not self.last_analysis:
            analysis = self.analyze_market(df)
        else:
            analysis = self.last_analysis
        
        # Calculate AI confidence scores
        bullish_score = 0
        bearish_score = 0
        reasons = []
        
        # Trend contribution
        if analysis['trend']['direction'] == 'bullish':
            bullish_score += analysis['trend']['confidence'] * 30
            reasons.append(f"Bullish trend ({analysis['trend']['confidence']:.1%})")
        elif analysis['trend']['direction'] == 'bearish':
            bearish_score += analysis['trend']['confidence'] * 30
            reasons.append(f"Bearish trend ({analysis['trend']['confidence']:.1%})")
        
        # Regime contribution
        regime = analysis['regime']['regime']
        regime_confidence = analysis['regime']['confidence']
        
        if regime == 'trending':
            if ml_direction == 'bullish':
                bullish_score += regime_confidence * 20
            elif ml_direction == 'bearish':
                bearish_score += regime_confidence * 20
        elif regime == 'high_volatility':
            # Reduce scores in high volatility
            reasons.append("High volatility - reducing confidence")
        
        # FVG contribution
        for fvg in analysis['fvgs']:
            if fvg['recommendation'] == 'TRADE':
                if fvg['fvg']['type'] == 'bullish':
                    bullish_score += fvg['confidence'] * 15
                else:
                    bearish_score += fvg['confidence'] * 15
        
        # Pattern contribution
        recent_patterns = analysis['patterns']
        for pattern in recent_patterns:
            if pattern['direction'] == 'bullish':
                bullish_score += pattern['confidence'] * 10
            elif pattern['direction'] == 'bearish':
                bearish_score += pattern['confidence'] * 10
        
        # Support/Resistance contribution
        current_price = analysis['current_price']
        sr = analysis['support_resistance']
        
        # Find nearest support/resistance
        supports = [s['price'] for s in sr.get('support', []) if s['price'] < current_price]
        resistances = [r['price'] for r in sr.get('resistance', []) if r['price'] > current_price]
        
        if supports:
            nearest_support = max(supports)
            distance_pct = (current_price - nearest_support) / current_price
            if distance_pct < 0.01:
                bullish_score += 10
                reasons.append(f"Near support ({distance_pct:.1%})")
        
        if resistances:
            nearest_resistance = min(resistances)
            distance_pct = (nearest_resistance - current_price) / current_price
            if distance_pct < 0.01:
                bearish_score += 10
                reasons.append(f"Near resistance ({distance_pct:.1%})")
        
        # ML direction override
        if ml_direction:
            if ml_direction == 'bullish':
                bullish_score += 20
                reasons.append(f"ML signal: BULLISH")
            else:
                bearish_score += 20
                reasons.append(f"ML signal: BEARISH")
        
        # Determine final direction
        total_score = bullish_score + bearish_score
        if total_score > 0:
            confidence = abs(bullish_score - bearish_score) / total_score
        else:
            confidence = 0
        
        if bullish_score > bearish_score:
            direction = 'bullish'
            confidence = min(0.99, confidence + 0.3)
        elif bearish_score > bullish_score:
            direction = 'bearish'
            confidence = min(0.99, confidence + 0.3)
        else:
            direction = 'neutral'
            confidence = 0.3
        
        # Calculate position size
        position = self.risk.calculate_position_size(
            account_balance=account_balance,
            confidence=confidence,
            regime=regime,
            volatility=self.current_volatility
        )
        
        # Calculate stop loss and take profit
        entry = current_price
        stop_loss = self.risk.get_dynamic_stop_loss(
            entry=entry,
            direction=direction,
            volatility=self.current_volatility,
            regime=regime
        )
        
        take_profit = self.risk.get_dynamic_take_profit(
            entry=entry,
            direction=direction,
            stop_loss=stop_loss,
            regime=regime
        )
        
        # Risk assessment
        risk_assessment = self.risk.assess_trade_risk(
            entry_price=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=confidence,
            regime=regime
        )
        
        # Final decision
        if risk_assessment['action'] == 'REJECT':
            decision = 'NO_TRADE'
            reason = f"Risk too high: {risk_assessment['rating']}"
        elif confidence < 0.4:
            decision = 'WAIT'
            reason = "Low confidence"
        else:
            decision = 'ENTRY'
            reason = "Signal meets criteria"
        
        return {
            'decision': decision,
            'reason': reason,
            'direction': direction,
            'confidence': round(confidence, 2),
            'entry': round(entry, 5),
            'stop_loss': round(stop_loss, 5),
            'take_profit': round(take_profit, 5),
            'position_size_percent': position['position_size_percent'],
            'lot_size': position['lot_size'],
            'risk_assessment': risk_assessment,
            'regime': regime,
            'reasons': reasons,
            'analysis': {
                'trend': analysis['trend']['direction'],
                'swing_points': len(analysis['swing_points']),
                'fvgs': len(analysis['fvgs']),
                'patterns': len(analysis['patterns'])
            }
        }
    
    def get_market_conditions(self, df: pd.DataFrame) -> Dict:
        """
        Get current market conditions summary
        
        Args:
            df: OHLCV data
            
        Returns:
            Market conditions dictionary
        """
        if not self.last_analysis:
            self.analyze_market(df)
        
        return {
            'regime': self.current_regime,
            'volatility': self.current_volatility,
            'trend': self.last_analysis['trend']['direction'],
            'recommendations': self.risk.optimize_for_market(self.current_regime)
        }
    
    def update(self, df: pd.DataFrame):
        """
        Update analysis with new data
        
        Args:
            df: Latest OHLCV data
        """
        self.analyze_market(df)


def create_helios_ai(config: dict = None) -> HeliosAITrading:
    """
    Factory function to create Helios AI trading system
    
    Args:
        config: Configuration dictionary
        
    Returns:
        HeliosAITrading instance
    """
    return HeliosAITrading(config)


def main():
    """Test Helios AI Trading System"""
    import random
    
    print("="*60)
    print("HELIOS AI TRADING SYSTEM TEST")
    print("="*60)
    
    # Create sample data
    data = []
    price = 1.1000
    
    for i in range(500):
        # Create trending movement
        if i < 150:
            price += 0.0003
        elif i < 300:
            price -= 0.0003
        elif i < 400:
            price += 0.0002
        else:
            price += random.uniform(-0.001, 0.001)
        
        # Create patterns
        if 50 <= i <= 55:
            if i == 52:
                price += 0.005  # Gap
        elif 200 <= i <= 205:
            if i == 202:
                price -= 0.004  # Gap down
        
        high = price + random.uniform(0.0005, 0.002)
        low = price - random.uniform(0.0005, 0.002)
        close = price + random.uniform(-0.0005, 0.0005)
        open_price = price - random.uniform(-0.0003, 0.0003)
        
        data.append({
            "time": 1700000000 + i * 900,
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "tick_volume": random.randint(100, 1000)
        })
    
    df = pd.DataFrame(data)
    
    # Initialize AI
    print("\n🚀 Initializing Helios AI Trading System...")
    ai = HeliosAITrading(use_ai=False)
    
    # Analyze market
    print("\n📊 Analyzing market...")
    analysis = ai.analyze_market(df)
    
    print(f"\n✅ Analysis Results:")
    print(f"  Regime: {analysis['regime']['regime']}")
    print(f"  Trend: {analysis['trend']['direction']} ({analysis['trend']['confidence']:.1%})")
    print(f"  Volatility: {analysis['volatility']:.4f}")
    print(f"  Current Price: {analysis['current_price']:.5f}")
    print(f"  Swing Points: {len(analysis['swing_points'])}")
    print(f"  FVGs: {len(analysis['fvgs'])}")
    print(f"  Patterns: {len(analysis['patterns'])}")
    
    # Generate signal
    print("\n🎯 Generating Trading Signal...")
    signal = ai.generate_signal(df, ml_direction='bullish', account_balance=10000)
    
    print(f"\n✅ Trading Signal:")
    print(f"  Decision: {signal['decision']}")
    print(f"  Direction: {signal['direction']}")
    print(f"  Confidence: {signal['confidence']:.1%}")
    print(f"  Entry: {signal['entry']}")
    print(f"  Stop Loss: {signal['stop_loss']}")
    print(f"  Take Profit: {signal['take_profit']}")
    print(f"  Position Size: {signal['position_size_percent']:.1f}%")
    print(f"  Lot Size: {signal['lot_size']:.2f}")
    
    print(f"\n📝 Reasons:")
    for reason in signal['reasons']:
        print(f"  - {reason}")
    
    print(f"\n🛡️  Risk Assessment:")
    print(f"  Rating: {signal['risk_assessment']['rating']}")
    print(f"  Action: {signal['risk_assessment']['action']}")
    print(f"  Risk/Reward: {signal['risk_assessment']['risk_reward']:.1f}")
    
    # Market conditions
    print("\n📊 Market Conditions:")
    conditions = ai.get_market_conditions(df)
    print(f"  Regime: {conditions['regime']}")
    print(f"  Volatility: {conditions['volatility']:.4f}")
    print(f"  Trend: {conditions['trend']}")
    
    print("\n✅ Helios AI Trading System test complete!")


if __name__ == "__main__":
    main()
