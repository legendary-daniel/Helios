"""
Helios ML Trading System - Trading Strategies
Implementation of multiple trading strategies with risk management
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Union
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
import talib
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class SignalType(Enum):
    """Trading signal types"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"

@dataclass
class TradingSignal:
    """Trading signal structure"""
    symbol: str
    signal_type: SignalType
    confidence: float
    price: float
    timestamp: pd.Timestamp
    strategy_name: str
    parameters: Dict[str, Any] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    position_size: Optional[float] = None
    risk_reward_ratio: Optional[float] = None

@dataclass
class Trade:
    """Trade structure"""
    symbol: str
    entry_time: pd.Timestamp
    exit_time: Optional[pd.Timestamp]
    entry_price: float
    exit_price: Optional[float]
    position_size: float
    side: str  # 'long' or 'short'
    strategy: str
    status: str  # 'open', 'closed', 'cancelled'
    pnl: float = 0.0
    commission: float = 0.0
    swap: float = 0.0
    comment: str = ""

class BaseStrategy(ABC):
    """Base class for all trading strategies"""
    
    def __init__(self, name: str, config, logger=None):
        self.name = name
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.current_position = None
        self.signal_history = []
        self.performance_metrics = {
            'total_signals': 0,
            'buy_signals': 0,
            'sell_signals': 0,
            'accuracy': 0.0
        }
        
    @abstractmethod
    def generate_signal(self, data: pd.DataFrame, symbol: str) -> Optional[TradingSignal]:
        """Generate trading signal based on market data"""
        pass
    
    def calculate_position_size(self, signal: TradingSignal, account_balance: float = 10000) -> float:
        """Calculate position size based on risk management rules"""
        risk_per_trade = self.config.risk.max_risk_per_trade
        
        if signal.stop_loss is not None:
            price_diff = abs(signal.price - signal.stop_loss)
            risk_amount = account_balance * risk_per_trade
            position_size = risk_amount / price_diff if price_diff > 0 else 0
        else:
            # Fixed percentage of account balance
            position_size = (account_balance * risk_per_trade) / signal.price
        
        # Apply maximum position limits
        max_position_value = account_balance * 0.1  # Max 10% of account per position
        max_size_by_value = max_position_value / signal.price
        
        return min(position_size, max_size_by_value)
    
    def calculate_stop_loss_take_profit(self, signal: TradingSignal, data: pd.DataFrame) -> Tuple[Optional[float], Optional[float]]:
        """Calculate stop loss and take profit levels"""
        
        if 'atr' in data.columns and not data.empty:
            atr = data['atr'].iloc[-1]
            if signal.signal_type == SignalType.BUY:
                stop_loss = signal.price - (atr * self.config.risk.stop_loss_atr_multiplier)
                take_profit = signal.price + (atr * self.config.risk.take_profit_ratio * self.config.risk.stop_loss_atr_multiplier)
            elif signal.signal_type == SignalType.SELL:
                stop_loss = signal.price + (atr * self.config.risk.stop_loss_atr_multiplier)
                take_profit = signal.price - (atr * self.config.risk.take_profit_ratio * self.config.risk.stop_loss_atr_multiplier)
            else:
                return None, None
        else:
            # Simple percentage-based stop loss/take profit
            stop_pct = 0.01  # 1%
            take_pct = self.config.risk.take_profit_ratio * stop_pct
            
            if signal.signal_type == SignalType.BUY:
                stop_loss = signal.price * (1 - stop_pct)
                take_profit = signal.price * (1 + take_pct)
            elif signal.signal_type == SignalType.SELL:
                stop_loss = signal.price * (1 + stop_pct)
                take_profit = signal.price * (1 - take_pct)
            else:
                return None, None
        
        return stop_loss, take_profit
    
    def update_performance(self, signal: TradingSignal, was_correct: bool = None):
        """Update strategy performance metrics"""
        self.performance_metrics['total_signals'] += 1
        
        if signal.signal_type in [SignalType.BUY, SignalType.SELL]:
            if signal.signal_type == SignalType.BUY:
                self.performance_metrics['buy_signals'] += 1
            else:
                self.performance_metrics['sell_signals'] += 1
            
            if was_correct is not None:
                # Calculate running accuracy
                correct_signals = getattr(self, '_correct_signals', 0) + (1 if was_correct else 0)
                total_valid_signals = getattr(self, '_total_valid_signals', 0) + 1
                
                self._correct_signals = correct_signals
                self._total_valid_signals = total_valid_signals
                
                self.performance_metrics['accuracy'] = correct_signals / total_valid_signals

