"""
Helios ML Trading System - Main Trading System
Core coordinator that integrates all components for automated trading
"""

import asyncio
import threading
import time
import logging
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import pickle

# Import all system components
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from config.config import config
from src.data_processor import DataProcessor
from src.ml_models import ModelFactory, EnsembleModel
from src.meta_learning import MetaLearningEngine
from src.trading_strategies import StrategyManager, SignalType
from src.mt5_interface import MT5Interface, TradeRequest

class HeliosTradingSystem:
    """Main trading system coordinator"""
    
    def __init__(self, config_path: str = "config/config.json", logger=None):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize all components
        self.data_processor = DataProcessor(self.config, self.logger)
        self.mt5_interface = MT5Interface(self.config, self.logger)
        self.meta_learning = MetaLearningEngine(self.config, self.logger)
        self.strategy_manager = StrategyManager(self.config, self.logger)
        
        # ML Models
        self.model_factory = ModelFactory()
        self.ml_models = {}
        
        # System state
        self.is_running = False
        self.last_training_time = None
        self.model_performance = {}
        self.daily_pnl = 0.0
        self.total_trades = 0
        self.successful_trades = 0
        
        # Data storage
        self.market_data_cache = {}
        self.processed_data_cache = {}
        self.signals_history = []
        
        # Trading parameters
        self.max_open_positions = self.config.risk.max_open_positions
        self.min_confidence_threshold = self.config.ml.confidence_threshold
        
        self.logger.info("Helios Trading System initialized")
    
    async def initialize(self) -> bool:
        """Initialize the trading system"""
        try:
            self.logger.info("Initializing Helios Trading System...")
            
            # Initialize MT5 connection
            if not self.mt5_interface.initialize():
                self.logger.error("Failed to initialize MT5 connection")
                return False
            
            # Load or train ML models
            await self._initialize_ml_models()
            
            # Load meta-learning data
            self._load_meta_learning_data()
            
            # Initialize strategy performance tracking
            self._initialize_strategy_tracking()
            
            self.logger.info("Helios Trading System initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize trading system: {e}")
            return False
    
    async def start_trading(self):
        """Start the automated trading system"""
        if self.is_running:
            self.logger.warning("Trading system is already running")
            return
        
        self.logger.info("Starting Helios Automated Trading System...")
        self.is_running = True
        
        try:
            # Start main trading loop
            await self._main_trading_loop()
            
        except Exception as e:
            self.logger.error(f"Error in trading loop: {e}")
        finally:
            self.is_running = False
            self.logger.info("Trading system stopped")
    
    async def stop_trading(self):
        """Stop the trading system"""
        self.logger.info("Stopping trading system...")
        self.is_running = False
    
    async def _main_trading_loop(self):
        """Main trading loop"""
        while self.is_running:
            try:
                start_time = time.time()
                
                # 1. Get market data for all symbols
                market_data = await self._update_market_data()
                
                if market_data:
                    # 2. Process market data and generate features
                    processed_data = await self._process_market_data(market_data)
                    
                    # 3. Generate trading signals
                    signals = await self._generate_trading_signals(processed_data)
                    
                    # 4. Execute trades if signals meet criteria
                    await self._execute_trades(signals, processed_data)
                    
                    # 5. Update performance and meta-learning
                    await self._update_performance_tracking()
                    
                    # 6. Check if models need retraining
                    await self._check_model_retraining()
                
                # 7. Send status update
                await self._send_status_update()
                
                # Calculate sleep time to maintain desired update frequency
                elapsed_time = time.time() - start_time
                sleep_time = max(0, self.config.data.real_time_update_interval - elapsed_time)
                
                await asyncio.sleep(sleep_time)
                
            except Exception as e:
                self.logger.error(f"Error in main trading loop: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def _update_market_data(self) -> Dict[str, pd.DataFrame]:
        """Update market data for all configured symbols"""
        market_data = {}
        
        for symbol in self.config.data.symbols:
            try:
                # Get data for multiple timeframes
                symbol_data = {}
                for timeframe in self.config.data.timeframes:
                    data = self.mt5_interface.get_market_data(symbol, timeframe, 500)
                    if data is not None:
                        symbol_data[timeframe] = data
                
                if symbol_data:
                    market_data[symbol] = symbol_data
                    self.logger.debug(f"Updated data for {symbol}")
                    
            except Exception as e:
                self.logger.error(f"Error updating data for {symbol}: {e}")
        
        return market_data
    
    async def _process_market_data(self, market_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """Process market data and generate features"""
        processed_data = {}
        
        for symbol, timeframes_data in market_data.items():
            try:
                # Use H1 data as primary for processing
                if 'H1' in timeframes_data:
                    primary_data = timeframes_data['H1'].copy()
                else:
                    # Use the first available timeframe
                    primary_data = list(timeframes_data.values())[0].copy()
                
                # Add multi-timeframe features
                for tf_name, tf_data in timeframes_data.items():
                    if tf_name != list(timeframes_data.keys())[0]:  # Skip primary
                        # Align timestamps
                        aligned_data = tf_data.reindex(primary_data.index, method='ffill')
                        for col in aligned_data.columns:
                            if col not in ['open', 'high', 'low', 'close', 'tick_volume']:
                                primary_data[f'{col}_{tf_name}'] = aligned_data[col]
                
                # Process features
                processed_symbol_data = self.data_processor.process_market_data(primary_data, symbol)
                
                if processed_symbol_data is not None and not processed_symbol_data.empty:
                    processed_data[symbol] = processed_symbol_data
                    
            except Exception as e:
                self.logger.error(f"Error processing data for {symbol}: {e}")
        
        return processed_data
    
    async def _generate_trading_signals(self, processed_data: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
        """Generate trading signals using ML models and strategies"""
        all_signals = []
        
        for symbol, data in processed_data.items():
            try:
                # 1. Get strategy signals
                strategy_signals = self.strategy_manager.generate_signals(data, symbol)
                
                # 2. Get ML model predictions
                ml_predictions = await self._get_ml_predictions(data, symbol)
                
                # 3. Get meta-learning recommendations
                market_conditions = self.meta_learning.get_market_conditions(
                    data, datetime.now()
                )
                strategy_recommendations = self.meta_learning.get_strategy_recommendations(
                    market_conditions
                )
                
                # 4. Combine signals
                combined_signals = self._combine_signals(
                    strategy_signals, ml_predictions, strategy_recommendations, 
                    market_conditions, symbol
                )
                
                all_signals.extend(combined_signals)
                
            except Exception as e:
                self.logger.error(f"Error generating signals for {symbol}: {e}")
        
        return all_signals
    
    async def _get_ml_predictions(self, data: pd.DataFrame, symbol: str) -> Dict[str, float]:
        """Get predictions from ML models"""
        predictions = {}
        
        try:
            # Prepare features for prediction
            feature_cols = [col for col in data.columns 
                          if col not in ['open', 'high', 'low', 'close', 'tick_volume', 'symbol', 'timestamp']]
            
            if len(feature_cols) == 0 or data.empty:
                return predictions
            
            X = data[feature_cols].tail(1)  # Get latest row
            
            # Get predictions from each model
            for model_name, model in self.ml_models.items():
                try:
                    pred = model.predict(X)
                    if len(pred) > 0:
                        predictions[model_name] = pred[0]
                except Exception as e:
                    self.logger.error(f"ML prediction error for {model_name}: {e}")
            
        except Exception as e:
            self.logger.error(f"Error getting ML predictions for {symbol}: {e}")
        
        return predictions
    
    def _combine_signals(self, strategy_signals: List, ml_predictions: Dict[str, float], 
                        strategy_recommendations: Dict[str, Any], market_conditions: Dict[str, Any],
                        symbol: str) -> List[Dict[str, Any]]:
        """Combine strategy and ML signals with meta-learning decisions"""
        combined_signals = []
        
        # Get the recommended strategy from meta-learning
        recommended_strategy = strategy_recommendations.get('primary_strategy', 'trend_following')
        strategy_score = strategy_recommendations.get('confidence_score', 0.5)
        
        # Process strategy signals
        for signal in strategy_signals:
            try:
                # Calculate combined confidence
                ml_confidence = self._get_ml_confidence(ml_predictions, signal.signal_type)
                total_confidence = (signal.confidence * 0.7 + 
                                  ml_confidence * 0.2 + 
                                  strategy_score * 0.1)
                
                # Apply market condition filters
                if self._should_execute_signal(signal, market_conditions, total_confidence):
                    combined_signal = {
                        'symbol': symbol,
                        'signal_type': signal.signal_type.value,
                        'confidence': total_confidence,
                        'price': signal.price,
                        'timestamp': signal.timestamp,
                        'strategy': signal.strategy_name,
                        'stop_loss': signal.stop_loss,
                        'take_profit': signal.take_profit,
                        'position_size': signal.position_size,
                        'risk_reward_ratio': signal.risk_reward_ratio,
                        'ml_predictions': ml_predictions,
                        'market_conditions': market_conditions,
                        'strategy_score': strategy_score,
                        'ml_confidence': ml_confidence
                    }
                    combined_signals.append(combined_signal)
                    
            except Exception as e:
                self.logger.error(f"Error combining signals: {e}")
        
        return combined_signals
    
    def _get_ml_confidence(self, ml_predictions: Dict[str, float], signal_type: SignalType) -> float:
        """Calculate confidence from ML predictions"""
        if not ml_predictions:
            return 0.5  # Neutral confidence
        
        # Analyze predictions for signal direction
        positive_predictions = [p for p in ml_predictions.values() if p > 0]
        negative_predictions = [p for p in ml_predictions.values() if p < 0]
        
        if signal_type == SignalType.BUY:
            confidence = len(positive_predictions) / len(ml_predictions)
        elif signal_type == SignalType.SELL:
            confidence = len(negative_predictions) / len(ml_predictions)
        else:
            confidence = 0.5
        
        return min(0.9, confidence + 0.3)  # Scale confidence
    
    def _should_execute_signal(self, signal, market_conditions: Dict[str, Any], 
                             total_confidence: float) -> bool:
        """Determine if a signal should be executed based on market conditions"""
        
        # Check confidence threshold
        if total_confidence < self.min_confidence_threshold:
            return False
        
        # Check maximum open positions
        current_positions = len(self.mt5_interface.get_open_positions())
        if current_positions >= self.max_open_positions:
            return False
        
        # Check daily loss limit
        if self.daily_pnl < -self.config.risk.max_daily_loss * 10000:  # Assume 10k account
            return False
        
        # Check strategy suitability for market regime
        strategy_name = signal.strategy_name
        regime = market_conditions.get('regime', 'unknown')
        
        # Apply regime-specific filters
        regime_filters = {
            'high_volatility': ['scalping', 'breakout'],
            'low_volatility': ['mean_reversion', 'trend_following'],
            'trending_up': ['trend_following'],
            'trending_down': ['mean_reversion'],
            'sideways': ['mean_reversion', 'scalping']
        }
        
        if regime in regime_filters:
            if strategy_name not in regime_filters[regime]:
                return False
        
        return True
    
    async def _execute_trades(self, signals: List[Dict[str, Any]], processed_data: Dict[str, pd.DataFrame]):
        """Execute trades based on signals"""
        
        # Filter signals by confidence and risk
        executable_signals = [
            s for s in signals 
            if s['confidence'] >= self.min_confidence_threshold
        ]
        
        if not executable_signals:
            return
        
        # Execute trades
        for signal in executable_signals[:self.max_open_positions]:  # Limit concurrent trades
            try:
                await self._execute_single_trade(signal)
                
            except Exception as e:
                self.logger.error(f"Error executing trade for {signal['symbol']}: {e}")
    
    async def _execute_single_trade(self, signal: Dict[str, Any]):
        """Execute a single trade"""
        
        try:
            # Create trade request
            if signal['signal_type'] == 'buy':
                order_type = 0  # ORDER_TYPE_BUY
                current_prices = self.mt5_interface.get_current_prices([signal['symbol']])
                price = current_prices.get(signal['symbol'], {}).get('ask', signal['price'])
            else:  # sell
                order_type = 1  # ORDER_TYPE_SELL
                current_prices = self.mt5_interface.get_current_prices([signal['symbol']])
                price = current_prices.get(signal['symbol'], {}).get('bid', signal['price'])
            
            trade_request = TradeRequest(
                action="BUY" if signal['signal_type'] == 'buy' else "SELL",
                symbol=signal['symbol'],
                volume=signal['position_size'],
                price=price,
                sl=signal['stop_loss'],
                tp=signal['take_profit'],
                comment=f"Helios ML {signal['strategy']}"
            )
            
            # Execute trade
            result = self.mt5_interface.place_order(trade_request)
            
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                self.total_trades += 1
                self.successful_trades += 1
                
                self.logger.info(
                    f"Trade executed: {signal['signal_type'].upper()} {signal['symbol']} "
                    f"Volume: {signal['position_size']:.2f} at {price:.5f}"
                )
                
                # Log signal for performance tracking
                self.signals_history.append({
                    'timestamp': signal['timestamp'],
                    'symbol': signal['symbol'],
                    'signal_type': signal['signal_type'],
                    'confidence': signal['confidence'],
                    'strategy': signal['strategy'],
                    'executed': True,
                    'price': price
                })
                
            else:
                self.logger.warning(f"Trade failed for {signal['symbol']}: {result.comment if result else 'Unknown error'}")
                
        except Exception as e:
            self.logger.error(f"Error in _execute_single_trade: {e}")
    
    async def _initialize_ml_models(self):
        """Initialize and load ML models"""
        try:
            model_types = ['ensemble', 'random_forest', 'lightgbm', 'xgboost']
            
            for model_type in model_types:
                try:
                    model = self.model_factory.create_model(model_type, self.config, self.logger)
                    
                    # Try to load existing model
                    model_path = f"models/{model_type}_model.pkl"
                    try:
                        model.load_model(model_path)
                        self.logger.info(f"Loaded existing {model_type} model")
                    except:
                        self.logger.info(f"No existing {model_type} model found")
                    
                    self.ml_models[model_type] = model
                    
                except Exception as e:
                    self.logger.error(f"Failed to initialize {model_type} model: {e}")
            
            self.logger.info(f"Initialized {len(self.ml_models)} ML models")
            
        except Exception as e:
            self.logger.error(f"Error initializing ML models: {e}")
    
    async def _check_model_retraining(self):
        """Check if models need retraining"""
        now = datetime.now()
        
        if (self.last_training_time is None or 
            (now - self.last_training_time).total_seconds() > self.config.ml.retrain_interval_hours * 3600):
            
            self.logger.info("Starting model retraining...")
            await self._retrain_models()
            self.last_training_time = now
    
    async def _retrain_models(self):
        """Retrain ML models with latest data"""
        try:
            # Get training data for each symbol
            for symbol in self.config.data.symbols:
                market_data = self.mt5_interface.get_market_data(symbol, "H1", 1000)
                if market_data is not None:
                    # Process data
                    processed_data = self.data_processor.process_market_data(market_data, symbol)
                    
                    if processed_data is not None and len(processed_data) > 100:
                        # Prepare training data
                        feature_cols = [col for col in processed_data.columns 
                                      if col not in ['open', 'high', 'low', 'close', 'tick_volume', 'symbol', 'timestamp']]
                        
                        X = processed_data[feature_cols].fillna(method='ffill').fillna(0)
                        
                        # Create target (future returns)
                        y = processed_data['close'].shift(-1) / processed_data['close'] - 1
                        
                        # Train each model
                        for model_name, model in self.ml_models.items():
                            try:
                                model.fit(X, y)
                                
                                # Save model
                                model.save_model(f"models/{model_name}_model.pkl")
                                
                                self.logger.info(f"Retrained and saved {model_name} model")
                                
                            except Exception as e:
                                self.logger.error(f"Error retraining {model_name}: {e}")
            
        except Exception as e:
            self.logger.error(f"Error in model retraining: {e}")
    
    def _initialize_strategy_tracking(self):
        """Initialize strategy performance tracking"""
        for strategy_name in self.strategy_manager.strategies.keys():
            self.meta_learning.strategy_performance[strategy_name] = \
                self.meta_learning.StrategyPerformance(name=strategy_name)
    
    def _load_meta_learning_data(self):
        """Load meta-learning data from disk"""
        try:
            self.meta_learning.load_performance_data("logs/meta_learning_performance.json")
        except Exception as e:
            self.logger.warning(f"Could not load meta-learning data: {e}")
    
    async def _update_performance_tracking(self):
        """Update performance tracking and meta-learning"""
        try:
            # Update meta-learning with latest market conditions
            for symbol, data in self.processed_data_cache.items():
                if not data.empty:
                    market_conditions = self.meta_learning.get_market_conditions(data, datetime.now())
                    
                    # This could be expanded to include actual trade outcomes
                    # for performance-based strategy adaptation
            
            # Save meta-learning data periodically
            if datetime.now().minute % 10 == 0:  # Every 10 minutes
                self.meta_learning.save_performance_data("logs/meta_learning_performance.json")
                
        except Exception as e:
            self.logger.error(f"Error updating performance tracking: {e}")
    
    async def _send_status_update(self):
        """Send status update to connected clients"""
        try:
            if hasattr(self.mt5_interface.ws_server, 'broadcast_message'):
                status = {
                    'type': 'status_update',
                    'timestamp': datetime.now().isoformat(),
                    'system_status': 'running' if self.is_running else 'stopped',
                    'total_trades': self.total_trades,
                    'successful_trades': self.successful_trades,
                    'success_rate': self.successful_trades / max(self.total_trades, 1),
                    'daily_pnl': self.daily_pnl,
                    'open_positions': len(self.mt5_interface.get_open_positions()),
                    'strategy_status': self.strategy_manager.get_strategy_status(),
                    'ml_models_loaded': list(self.ml_models.keys()),
                    'market_regime': self.meta_learning.current_regime.value
                }
                
                await self.mt5_interface.ws_server.broadcast_message(status)
                
        except Exception as e:
            self.logger.error(f"Error sending status update: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            'system_running': self.is_running,
            'total_trades': self.total_trades,
            'successful_trades': self.successful_trades,
            'success_rate': self.successful_trades / max(self.total_trades, 1),
            'daily_pnl': self.daily_pnl,
            'open_positions': len(self.mt5_interface.get_open_positions()),
            'ml_models': list(self.ml_models.keys()),
            'strategies': list(self.strategy_manager.strategies.keys()),
            'account_info': self.mt5_interface.get_account_info(),
            'strategy_performance': self.strategy_manager.get_strategy_status(),
            'last_update': datetime.now().isoformat()
        }
    
    async def shutdown(self):
        """Shutdown the trading system gracefully"""
        self.logger.info("Shutting down Helios Trading System...")
        
        await self.stop_trading()
        
        # Save all data
        self.meta_learning.save_performance_data("logs/meta_learning_performance.json")
        
        # Close MT5 connection
        self.mt5_interface.shutdown()
        
        self.logger.info("Helios Trading System shutdown complete")

if __name__ == "__main__":
    # Test the trading system
    import asyncio
    
    async def test_trading_system():
        logging.basicConfig(level=logging.INFO)
        
        system = HeliosTradingSystem()
        
        # Initialize system
        if await system.initialize():
            print("System initialized successfully!")
            print("Starting trading for 10 seconds...")
            
            # Run for 10 seconds to test
            trading_task = asyncio.create_task(system.start_trading())
            
            try:
                await asyncio.sleep(10)
            except KeyboardInterrupt:
                print("Stopping system...")
            finally:
                await system.shutdown()
                trading_task.cancel()
        else:
            print("Failed to initialize system")
    
    # Run the test
    asyncio.run(test_trading_system())