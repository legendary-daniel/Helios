"""
Helios ML Trading System - Configuration Module
Comprehensive configuration for the Python-MT5 integrated trading system
"""

import os
import json
from typing import Dict, List, Any
from dataclasses import dataclass, asdict
import logging

@dataclass
class MT5Config:
    """MetaTrader 5 configuration settings"""
    login: int = 0
    password: str = ""
    server: str = ""
    timeout: int = 60000
    portable: bool = False
    path: str = ""
    
@dataclass
class DataConfig:
    """Market data configuration"""
    symbols: List[str] = None
    timeframes: List[str] = None
    lookback_days: int = 365
    real_time_update_interval: float = 1.0  # seconds
    historical_data_path: str = "data/historical"
    tick_data_enabled: bool = False
    
@dataclass
class MLConfig:
    """Machine learning model configuration"""
    feature_window: int = 50
    prediction_window: int = 10
    model_type: str = "ensemble"  # lstm, random_forest, ensemble
    retrain_interval_hours: int = 6
    confidence_threshold: float = 0.7
    models_path: str = "models"
    ensemble_weights_path: str = "models/ensemble_weights.json"
    
@dataclass
class StrategyConfig:
    """Trading strategy configuration"""
    strategies: List[Dict[str, Any]] = None
    default_strategy: str = "trend_following"
    max_concurrent_strategies: int = 3
    strategy_rotation_enabled: bool = True
    min_strategy_performance: float = 0.05  # 5% minimum return
    
@dataclass
class RiskConfig:
    """Risk management configuration"""
    max_risk_per_trade: float = 0.02  # 2% max risk per trade
    max_daily_loss: float = 0.05      # 5% max daily loss
    max_portfolio_risk: float = 0.10  # 10% max portfolio risk
    max_open_positions: int = 5
    position_sizing_method: str = "kelly"  # fixed, kelly, volatility
    stop_loss_atr_multiplier: float = 2.0
    take_profit_ratio: float = 2.0
    
@dataclass
class MetaLearningConfig:
    """Meta-learning configuration"""
    market_regime_detection: bool = True
    volatility_analysis: bool = True
    time_based_regimes: bool = True
    strategy_performance_tracking: bool = True
    adaptation_interval_hours: int = 4
    regime_lookback_periods: int = 20
    
@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: str = "logs/helios_trading.log"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    console_output: bool = True
    