class TrendFollowingStrategy(BaseStrategy):
    """Trend following strategy using moving averages and RSI"""
    
    def __init__(self, config, logger=None):
        super().__init__("TrendFollowing", config, logger)
        
        # Strategy parameters
        self.fast_ema = config.strategy.strategies[0]['parameters']['fast_ema']
        self.slow_ema = config.strategy.strategies[0]['parameters']['slow_ema']
        self.rsi_period = config.strategy.strategies[0]['parameters']['rsi_period']
        self.rsi_oversold = config.strategy.strategies[0]['parameters']['rsi_oversold']
        self.rsi_overbought = config.strategy.strategies[0]['parameters']['rsi_overbought']
    
    def generate_signal(self, data: pd.DataFrame, symbol: str) -> Optional[TradingSignal]:
        """Generate trend following signals"""
        
        if len(data) < max(self.slow_ema, self.rsi_period) + 2:
            return None
        
        current_time = data.index[-1]
        current_price = data['close'].iloc[-1]
        
        # Calculate indicators
        ema_fast = data['close'].ewm(span=self.fast_ema).mean().iloc[-1]
        ema_slow = data['close'].ewm(span=self.slow_ema).mean().iloc[-1]
        rsi = self._calculate_rsi(data['close'], self.rsi_period)
        
        if np.isnan(rsi):
            return None
        
        # Signal generation logic
        signal_type = SignalType.HOLD
        confidence = 0.0
        
        # Trend confirmation: EMA crossover with RSI filter
        if ema_fast > ema_slow and rsi > self.rsi_oversold and rsi < self.rsi_overbought:
            # Uptrend confirmed
            signal_type = SignalType.BUY
            confidence = min(0.9, (ema_fast - ema_slow) / ema_slow * 10 + (rsi - 50) / 50)
        elif ema_fast < ema_slow and rsi > self.rsi_oversold and rsi < self.rsi_overbought:
            # Downtrend confirmed
            signal_type = SignalType.SELL
            confidence = min(0.9, (ema_slow - ema_fast) / ema_slow * 10 + (50 - rsi) / 50)
        
        if signal_type == SignalType.HOLD:
            return None
        
        # Create signal
        signal = TradingSignal(
            symbol=symbol,
            signal_type=signal_type,
            confidence=confidence,
            price=current_price,
            timestamp=current_time,
            strategy_name=self.name
        )
        
        # Calculate stop loss and take profit
        stop_loss, take_profit = self.calculate_stop_loss_take_profit(signal, data)
        signal.stop_loss = stop_loss
        signal.take_profit = take_profit
        signal.risk_reward_ratio = (abs(current_price - take_profit) / abs(current_price - stop_loss)) if stop_loss else None
        
        # Calculate position size
        signal.position_size = self.calculate_position_size(signal)
        
        return signal
    
    def _calculate_rsi(self, prices: pd.Series, period: int) -> float:
        """Calculate RSI using talib"""
        try:
            rsi_values = talib.RSI(prices.values, timeperiod=period)
            return rsi_values[-1] if not np.isnan(rsi_values[-1]) else 50.0
        except:
            # Simple RSI calculation without talib
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50.0

