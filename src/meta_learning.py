"""
Helios ML Trading System - Strategy Selection and Meta-Learning
Advanced meta-learning system for dynamic strategy selection based on market regimes
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Union
import logging
from dataclasses import dataclass
from enum import Enum
import json
from collections import deque
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class MarketRegime(Enum):
    """Market regime classifications"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    BEARISH = "bearish"
    BULLISH = "bullish"
    UNKNOWN = "unknown"

class TimeRegime(Enum):
    """Time-based market regimes"""
    LONDON_SESSION = "london_session"
    NEW_YORK_SESSION = "new_york_session"
    ASIAN_SESSION = "asian_session"
    WEEKEND = "weekend"
    NEWS_TIME = "news_time"
    NORMAL = "normal"

@dataclass
class StrategyPerformance:
    """Strategy performance tracking"""
    name: str
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_profit: float = 0.0
    total_loss: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    last_updated: str = ""
    current_streak: int = 0
    
    def update(self, trade_result: Dict[str, Any]):
        """Update performance with new trade result"""
        self.total_trades += 1
        
        if trade_result['profit'] > 0:
            self.winning_trades += 1
            self.total_profit += trade_result['profit']
            self.current_streak += 1
        else:
            self.losing_trades += 1
            self.total_loss += abs(trade_result['profit'])
            self.current_streak = 0
            
        # Update metrics
        if self.total_trades > 0:
            self.win_rate = self.winning_trades / self.total_trades
            self.avg_win = self.total_profit / max(self.winning_trades, 1)
            self.avg_loss = self.total_loss / max(self.losing_trades, 1)
            self.profit_factor = self.total_profit / max(self.total_loss, 0.001)
        
        # Update max drawdown
        if trade_result.get('drawdown', 0) > self.max_drawdown:
            self.max_drawdown = trade_result['drawdown']
            
        self.last_updated = pd.Timestamp.now().isoformat()
    
    def get_score(self, market_conditions: Dict[str, Any]) -> float:
        """Calculate strategy score based on performance and market conditions"""
        score = 0.0
        
        # Base performance score (0-40 points)
        if self.total_trades >= 5:  # Minimum trades for reliable metrics
            score += self.win_rate * 20  # Win rate component (0-20)
            score += min(self.profit_factor * 10, 20)  # Profit factor component (0-20)
        
        # Recency score (0-30 points) - recent performance weighted higher
        if self.current_streak >= 3:
            score += min(self.current_streak * 5, 20)  # Winning streak bonus
        elif self.current_streak <= -3:
            score -= 20  # Losing streak penalty
        
        # Market condition adaptation (0-30 points)
        score += self._get_market_adaptation_score(market_conditions)
        
        # Minimum trades requirement
        if self.total_trades < 5:
            score *= 0.5  # Reduce score for strategies with insufficient data
        
        return max(score, 0)
    
    def _get_market_adaptation_score(self, market_conditions: Dict[str, Any]) -> float:
        """Calculate how well the strategy fits current market conditions"""
        score = 0.0
        
        # Volatility preference
        market_volatility = market_conditions.get('volatility', 'medium')
        if market_volatility == 'high' and self.name in ['scalping', 'breakout']:
            score += 10
        elif market_volatility == 'low' and self.name in ['mean_reversion', 'trend_following']:
            score += 10
        elif market_volatility == 'medium':
            score += 5  # Neutral bonus
        
        # Trend preference
        trend_direction = market_conditions.get('trend', 'sideways')
        if trend_direction == 'up' and self.name == 'trend_following':
            score += 10
        elif trend_direction == 'down' and self.name == 'mean_reversion':
            score += 10
        elif trend_direction == 'sideways' and self.name in ['mean_reversion', 'scalping']:
            score += 10
        
        # Session preference
        session = market_conditions.get('session', 'normal')
        if session == 'london_session' and self.name in ['scalping', 'trend_following']:
            score += 5
        elif session == 'new_york_session' and self.name in ['breakout', 'scalping']:
            score += 5
        elif session == 'asian_session' and self.name == 'mean_reversion':
            score += 5
        
        return min(score, 30)  # Cap at 30 points