class ConfigManager:
    """Configuration manager for the trading system"""
    
    def __init__(self, config_path: str = "config/config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        
        # Initialize all configurations
        self.mt5 = MT5Config(**self.config.get('mt5', {}))
        self.data = DataConfig(**self.config.get('data', {}))
        self.ml = MLConfig(**self.config.get('ml', {}))
        self.strategy = StrategyConfig(**self.config.get('strategy', {}))
        self.risk = RiskConfig(**self.config.get('risk', {}))
        self.meta_learning = MetaLearningConfig(**self.config.get('meta_learning', {}))
        self.logging = LoggingConfig(**self.config.get('logging', {}))
        
        # Set default values if not provided
        self._set_defaults()
    
    def _set_defaults(self):
        """Set default configuration values"""
        if not self.data.symbols:
            self.data.symbols = [
                "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", 
                "USDCHF", "USDCAD", "NZDUSD", "EURJPY",
                "BTCUSD", "XAUUSD"
            ]
        
        if not self.data.timeframes:
            self.data.timeframes = [
                "M1", "M5", "M15", "M30", "H1", "H4", "D1"
            ]
        
        if not self.strategy.strategies:
            self.strategy.strategies = [
                {
                    "name": "trend_following",
                    "enabled": True,
                    "priority": 1,
                    "parameters": {
                        "fast_ema": 12,
                        "slow_ema": 26,
                        "rsi_period": 14,
                        "rsi_oversold": 30,
                        "rsi_overbought": 70
                    }
                },
                {
                    "name": "mean_reversion",
                    "enabled": True,
                    "priority": 2,
                    "parameters": {
                        "bb_period": 20,
                        "bb_std": 2,
                        "rsi_period": 14,
                        "rsi_oversold": 25,
                        "rsi_overbought": 75
                    }
                },
                {
                    "name": "breakout",
                    "enabled": True,
                    "priority": 3,
                    "parameters": {
                        "breakout_period": 20,
                        "volume_threshold": 1.5,
                        "price_momentum": 0.01
                    }
                },
                {
                    "name": "scalping",
                    "enabled": True,
                    "priority": 4,
                    "parameters": {
                        "tick_threshold": 5,
                        "time_limit_seconds": 300,
                        "profit_target": 0.001
                    }
                }
            ]
    
    def _load_config(self) -> Dict:
        """Load configuration from file or create default"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logging.warning(f"Failed to load config: {e}. Using defaults.")
        
        # Create default configuration
        default_config = {
            "mt5": {
                "timeout": 60000,
                "portable": False
            },
            "data": {
                "lookback_days": 365,
                "real_time_update_interval": 1.0,
                "tick_data_enabled": False
            },
            "ml": {
                "feature_window": 50,
                "prediction_window": 10,
                "model_type": "ensemble",
                "retrain_interval_hours": 6,
                "confidence_threshold": 0.7
            },
            "strategy": {
                "default_strategy": "trend_following",
                "max_concurrent_strategies": 3,
                "strategy_rotation_enabled": True,
                "min_strategy_performance": 0.05
            },
            "risk": {
                "max_risk_per_trade": 0.02,
                "max_daily_loss": 0.05,
                "max_portfolio_risk": 0.10,
                "max_open_positions": 5,
                "position_sizing_method": "kelly"
            },
            "meta_learning": {
                "market_regime_detection": True,
                "volatility_analysis": True,
                "time_based_regimes": True,
                "strategy_performance_tracking": True,
                "adaptation_interval_hours": 4
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "file_path": "logs/helios_trading.log",
                "max_file_size": 10485760,
                "backup_count": 5,
                "console_output": True
            }
        }
        
        # Save default configuration
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(default_config, f, indent=2)
        
        return default_config
    
    def save_config(self):
        """Save current configuration to file"""
        config_dict = {
            "mt5": asdict(self.mt5),
            "data": asdict(self.data),
            "ml": asdict(self.ml),
            "strategy": asdict(self.strategy),
            "risk": asdict(self.risk),
            "meta_learning": asdict(self.meta_learning),
            "logging": asdict(self.logging)
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(config_dict, f, indent=2)
    
    def get_config_summary(self) -> str:
        """Get a summary of the current configuration"""
        summary = f"""
Helios ML Trading System Configuration Summary:

MT5 Connection:
  - Server: {self.mt5.server}
  - Timeout: {self.mt5.timeout}ms

Market Data:
  - Symbols: {len(self.data.symbols)} pairs
  - Timeframes: {len(self.data.timeframes)} timeframes
  - Lookback: {self.data.lookback_days} days

ML Configuration:
  - Model Type: {self.ml.model_type}
  - Feature Window: {self.ml.feature_window}
  - Confidence Threshold: {self.ml.confidence_threshold}

Strategies:
  - Default: {self.strategy.default_strategy}
  - Total Strategies: {len(self.strategy.strategies)}

Risk Management:
  - Max Risk/Trade: {self.risk.max_risk_per_trade*100}%
  - Max Daily Loss: {self.risk.max_daily_loss*100}%
  - Max Positions: {self.risk.max_open_positions}

Meta-Learning:
  - Adaptation Interval: {self.meta_learning.adaptation_interval_hours} hours
  - Market Regime Detection: {self.meta_learning.market_regime_detection}
"""
        return summary

# Global configuration instance
config = ConfigManager()

if __name__ == "__main__":
    print(config.get_config_summary())