class MeanReversionStrategy(BaseStrategy):
    """Mean reversion strategy using Bollinger Bands and RSI"""
    
    def __init__(self, config, logger=None):
        super().__init__("MeanReversion", config, logger)
        
        # Strategy parameters
        self.bb_period = config.strategy.strategies[1]['parameters']['bb_period']
        self.bb_std = config.strategy.strategies[1]['parameters']['bb_std']
        self.rsi_period = config.strategy.strategies[1]['parameters']['rsi_period']
        self.rsi_oversold = config.strategy.strategies[1]['parameters']['rsi_oversold']
        self.rsi_overbought = config.strategy.strategies[1]['parameters']['rsi_overbought']
    
    def generate_signal(self, data: pd.DataFrame, symbol: str) -> Optional[TradingSignal]:
        """Generate mean reversion signals"""
        
        if len(data) < self.bb_period + 2:
            return None
        
        current_time = data.index[-1]
        current_price = data['close'].iloc[-1]
        
        # Calculate indicators
        bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(data['close'])
        rsi = self._calculate_rsi(data['close'], self.rsi_period)
        
        if np.isnan(bb_upper) or np.isnan(rsi):
            return None
        
        # Signal generation logic
        signal_type = SignalType.HOLD
        confidence = 0.0
        
        # Mean reversion signals
        if current_price <= bb_lower and rsi < self.rsi_oversold:
            # Oversold condition - expect bounce
            signal_type = SignalType.BUY
            oversold_level = (self.rsi_oversold - rsi) / self.rsi_oversold
            bb_position = (current_price - bb_lower) / (bb_upper - bb_lower)
            confidence = min(0.9, oversold_level + (1 - bb_position))
            
        elif current_price >= bb_upper and rsi > self.rsi_overbought:
            # Overbought condition - expect pullback
            signal_type = SignalType.SELL
            overbought_level = (rsi - self.rsi_overbought) / (100 - self.rsi_overbought)
            bb_position = (current_price - bb_lower) / (bb_upper - bb_lower)
            confidence = min(0.9, overbought_level + bb_position)
        
        if signal_type == SignalType.HOLD:
            return None
        
        # Create signal
        signal = TradingSignal(
            symbol=symbol,
            signal_type=signal_type,
            confidence=confidence,
            price=current_price,
            timestamp=current_time,
            strategy_name=self.name
        )
        
        # Calculate stop loss and take profit
        stop_loss, take_profit = self.calculate_stop_loss_take_profit(signal, data)
        signal.stop_loss = stop_loss
        signal.take_profit = take_profit
        signal.risk_reward_ratio = (abs(current_price - take_profit) / abs(current_price - stop_loss)) if stop_loss else None
        
        # Calculate position size
        signal.position_size = self.calculate_position_size(signal)
        
        return signal
    
    def _calculate_bollinger_bands(self, prices: pd.Series) -> Tuple[float, float, float]:
        """Calculate Bollinger Bands"""
        try:
            bb_upper, bb_middle, bb_lower = talib.BBANDS(
                prices.values, 
                timeperiod=self.bb_period, 
                nbdevup=self.bb_std, 
                nbdevdn=self.bb_std
            )
            return bb_upper[-1], bb_middle[-1], bb_lower[-1]
        except:
            # Simple calculation without talib
            sma = prices.rolling(window=self.bb_period).mean()
            std = prices.rolling(window=self.bb_period).std()
            upper = sma + (std * self.bb_std)
            lower = sma - (std * self.bb_std)
            return upper.iloc[-1], sma.iloc[-1], lower.iloc[-1]
    
    def _calculate_rsi(self, prices: pd.Series, period: int) -> float:
        """Calculate RSI"""
        try:
            rsi_values = talib.RSI(prices.values, timeperiod=period)
            return rsi_values[-1] if not np.isnan(rsi_values[-1]) else 50.0
        except:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50.0

class BreakoutStrategy(BaseStrategy):
    """Breakout strategy using price momentum and volume"""
    
    def __init__(self, config, logger=None):
        super().__init__("Breakout", config, logger)
        
        # Strategy parameters
        self.breakout_period = config.strategy.strategies[2]['parameters']['breakout_period']
        self.volume_threshold = config.strategy.strategies[2]['parameters']['volume_threshold']
        self.price_momentum = config.strategy.strategies[2]['parameters']['price_momentum']
    
    def generate_signal(self, data: pd.DataFrame, symbol: str) -> Optional[TradingSignal]:
        """Generate breakout signals"""
        
        if len(data) < self.breakout_period + 2:
            return None
        
        current_time = data.index[-1]
        current_price = data['close'].iloc[-1]
        
        # Calculate indicators
        recent_high = data['high'].rolling(window=self.breakout_period).max().iloc[-1]
        recent_low = data['low'].rolling(window=self.breakout_period).min().iloc[-1]
        avg_volume = data['tick_volume'].rolling(window=20).mean().iloc[-1] if 'tick_volume' in data.columns else None
        
        # Calculate momentum
        price_momentum = (current_price - data['close'].iloc[-2]) / data['close'].iloc[-2]
        
        # Signal generation logic
        signal_type = SignalType.HOLD
        confidence = 0.0
        
        # Breakout conditions
        if current_price > recent_high and price_momentum > self.price_momentum:
            # Upward breakout
            signal_type = SignalType.BUY
            momentum_factor = (price_momentum - self.price_momentum) / self.price_momentum
            volume_factor = 1.0
            
            if avg_volume and data['tick_volume'].iloc[-1] > avg_volume * self.volume_threshold:
                volume_factor = 1.5
            
            confidence = min(0.9, momentum_factor * volume_factor)
            
        elif current_price < recent_low and price_momentum < -self.price_momentum:
            # Downward breakout
            signal_type = SignalType.SELL
            momentum_factor = abs(price_momentum + self.price_momentum) / self.price_momentum
            volume_factor = 1.0
            
            if avg_volume and data['tick_volume'].iloc[-1] > avg_volume * self.volume_threshold:
                volume_factor = 1.5
            
            confidence = min(0.9, momentum_factor * volume_factor)
        
        if signal_type == SignalType.HOLD:
            return None
        
        # Create signal
        signal = TradingSignal(
            symbol=symbol,
            signal_type=signal_type,
            confidence=confidence,
            price=current_price,
            timestamp=current_time,
            strategy_name=self.name
        )
        
        # Calculate stop loss and take profit
        stop_loss, take_profit = self.calculate_stop_loss_take_profit(signal, data)
        signal.stop_loss = stop_loss
        signal.take_profit = take_profit
        signal.risk_reward_ratio = (abs(current_price - take_profit) / abs(current_price - stop_loss)) if stop_loss else None
        
        # Calculate position size
        signal.position_size = self.calculate_position_size(signal)
        
        return signal

