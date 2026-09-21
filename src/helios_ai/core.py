"""
Helios AI Trading System - Core Module
Base classes and data processing for AI components
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.base import BaseEstimator, ClassifierMixin, RegressorMixin
import warnings
import logging

logger = logging.getLogger(__name__)


class AIBaseModel:
    """Base class for all AI models in the Helios system"""
    
    def __init__(self, name: str, use_ai: bool = True):
        """
        Initialize base AI model
        
        Args:
            name: Model name for logging
            use_ai: Whether to use AI or fallback to rules
        """
        self.name = name
        self.use_ai = use_ai
        self.is_trained = False
        self.scaler = StandardScaler()
        
    def prepare_features(self, df: pd.DataFrame) -> np.ndarray:
        """
        Prepare features from OHLCV data
        
        Args:
            df: DataFrame with OHLCV columns
            
        Returns:
            Feature array
        """
        features = []
        
        # Price-based features
        if 'close' in df.columns:
            features.append(df['close'].values)
            features.append(df['open'].values)
            features.append(df['high'].values)
            features.append(df['low'].values)
            
            # Returns
            returns = df['close'].pct_change().fillna(0).values
            features.append(returns)
            
            # Log returns
            log_returns = np.log(df['close'] / df['close'].shift(1)).fillna(0).values
            features.append(log_returns)
        
        # Volume features
        if 'tick_volume' in df.columns:
            features.append(df['tick_volume'].values)
            
            # Volume moving average
            vol_ma = df['tick_volume'].rolling(20).mean().fillna(0).values
            features.append(vol_ma)
            
            # Volume ratio
            vol_ratio = (df['tick_volume'] / vol_ma).fillna(1).values
            features.append(vol_ratio)
        
        # Technical indicators as features
        features = self._add_technical_features(df, features)
        
        return) if features else np np.column_stack(features.array([])
    
    def _add_technical_features(self, df: pd.DataFrame, features: List) -> List:
        """Add technical indicators as features"""
        
        try:
            import pandas_ta as ta
            
            # Trend indicators
            if 'close' in df.columns:
                # EMA
                features.append(df.ta.ema(length=9, close='close', append=True).fillna(0).values)
                features.append(df.ta.ema(length=21, close='close', append=True).fillna(0).values)
                
                # RSI
                features.append(df.ta.rsi(length=14, close='close', append=True).fillna(50).values)
                
                # MACD
                macd = df.ta.macd(fast=12, slow=26, signal=9, close='close', append=True)
                if macd is not None:
                    features.append(pd.DataFrame(macd).iloc[:, 0].fillna(0).values)
                
                # Bollinger Bands
                bbands = df.ta.bbands(length=20, close='close', std=2, append=True)
                if bbands is not None:
                    features.append(pd.DataFrame(bbands).iloc[:, 0].fillna(0).values)
                
                # ATR (Average True Range)
                features.append(df.ta.atr(length=14, high='high', low='low', close='close', append=True).fillna(0).values)
                
        except ImportError:
            # Fallback: manual indicators
            features = self._manual_technical_features(df, features)
        
        return features
    
    def _manual_technical_features(self, df: pd.DataFrame, features: List) -> List:
        """Manual technical features if pandas-ta not available"""
        
        if 'close' not in df.columns:
            return features
        
        # Simple moving averages
        for window in [9, 21, 50]:
            sma = df['close'].rolling(window).mean().fillna(0).values
            features.append(sma)
        
        # RSI (manual calculation)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, 0.0001)
        rsi = 100 - (100 / (1 + rs))
        features.append(rsi.fillna(50).values)
        
        # Volatility
        volatility = df['close'].rolling(20).std().fillna(0).values
        features.append(volatility)
        
        return features
    
    def normalize_data(self, X: np.ndarray) -> np.ndarray:
        """Normalize feature data"""
        try:
            return self.scaler.fit_transform(X)
        except:
            return X
    
    def predict_with_fallback(self, df: pd.DataFrame, rule_based_func, *args, **kwargs):
        """
        Predict with AI, fall back to rule-based if AI fails
        
        Args:
            df: Input data
            rule_based_func: Function to call if AI fails
            *args, **kwargs: Arguments for both AI and rule-based
            
        Returns:
            Prediction result
        """
        if not self.use_ai or not self.is_trained:
            return rule_based_func(*args, **kwargs)
        
        try:
            return self._ai_predict(df)
        except Exception as e:
            logger.warning(f"{self.name} AI failed, using rule-based: {e}")
            return rule_based_func(*args, **kwargs)
    
    def _ai_predict(self, df: pd.DataFrame):
        """Override in subclasses"""
        raise NotImplementedError
    
    def train(self, X: np.ndarray, y: np.ndarray):
        """Train the model - override in subclasses"""
        raise NotImplementedError
    
    def save(self, path: str):
        """Save model - override in subclasses"""
        raise NotImplementedError
    
    def load(self, path: str):
        """Load model - override in subclasses"""
        raise NotImplementedError


class FeatureEngineer:
    """
    Feature engineering for AI models
    Creates advanced features from raw OHLCV data
    """
    
    @staticmethod
    def create_all_features(df: pd.DataFrame) -> pd.DataFrame:
        """
        Create comprehensive feature set
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with added features
        """
        result = df.copy()
        
        # Price features
        result['return'] = df['close'].pct_change()
        result['log_return'] = np.log(df['close'] / df['close'].shift(1))
        
        # Moving averages
        for window in [5, 9, 13, 21, 34, 55, 89]:
            result[f'sma_{window}'] = df['close'].rolling(window).mean()
            result[f'ema_{window}'] = df['close'].ewm(span=window, adjust=False).mean()
        
        # MA crossovers
        result['sma_9_21_cross'] = (result['sma_9'] > result['sma_21']).astype(int)
        result['sma_21_55_cross'] = (result['sma_21'] > result['sma_55']).astype(int)
        
        # Volatility
        result['volatility_10'] = df['close'].rolling(10).std()
        result['volatility_20'] = df['close'].rolling(20).std()
        result['volatility_ratio'] = result['volatility_10'] / result['volatility_20'].replace(0, 1)
        
        # Momentum
        for period in [5, 10, 20]:
            result[f'momentum_{period}'] = df['close'] - df['close'].shift(period)
            result[f'roc_{period}'] = (df['close'] - df['close'].shift(period)) / df['close'].shift(period)
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, 0.0001)
        result['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        result['macd'] = ema12 - ema26
        result['macd_signal'] = result['macd'].ewm(span=9, adjust=False).mean()
        result['macd_hist'] = result['macd'] - result['macd_signal']
        
        # Bollinger Bands
        sma20 = df['close'].rolling(20).mean()
        std20 = df['close'].rolling(20).std()
        result['bb_upper'] = sma20 + (std20 * 2)
        result['bb_lower'] = sma20 - (std20 * 2)
        result['bb_width'] = (result['bb_upper'] - result['bb_lower']) / sma20
        result['bb_position'] = (df['close'] - result['bb_lower']) / (result['bb_upper'] - result['bb_lower']).replace(0, 1)
        
        # Volume features
        if 'tick_volume' in df.columns:
            result['volume_ma'] = df['tick_volume'].rolling(20).mean()
            result['volume_ratio'] = df['tick_volume'] / result['volume_ma'].replace(0, 1)
            
            # OBV (On Balance Volume)
            result['obv'] = (np.sign(df['close'].diff()) * df['tick_volume']).fillna(0).cumsum()
        
        # Price position features
        result['high_low_ratio'] = (df['close'] - df['low']) / (df['high'] - df['low']).replace(0, 1)
        result['close_open_ratio'] = (df['close'] - df['open']) / (df['high'] - df['low']).replace(0, 1)
        
        # Fill NaN
        result = result.fillna(0)
        
        # Replace inf
        result = result.replace([np.inf, -np.inf], 0)
        
        return result
    
    @staticmethod
    def create_sequence_data(df: pd.DataFrame, sequence_length: int = 10) -> Tuple[np.ndarray, np.ndarray]:
        """
        Create sequences for LSTM/RNN models
        
        Args:
            df: DataFrame with features
            sequence_length: Number of time steps per sequence
            
        Returns:
            X, y arrays
        """
        features = ['open', 'high', 'low', 'close']
        if 'tick_volume' in df.columns:
            features.append('tick_volume')
        
        data = df[features].values
        
        X, y = [], []
        for i in range(sequence_length, len(data)):
            X.append(data[i-sequence_length:i])
            # Next candle direction
            y.append(1 if df['close'].iloc[i] > df['close'].iloc[i-1] else 0)
        
        return np.array(X), np.array(y)
    
    @staticmethod
    def create_labeled_data(df: pd.DataFrame, look_forward: int = 5, threshold: float = 0.005) -> Tuple[np.ndarray, np.ndarray]:
        """
        Create labeled data for classification
        
        Args:
            df: DataFrame with features
            look_forward: Bars to look forward for target
            threshold: Threshold for label (e.g., 0.5% = 0.005)
            
        Returns:
            X, y arrays
        """
        features_df = FeatureEngineer.create_all_features(df)
        
        # Remove non-feature columns
        drop_cols = ['time', 'open', 'high', 'low', 'close', 'tick_volume']
        feature_cols = [c for c in features_df.columns if c not in drop_cols]
        
        X = features_df[feature_cols].values[:-look_forward]
        
        # Create labels
        future_returns = df['close'].pct_change(look_forward).shift(-look_forward)
        y = np.where(future_returns > threshold, 1,  # Long
               np.where(future_returns < -threshold, -1,  # Short
               0))  # Neutral
        
        y = y[:-look_forward]
        
        return X, y


class ModelStore:
    """
    Model storage and versioning
    """
    
    def __init__(self, model_dir: str = "models"):
        import os
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)
    
    def save_model(self, model, name: str, version: str = "v1"):
        """Save model to disk"""
        import joblib
        import os
        
        filename = os.path.join(self.model_dir, f"{name}_{version}.pkl")
        joblib.dump(model, filename)
        logger.info(f"Model saved: {filename}")
        return filename
    
    def load_model(self, name: str, version: str = "v1"):
        """Load model from disk"""
        import joblib
        import os
        
        filename = os.path.join(self.model_dir, f"{name}_{version}.pkl")
        if os.path.exists(filename):
            model = joblib.load(filename)
            logger.info(f"Model loaded: {filename}")
            return model
        else:
            logger.warning(f"Model not found: {filename}")
            return None
    
    def list_models(self):
        """List all saved models"""
        import os
        return [f for f in os.listdir(self.model_dir) if f.endswith('.pkl')]


def create_ai_pipeline(config: dict = None) -> Dict:
    """
    Factory function to create full AI pipeline
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Dictionary of AI components
    """
    from .modules import (
        StructureAI, FVGAI, OBValidationAI,
        PatternRecognitionAI, DynamicLevelsAI,
        RegimeDetectionAI, RiskManagementAI
    )
    
    config = config or {}
    use_ai = config.get('use_ai', True)
    
    return {
        'structure': StructureAI(use_ai=use_ai),
        'fvg': FVGAI(use_ai=use_ai),
        'order_block': OBValidationAI(use_ai=use_ai),
        'pattern': PatternRecognitionAI(use_ai=use_ai),
        'levels': DynamicLevelsAI(use_ai=use_ai),
        'regime': RegimeDetectionAI(use_ai=use_ai),
        'risk': RiskManagementAI(use_ai=use_ai)
    }