class MetaLearningEngine:
    """Meta-learning engine for dynamic strategy selection"""
    
    def __init__(self, config, logger=None):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        
        # Strategy performance tracking
        self.strategy_performance: Dict[str, StrategyPerformance] = {}
        self.initialize_strategies()
        
        # Market regime detection
        self.regime_buffer = deque(maxlen=50)
        self.current_regime = MarketRegime.UNKNOWN
        self.current_time_regime = TimeRegime.NORMAL
        
        # Historical performance data
        self.performance_history = {}
        self.regime_performance = {}
        
        # Adaptation parameters
        self.min_trades_for_reliable_score = 5
        self.regime_adaptation_enabled = config.meta_learning.market_regime_detection
        self.volatility_analysis_enabled = config.meta_learning.volatility_analysis
        self.time_analysis_enabled = config.meta_learning.time_based_regimes
        
        self.logger.info("Meta-learning engine initialized")
    
    def initialize_strategies(self):
        """Initialize strategy performance tracking"""
        strategy_names = [s['name'] for s in self.config.strategy.strategies if s['enabled']]
        
        for name in strategy_names:
            self.strategy_performance[name] = StrategyPerformance(name=name)
            self.performance_history[name] = []
            self.regime_performance[name] = {}
        
        self.logger.info(f"Initialized {len(strategy_names)} strategies for tracking")
    
    def detect_market_regime(self, data: pd.DataFrame) -> Tuple[MarketRegime, Dict[str, Any]]:
        """Detect current market regime based on price action"""
        
        if len(data) < 50:  # Need sufficient data
            return MarketRegime.UNKNOWN, {}
        
        current_price = data['close'].iloc[-1]
        prices_20 = data['close'].iloc[-20:]
        prices_50 = data['close'].iloc[-50:]
        
        # Calculate trend indicators
        sma_20 = data['sma_20'].iloc[-1] if 'sma_20' in data.columns else None
        sma_50 = data['sma_50'].iloc[-1] if 'sma_50' in data.columns else None
        
        # Calculate volatility
        returns = data['close'].pct_change().dropna()
        volatility_20 = returns.tail(20).std() * np.sqrt(252)  # Annualized
        volatility_50 = returns.tail(50).std() * np.sqrt(252)
        
        # Trend detection
        if sma_20 is not None and sma_50 is not None:
            if current_price > sma_20 > sma_50:
                trend_strength = (current_price - sma_50) / sma_50
                if trend_strength > 0.02:  # 2% above 50-day MA
                    regime = MarketRegime.TRENDING_UP
                else:
                    regime = MarketRegime.BULLISH
            elif current_price < sma_20 < sma_50:
                trend_strength = (sma_50 - current_price) / sma_50
                if trend_strength > 0.02:  # 2% below 50-day MA
                    regime = MarketRegime.TRENDING_DOWN
                else:
                    regime = MarketRegime.BEARISH
            else:
                regime = MarketRegime.SIDEWAYS
        else:
            # Fallback trend detection using price action
            slope_20 = np.polyfit(range(20), prices_20, 1)[0]
            slope_50 = np.polyfit(range(50), prices_50, 1)[0]
            
            if slope_20 > 0 and slope_50 > 0:
                regime = MarketRegime.TRENDING_UP
            elif slope_20 < 0 and slope_50 < 0:
                regime = MarketRegime.TRENDING_DOWN
            else:
                regime = MarketRegime.SIDEWAYS
        
        # Volatility regime
        if volatility_20 > volatility_50 * 1.5:
            vol_regime = MarketRegime.HIGH_VOLATILITY
        elif volatility_20 < volatility_50 * 0.7:
            vol_regime = MarketRegime.LOW_VOLATILITY
        else:
            vol_regime = MarketRegime.UNKNOWN  # Normal volatility
        
        # Combine regimes
        if vol_regime == MarketRegime.HIGH_VOLATILITY:
            final_regime = MarketRegime.HIGH_VOLATILITY
        elif vol_regime == MarketRegime.LOW_VOLATILITY:
            final_regime = MarketRegime.LOW_VOLATILITY
        else:
            final_regime = regime
        
        # Store regime for history
        regime_info = {
            'timestamp': pd.Timestamp.now(),
            'regime': final_regime.value,
            'trend': 'up' if regime in [MarketRegime.TRENDING_UP, MarketRegime.BULLISH] else 
                    'down' if regime in [MarketRegime.TRENDING_DOWN, MarketRegime.BEARISH] else 'sideways',
            'volatility': 'high' if vol_regime == MarketRegime.HIGH_VOLATILITY else
                         'low' if vol_regime == MarketRegime.LOW_VOLATILITY else 'normal',
            'trend_strength': np.polyfit(range(20), prices_20, 1)[0] / current_price,
            'volatility_ratio': volatility_20 / max(volatility_50, 0.001)
        }
        
        self.regime_buffer.append(regime_info)
        self.current_regime = final_regime
        
        return final_regime, regime_info
    
    def detect_time_regime(self, timestamp: pd.Timestamp) -> TimeRegime:
        """Detect time-based market regime"""
        hour = timestamp.hour
        weekday = timestamp.weekday()
        
        # Weekend check
        if weekday >= 5:  # Saturday or Sunday
            return TimeRegime.WEEKEND
        
        # Session detection (UTC times)
        if 0 <= hour < 8:  # Asian session
            return TimeRegime.ASIAN_SESSION
        elif 8 <= hour < 16:  # London session
            return TimeRegime.LONDON_SESSION
        elif 16 <= hour < 24:  # New York session
            return TimeRegime.NEW_YORK_SESSION
        
        return TimeRegime.NORMAL
    
    def get_market_conditions(self, data: pd.DataFrame, timestamp: pd.Timestamp) -> Dict[str, Any]:
        """Get comprehensive market conditions"""
        regime, regime_info = self.detect_market_regime(data)
        time_regime = self.detect_time_regime(timestamp)
        
        market_conditions = {
            'regime': regime.value,
            'trend': regime_info.get('trend', 'sideways'),
            'volatility': regime_info.get('volatility', 'normal'),
            'trend_strength': regime_info.get('trend_strength', 0),
            'volatility_ratio': regime_info.get('volatility_ratio', 1),
            'session': time_regime.value,
            'hour': timestamp.hour,
            'weekday': timestamp.weekday(),
            'timestamp': timestamp
        }
        
        # Add technical indicators if available
        if 'rsi' in data.columns and not data.empty:
            current_rsi = data['rsi'].iloc[-1] if not pd.isna(data['rsi'].iloc[-1]) else 50
            market_conditions['rsi'] = current_rsi
            
            if current_rsi > 70:
                market_conditions['momentum'] = 'overbought'
            elif current_rsi < 30:
                market_conditions['momentum'] = 'oversold'
            else:
                market_conditions['momentum'] = 'neutral'
        
        return market_conditions
    
    def select_best_strategy(self, market_conditions: Dict[str, Any]) -> Tuple[str, float, Dict[str, float]]:
        """Select the best strategy based on current market conditions"""
        
        strategy_scores = {}
        
        for name, performance in self.strategy_performance.items():
            score = performance.get_score(market_conditions)
            strategy_scores[name] = score
        
        # Add market condition bonuses
        strategy_scores = self._apply_market_condition_bonuses(strategy_scores, market_conditions)
        
        if not strategy_scores:
            # Fallback to default strategy
            default_strategy = self.config.strategy.default_strategy
            self.logger.warning(f"No strategies available, falling back to {default_strategy}")
            return default_strategy, 0.5, {}
        
        # Select best strategy
        best_strategy = max(strategy_scores, key=strategy_scores.get)
        best_score = strategy_scores[best_strategy]
        
        # Log selection
        self.logger.info(f"Selected strategy: {best_strategy} (score: {best_score:.3f})")
        self.logger.debug(f"All strategy scores: {strategy_scores}")
        
        return best_strategy, best_score, strategy_scores
    
    def _apply_market_condition_bonuses(self, strategy_scores: Dict[str, float], 
                                      market_conditions: Dict[str, Any]) -> Dict[str, float]:
        """Apply additional bonuses based on market conditions"""
        
        # High volatility bonus
        if market_conditions.get('volatility') == 'high':
            strategy_scores['scalping'] = strategy_scores.get('scalping', 0) + 10
            strategy_scores['breakout'] = strategy_scores.get('breakout', 0) + 10
        
        # Low volatility bonus
        elif market_conditions.get('volatility') == 'low':
            strategy_scores['mean_reversion'] = strategy_scores.get('mean_reversion', 0) + 10
            strategy_scores['trend_following'] = strategy_scores.get('trend_following', 0) + 5
        
        # Trend preference
        trend = market_conditions.get('trend', 'sideways')
        if trend == 'up':
            strategy_scores['trend_following'] = strategy_scores.get('trend_following', 0) + 10
        elif trend == 'down':
            strategy_scores['mean_reversion'] = strategy_scores.get('mean_reversion', 0) + 10
        elif trend == 'sideways':
            strategy_scores['scalping'] = strategy_scores.get('scalping', 0) + 10
        
        # Session-specific bonuses
        session = market_conditions.get('session', 'normal')
        if session == 'london_session':
            strategy_scores['scalping'] = strategy_scores.get('scalping', 0) + 5
            strategy_scores['trend_following'] = strategy_scores.get('trend_following', 0) + 5
        elif session == 'new_york_session':
            strategy_scores['breakout'] = strategy_scores.get('breakout', 0) + 5
            strategy_scores['scalping'] = strategy_scores.get('scalping', 0) + 5
        
        return strategy_scores
    
    def update_strategy_performance(self, strategy_name: str, trade_result: Dict[str, Any]):
        """Update strategy performance with new trade result"""
        
        if strategy_name in self.strategy_performance:
            self.strategy_performance[strategy_name].update(trade_result)
            self.performance_history[strategy_name].append({
                'timestamp': pd.Timestamp.now(),
                'profit': trade_result['profit'],
                'regime': self.current_regime.value,
                'market_conditions': self.get_market_conditions(trade_result.get('data', pd.DataFrame()), 
                                                              trade_result.get('timestamp', pd.Timestamp.now()))
            })
            
            # Update regime-specific performance
            regime = self.current_regime.value
            if regime not in self.regime_performance[strategy_name]:
                self.regime_performance[strategy_name][regime] = StrategyPerformance(name=f"{strategy_name}_{regime}")
            
            self.regime_performance[strategy_name][regime].update(trade_result)
            
            self.logger.info(f"Updated performance for {strategy_name}: Win rate {self.strategy_performance[strategy_name].win_rate:.2%}")
    
    def should_adapt(self) -> bool:
        """Determine if the system should adapt strategy selection"""
        # Check if it's time for adaptation
        now = pd.Timestamp.now()
        if hasattr(self, 'last_adaptation'):
            time_since_adaptation = (now - self.last_adaptation).total_seconds() / 3600
            if time_since_adaptation < self.config.meta_learning.adaptation_interval_hours:
                return False
        
        # Check if we have enough recent data
        total_trades = sum(p.total_trades for p in self.strategy_performance.values())
        if total_trades < 10:
            return False
        
        self.last_adaptation = now
        return True
    
    def adapt_strategy_weights(self):
        """Adapt strategy weights based on recent performance"""
        # This could involve adjusting weights in the ensemble model
        # For now, we'll focus on selection logic
        
        adaptation_notes = []
        
        for name, performance in self.strategy_performance.items():
            if performance.total_trades >= self.min_trades_for_reliable_score:
                # Check recent performance
                recent_history = [h for h in self.performance_history[name] 
                                if (pd.Timestamp.now() - h['timestamp']).total_seconds() < 24*3600]
                
                if recent_history:
                    recent_profit = sum(h['profit'] for h in recent_history)
                    if recent_profit < -0.02:  # -2% in last 24 hours
                        adaptation_notes.append(f"Strategy {name} showing poor recent performance")
        
        if adaptation_notes:
            self.logger.warning(f"Adaptation triggered: {'; '.join(adaptation_notes)}")
        
        return adaptation_notes
    
    def get_strategy_recommendations(self, market_conditions: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed strategy recommendations"""
        
        best_strategy, best_score, all_scores = self.select_best_strategy(market_conditions)
        
        recommendations = {
            'primary_strategy': best_strategy,
            'confidence_score': best_score,
            'all_scores': all_scores,
            'market_regime': market_conditions,
            'adaptation_suggestions': self.adapt_strategy_weights() if self.should_adapt() else [],
            'total_tracked_strategies': len(self.strategy_performance),
            'timestamp': pd.Timestamp.now().isoformat()
        }
        
        return recommendations
    
    def save_performance_data(self, filepath: str):
        """Save performance data to file"""
        data = {
            'strategy_performance': {name: {
                'total_trades': perf.total_trades,
                'winning_trades': perf.winning_trades,
                'total_profit': perf.total_profit,
                'total_loss': perf.total_loss,
                'win_rate': perf.win_rate,
                'profit_factor': perf.profit_factor,
                'max_drawdown': perf.max_drawdown,
                'last_updated': perf.last_updated
            } for name, perf in self.strategy_performance.items()},
            'regime_performance': {name: {regime: {
                'total_trades': perf.total_trades,
                'win_rate': perf.win_rate,
                'profit_factor': perf.profit_factor
            } for regime, perf in regimes.items()} 
            for name, regimes in self.regime_performance.items()},
            'current_regime': self.current_regime.value
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        self.logger.info(f"Performance data saved to {filepath}")
    
    def load_performance_data(self, filepath: str):
        """Load performance data from file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Restore strategy performance
            for name, perf_data in data.get('strategy_performance', {}).items():
                if name in self.strategy_performance:
                    for attr, value in perf_data.items():
                        setattr(self.strategy_performance[name], attr, value)
            
            # Restore regime performance
            for name, regimes_data in data.get('regime_performance', {}).items():
                if name in self.regime_performance:
                    for regime, perf_data in regimes_data.items():
                        if regime in self.regime_performance[name]:
                            for attr, value in perf_data.items():
                                setattr(self.regime_performance[name][regime], attr, value)
            
            self.logger.info(f"Performance data loaded from {filepath}")
            
        except Exception as e:
            self.logger.error(f"Failed to load performance data: {e}")

if __name__ == "__main__":
    # Test the meta-learning engine
    import logging
    logging.basicConfig(level=logging.INFO)
    
    from config.config import config
    
    # Create sample market data
    dates = pd.date_range(start='2023-01-01', periods=200, freq='1H')
    np.random.seed(42)
    
    # Create trending market data
    price = 1.1000
    prices = []
    for i in range(200):
        trend = 0.0001 if i < 100 else -0.0001
        noise = np.random.randn() * 0.001
        price = price * (1 + trend + noise)
        prices.append(price)
    
    sample_data = pd.DataFrame({
        'open': prices,
        'high': [p * (1 + abs(np.random.randn()) * 0.0005) for p in prices],
        'low': [p * (1 - abs(np.random.randn()) * 0.0005) for p in prices],
        'close': prices,
        'tick_volume': np.random.randint(100, 1000, 200)
    }, index=dates)
    
    # Ensure high > low
    sample_data['high'] = np.maximum(sample_data['high'], 
                                   np.maximum(sample_data['open'], sample_data['close']))
    sample_data['low'] = np.minimum(sample_data['low'], 
                                  np.minimum(sample_data['open'], sample_data['close']))
    
    # Test meta-learning engine
    engine = MetaLearningEngine(config)
    
    # Test market regime detection
    regime, regime_info = engine.detect_market_regime(sample_data)
    print(f"Detected regime: {regime}")
    print(f"Regime info: {regime_info}")
    
    # Test time regime detection
    time_regime = engine.detect_time_regime(pd.Timestamp('2023-01-01 10:00:00'))
    print(f"Time regime: {time_regime}")
    
    # Test strategy selection
    market_conditions = engine.get_market_conditions(sample_data, pd.Timestamp('2023-01-01 10:00:00'))
    recommendations = engine.get_strategy_recommendations(market_conditions)
    print(f"Strategy recommendations: {recommendations}")
    
    # Test performance update
    trade_result = {
        'profit': 0.001,
        'drawdown': 0.001,
        'timestamp': pd.Timestamp.now()
    }
    engine.update_strategy_performance('trend_following', trade_result)
    
    # Get final recommendations
    final_recommendations = engine.get_strategy_recommendations(market_conditions)
    print(f"Final recommendations: {final_recommendations}")