class ScalpingStrategy(BaseStrategy):
    """Scalping strategy for quick trades with tight stop losses"""
    
    def __init__(self, config, logger=None):
        super().__init__("Scalping", config, logger)
        
        # Strategy parameters
        self.tick_threshold = config.strategy.strategies[3]['parameters']['tick_threshold']
        self.time_limit_seconds = config.strategy.strategies[3]['parameters']['time_limit_seconds']
        self.profit_target = config.strategy.strategies[3]['parameters']['profit_target']
    
    def generate_signal(self, data: pd.DataFrame, symbol: str) -> Optional[TradingSignal]:
        """Generate scalping signals"""
        
        if len(data) < 10:
            return None
        
        current_time = data.index[-1]
        current_price = data['close'].iloc[-1]
        
        # Calculate tick-based momentum
        price_changes = data['close'].diff().abs().tail(5).mean()
        
        # Scalping signals based on quick price movements
        signal_type = SignalType.HOLD
        confidence = 0.0
        
        # Simple momentum-based scalping
        if price_changes > self.tick_threshold * 0.0001:  # Convert to price level
            recent_returns = data['close'].pct_change().tail(3)
            avg_return = recent_returns.mean()
            
            if avg_return > 0:
                signal_type = SignalType.BUY
                confidence = min(0.8, avg_return * 1000)  # Scale confidence
            elif avg_return < 0:
                signal_type = SignalType.SELL
                confidence = min(0.8, abs(avg_return) * 1000)
        
        if signal_type == SignalType.HOLD:
            return None
        
        # Create signal
        signal = TradingSignal(
            symbol=symbol,
            signal_type=signal_type,
            confidence=confidence,
            price=current_price,
            timestamp=current_time,
            strategy_name=self.name,
            parameters={'time_limit': self.time_limit_seconds}
        )
        
        # Tight stop loss and take profit for scalping
        stop_distance = current_price * 0.0005  # 0.05% stop loss
        profit_distance = current_price * self.profit_target  # Profit target
        
        if signal_type == SignalType.BUY:
            signal.stop_loss = current_price - stop_distance
            signal.take_profit = current_price + profit_distance
        else:
            signal.stop_loss = current_price + stop_distance
            signal.take_profit = current_price - profit_distance
        
        signal.risk_reward_ratio = profit_distance / stop_distance
        
        # Smaller position size for scalping
        signal.position_size = self.calculate_position_size(signal) * 0.5  # Reduce size
        
        return signal

class StrategyManager:
    """Manager for all trading strategies"""
    
    def __init__(self, config, logger=None):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.strategies = {}
        self.initialize_strategies()
        
        # Performance tracking
        self.strategy_performance = {}
        
    def initialize_strategies(self):
        """Initialize all enabled strategies"""
        for strategy_config in self.config.strategy.strategies:
            if strategy_config['enabled']:
                name = strategy_config['name']
                
                if name == 'trend_following':
                    self.strategies[name] = TrendFollowingStrategy(self.config, self.logger)
                elif name == 'mean_reversion':
                    self.strategies[name] = MeanReversionStrategy(self.config, self.logger)
                elif name == 'breakout':
                    self.strategies[name] = BreakoutStrategy(self.config, self.logger)
                elif name == 'scalping':
                    self.strategies[name] = ScalpingStrategy(self.config, self.logger)
                
                self.strategy_performance[name] = {
                    'total_signals': 0,
                    'buy_signals': 0,
                    'sell_signals': 0,
                    'avg_confidence': 0.0,
                    'last_signal_time': None
                }
        
        self.logger.info(f"Initialized {len(self.strategies)} trading strategies")
    
    def generate_signals(self, data: pd.DataFrame, symbol: str) -> List[TradingSignal]:
        """Generate signals from all strategies"""
        signals = []
        
        for strategy_name, strategy in self.strategies.items():
            try:
                signal = strategy.generate_signal(data, symbol)
                if signal:
                    signals.append(signal)
                    
                    # Update performance tracking
                    perf = self.strategy_performance[strategy_name]
                    perf['total_signals'] += 1
                    perf['avg_confidence'] = (perf['avg_confidence'] * (perf['total_signals'] - 1) + signal.confidence) / perf['total_signals']
                    perf['last_signal_time'] = signal.timestamp
                    
                    if signal.signal_type == SignalType.BUY:
                        perf['buy_signals'] += 1
                    elif signal.signal_type == SignalType.SELL:
                        perf['sell_signals'] += 1
                        
            except Exception as e:
                self.logger.error(f"Error generating signal from {strategy_name}: {e}")
        
        # Sort signals by confidence (highest first)
        signals.sort(key=lambda x: x.confidence, reverse=True)
        
        return signals
    
    def get_best_signal(self, signals: List[TradingSignal], max_signals: int = 1) -> List[TradingSignal]:
        """Get the best signal(s) based on confidence and strategy performance"""
        if not signals:
            return []
        
        # Filter signals by confidence threshold
        min_confidence = self.config.ml.confidence_threshold
        filtered_signals = [s for s in signals if s.confidence >= min_confidence]
        
        if not filtered_signals:
            # If no signals meet confidence threshold, return the best one if available
            return [signals[0]] if signals else []
        
        # Return top N signals
        return filtered_signals[:max_signals]
    
    def update_performance(self, strategy_name: str, was_correct: bool = None):
        """Update strategy performance"""
        if strategy_name in self.strategies:
            self.strategies[strategy_name].update_performance(None, was_correct)
    
    def get_strategy_status(self) -> Dict[str, Any]:
        """Get current status of all strategies"""
        status = {}
        
        for name, strategy in self.strategies.items():
            perf = self.strategy_performance[name]
            status[name] = {
                'enabled': True,
                'total_signals': perf['total_signals'],
                'buy_signals': perf['buy_signals'],
                'sell_signals': perf['sell_signals'],
                'avg_confidence': perf['avg_confidence'],
                'accuracy': strategy.performance_metrics.get('accuracy', 0.0),
                'last_signal_time': perf['last_signal_time'],
                'last_updated': pd.Timestamp.now().isoformat()
            }
        
        return status

if __name__ == "__main__":
    # Test the strategies
    import logging
    logging.basicConfig(level=logging.INFO)
    
    from config.config import config
    
    # Create sample market data
    dates = pd.date_range(start='2023-01-01', periods=100, freq='1min')
    np.random.seed(42)
    
    price = 1.1000
    prices = []
    for i in range(100):
        trend = 0.0001 * np.sin(i * 0.1)  # Sinusoidal trend
        noise = np.random.randn() * 0.0005
        price = price * (1 + trend + noise)
        prices.append(price)
    
    sample_data = pd.DataFrame({
        'open': prices,
        'high': [p * (1 + abs(np.random.randn()) * 0.0003) for p in prices],
        'low': [p * (1 - abs(np.random.randn()) * 0.0003) for p in prices],
        'close': prices,
        'tick_volume': np.random.randint(100, 1000, 100)
    }, index=dates)
    
    # Ensure high > low
    sample_data['high'] = np.maximum(sample_data['high'], 
                                   np.maximum(sample_data['open'], sample_data['close']))
    sample_data['low'] = np.minimum(sample_data['low'], 
                                  np.minimum(sample_data['open'], sample_data['close']))
    
    # Test strategies
    manager = StrategyManager(config)
    
    print("Testing all strategies...")
    signals = manager.generate_signals(sample_data, "EURUSD")
    
    print(f"Generated {len(signals)} signals:")
    for signal in signals:
        print(f"  {signal.strategy_name}: {signal.signal_type.value} at {signal.price:.5f} (confidence: {signal.confidence:.3f})")
    
    # Test best signal selection
    best_signals = manager.get_best_signal(signals)
    print(f"\nBest signals: {len(best_signals)}")
    for signal in best_signals:
        print(f"  {signal.strategy_name}: {signal.signal_type.value} at {signal.price:.5f}")
    
    # Get strategy status
    status = manager.get_strategy_status()
    print(f"\nStrategy status: {status}")