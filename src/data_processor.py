"""
Helios ML Trading System - Data Processing Module
Advanced market data processing and feature engineering
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional, Union
import ta
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.decomposition import PCA
from sklearn.feature_selection import SelectKBest, f_regression
import logging
import warnings
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

warnings.filterwarnings('ignore')

class DataProcessor:
    """Advanced market data processor with feature engineering"""
    
    def __init__(self, config, logger=None):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.scalers = {}
        self.feature_importance = {}
        
    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate comprehensive technical indicators"""
        df = df.copy()
        
        # Price-based indicators
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        df['price_range'] = (df['high'] - df['low']) / df['close']
        df['upper_shadow'] = (df['high'] - np.maximum(df['open'], df['close'])) / df['close']
        df['lower_shadow'] = (np.minimum(df['open'], df['close']) - df['low']) / df['close']
        df['body_size'] = abs(df['close'] - df['open']) / df['close']
        
        # Moving averages
        df['sma_10'] = ta.trend.sma_indicator(df['close'], window=10)
        df['sma_20'] = ta.trend.sma_indicator(df['close'], window=20)
        df['sma_50'] = ta.trend.sma_indicator(df['close'], window=50)
        df['ema_12'] = ta.trend.ema_indicator(df['close'], window=12)
        df['ema_26'] = ta.trend.ema_indicator(df['close'], window=26)
        df['wma_20'] = ta.trend.wma_indicator(df['close'], window=20)
        
        # MA relationships
        df['ma_ratio_short'] = df['sma_10'] / df['sma_20']
        df['ma_ratio_long'] = df['sma_20'] / df['sma_50']
        df['price_above_sma20'] = (df['close'] > df['sma_20']).astype(int)
        df['price_above_sma50'] = (df['close'] > df['sma_50']).astype(int)
        
        # MACD
        macd = ta.trend.MACD(df['close'])
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_histogram'] = macd.macd_diff()
        
        # RSI
        rsi = ta.momentum.RSIIndicator(df['close'], window=14)
        df['rsi'] = rsi.rsi()
        df['rsi_sma'] = ta.trend.sma_indicator(df['rsi'], window=10)
        df['rsi_overbought'] = (df['rsi'] > 70).astype(int)
        df['rsi_oversold'] = (df['rsi'] < 30).astype(int)
        
        # Bollinger Bands
        bb = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
        df['bb_upper'] = bb.bollinger_hband()
        df['bb_lower'] = bb.bollinger_lband()
        df['bb_middle'] = bb.bollinger_mavg()
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # Stochastic
        stoch = ta.momentum.StochasticOscillator(df['high'], df['low'], df['close'])
        df['stoch_k'] = stoch.stoch()
        df['stoch_d'] = stoch.stoch_signal()
        
        # Williams %R
        williams = ta.momentum.WilliamsRIndicator(df['high'], df['low'], df['close'])
        df['williams_r'] = williams.williams_r()
        
        # Average True Range (ATR)
        atr = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close'])
        df['atr'] = atr.average_true_range()
        df['atr_ratio'] = df['atr'] / df['close']
        
        # Commodity Channel Index (CCI)
        cci = ta.trend.CCIIndicator(df['high'], df['low'], df['close'])
        df['cci'] = cci.cci()
        
        # Money Flow Index (MFI)
        mfi = ta.volume.MFIIndicator(df['high'], df['low'], df['close'], df['tick_volume'])
        df['mfi'] = mfi.money_flow_index()
        
        # Volume indicators
        if 'tick_volume' in df.columns:
            df['volume_sma'] = ta.trend.sma_indicator(df['tick_volume'], window=20)
            df['volume_ratio'] = df['tick_volume'] / df['volume_sma']
            df['vwap'] = (df['close'] * df['tick_volume']).cumsum() / df['tick_volume'].cumsum()
        
        # Momentum indicators
        df['roc'] = ta.momentum.ROCIndicator(df['close'], window=12).roc()
        df['stoch_roc'] = ta.momentum.ROCIIndicator(df['close'], window=14).roci()
        
        # Trend strength
        df['adx'] = ta.trend.ADXIndicator(df['high'], df['low'], df['close']).adx()
        df['di_plus'] = ta.trend.ADXIndicator(df['high'], df['low'], df['close']).adx_pos()
        df['di_minus'] = ta.trend.ADXIndicator(df['high'], df['low'], df['close']).adx_neg()
        
        # Parabolic SAR
        psar = ta.trend.PSARIndicator(df['high'], df['low'], df['close'])
        df['psar'] = psar.psar()
        df['psar_up'] = psar.psar_up().astype(int)
        df['psar_down'] = psar.psar_down().astype(int)
        
        # Ichimoku
        try:
            ichimoku = ta.trend.IchimokuIndicator(df['high'], df['low'], df['close'])
            df['ichimoku_conversion'] = ichimoku.ichimoku_conversion_line()
            df['ichimoku_base'] = ichimoku.ichimoku_base_line()
            df['ichimoku_a'] = ichimoku.ichimoku_a()
            df['ichimoku_b'] = ichimoku.ichimoku_b()
            df['ichimoku_above_cloud'] = (df['close'] > df['ichimoku_a']) & (df['close'] > df['ichimoku_b'])
        except:
            # If Ichimoku fails, continue without it
            pass
        
        return df
    
    def calculate_multi_timeframe_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate features across multiple timeframes"""
        features_df = pd.DataFrame()
        
        timeframes = {
            'M1': 1, 'M5': 5, 'M15': 15, 'M30': 30,
            'H1': 60, 'H4': 240, 'D1': 1440
        }
        
        for tf_name, tf_minutes in timeframes.items():
            # Resample to timeframe
            if tf_minutes > 1:
                resampled = df.resample(f'{tf_minutes}T').agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'tick_volume': 'sum'
                }).dropna()
            else:
                resampled = df.copy()
            
            if len(resampled) > 20:  # Ensure sufficient data
                # Calculate features for this timeframe
                features = self.calculate_technical_indicators(resampled)
                
                # Add timeframe suffix
                feature_cols = [col for col in features.columns if col not in ['open', 'high', 'low', 'close', 'tick_volume']]
                for col in feature_cols:
                    features[f'{col}_{tf_name}'] = features[col]
                
                # Keep only essential columns for merging
                timeframe_df = features[['close', 'high', 'low', 'open'] + 
                                      [f'{col}_{tf_name}' for col in feature_cols]].copy()
                
                if features_df.empty:
                    features_df = timeframe_df.copy()
                else:
                    features_df = features_df.join(timeframe_df, rsuffix=f'_{tf_name}')
        
        return features_df.dropna()
    
    def calculate_pattern_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate pattern-based features"""
        df = df.copy()
        
        # Candlestick patterns
        df['doji'] = (abs(df['close'] - df['open']) / (df['high'] - df['low']) < 0.1).astype(int)
        df['hammer'] = ((df['close'] > df['open']) & 
                       ((df['open'] - df['low']) / (0.001 + df['high'] - df['low']) > 0.6) &
                       ((df['high'] - df['close']) / (0.001 + df['high'] - df['low']) < 0.4)).astype(int)
        df['shooting_star'] = ((df['close'] < df['open']) & 
                              ((df['high'] - df['open']) / (0.001 + df['high'] - df['low']) > 0.6) &
                              ((df['close'] - df['low']) / (0.001 + df['high'] - df['low']) < 0.4)).astype(int)
        
        # Support and resistance levels
        df['support_level'] = df['low'].rolling(window=20).min()
        df['resistance_level'] = df['high'].rolling(window=20).max()
        df['price_distance_support'] = (df['close'] - df['support_level']) / df['close']
        df['price_distance_resistance'] = (df['resistance_level'] - df['close']) / df['close']
        
        # Fractal patterns
        df['fractal_high'] = ((df['high'] > df['high'].shift(1)) & 
                             (df['high'] > df['high'].shift(-1))).astype(int)
        df['fractal_low'] = ((df['low'] < df['low'].shift(1)) & 
                            (df['low'] < df['low'].shift(-1))).astype(int)
        
        return df
    
    def calculate_volatility_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate volatility-based features"""
        df = df.copy()
        
        # Historical volatility
        df['hv_5'] = df['returns'].rolling(window=5).std() * np.sqrt(252)
        df['hv_20'] = df['returns'].rolling(window=20).std() * np.sqrt(252)
        df['hv_50'] = df['returns'].rolling(window=50).std() * np.sqrt(252)
        
        # GARCH-like features
        df['volatility_clustering'] = (df['returns'].abs() > df['returns'].rolling(window=10).std()).astype(int)
        
        # Parkinson volatility estimator
        df['parkinson_vol'] = np.sqrt((1/(4*np.log(2))) * 
                                     (np.log(df['high']/df['low']))**2)
        
        # Garman-Klass volatility estimator
        df['gk_vol'] = np.sqrt((0.5 * (np.log(df['high']/df['low']))**2 - 
                               (2*np.log(2)-1) * (np.log(df['close']/df['open']))**2))
        
        return df
    
    def calculate_sentiment_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate market sentiment features"""
        df = df.copy()
        
        # Fear & Greed style indicators
        df['momentum'] = df['close'] / df['close'].shift(10) - 1
        df['momentum_sma'] = df['momentum'].rolling(window=10).mean()
        df['momentum_ratio'] = df['momentum'] / (df['momentum_sma'] + 1e-8)
        
        # Market structure
        df['higher_high'] = (df['high'] > df['high'].shift(1)).astype(int)
        df['lower_low'] = (df['low'] < df['low'].shift(1)).astype(int)
        df['trend_strength'] = np.where(df['higher_high'] & ~df['lower_low'], 1,
                                      np.where(df['lower_low'] & ~df['higher_high'], -1, 0))
        
        return df
    
    def select_features(self, df: pd.DataFrame, target_col: str, 
                       method: str = 'k_best', k: int = 50) -> Tuple[pd.DataFrame, List[str]]:
        """Feature selection using various methods"""
        
        # Separate features and target
        feature_cols = [col for col in df.columns if col != target_col]
        X = df[feature_cols].fillna(method='ffill').fillna(method='bfill')
        y = df[target_col].fillna(method='ffill').fillna(method='bfill')
        
        # Remove infinite values
        X = X.replace([np.inf, -np.inf], np.nan).fillna(0)
        
        if method == 'k_best':
            # Statistical feature selection
            selector = SelectKBest(score_func=f_regression, k=k)
            X_selected = selector.fit_transform(X, y)
            selected_features = [feature_cols[i] for i in selector.get_support(indices=True)]
            
        elif method == 'pca':
            # PCA dimensionality reduction
            pca = PCA(n_components=k)
            X_selected = pca.fit_transform(X)
            selected_features = [f'PC_{i+1}' for i in range(k)]
            
        elif method == 'correlation':
            # Correlation-based selection
            correlations = X.corrwith(y).abs().sort_values(ascending=False)
            selected_features = correlations.head(k).index.tolist()
            X_selected = X[selected_features]
            
        else:
            # Return all features if method not recognized
            selected_features = feature_cols
            X_selected = X
        
        return X_selected, selected_features
    
    def normalize_features(self, df: pd.DataFrame, fit: bool = True) -> pd.DataFrame:
        """Normalize features using robust scaling"""
        df_norm = df.copy()
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        for col in numeric_cols:
            if fit:
                self.scalers[col] = RobustScaler()
                df_norm[col] = self.scalers[col].fit_transform(df[col].values.reshape(-1, 1)).flatten()
            else:
                if col in self.scalers:
                    df_norm[col] = self.scalers[col].transform(df[col].values.reshape(-1, 1)).flatten()
        
        return df_norm
    
    def create_sequences(self, df: pd.DataFrame, target_col: str, 
                        sequence_length: int, prediction_horizon: int = 1) -> Tuple[np.ndarray, np.ndarray]:
        """Create sequences for LSTM models"""
        data = df.copy()
        features = [col for col in data.columns if col != target_col]
        
        # Prepare data
        feature_data = data[features].fillna(method='ffill').fillna(0).values
        target_data = data[target_col].fillna(method='ffill').fillna(0).values
        
        # Create sequences
        X, y = [], []
        for i in range(sequence_length, len(feature_data) - prediction_horizon + 1):
            X.append(feature_data[i-sequence_length:i])
            y.append(target_data[i:i+prediction_horizon])
        
        return np.array(X), np.array(y)
    
    def process_market_data(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Complete market data processing pipeline"""
        self.logger.info(f"Processing market data for {symbol}")
        
        # Ensure required columns
        required_cols = ['open', 'high', 'low', 'close', 'tick_volume']
        if not all(col in df.columns for col in required_cols):
            raise ValueError(f"Missing required columns: {required_cols}")
        
        # Sort by timestamp
        df = df.sort_index()
        
        # Calculate all features
        df = self.calculate_technical_indicators(df)
        df = self.calculate_pattern_features(df)
        df = self.calculate_volatility_features(df)
        df = self.calculate_sentiment_features(df)
        
        # Calculate multi-timeframe features
        df = self.calculate_multi_timeframe_features(df)
        
        # Add symbol identifier
        df['symbol'] = symbol
        df['timestamp'] = df.index
        
        # Remove rows with all NaN values
        df = df.dropna(how='all')
        
        # Log feature count
        feature_count = len([col for col in df.columns if col not in ['open', 'high', 'low', 'close', 'tick_volume', 'symbol', 'timestamp']])
        self.logger.info(f"Generated {feature_count} features for {symbol}")
        
        return df

if __name__ == "__main__":
    # Test the data processor
    import logging
    logging.basicConfig(level=logging.INFO)
    
    from config.config import config
    
    # Create sample data
    dates = pd.date_range(start='2023-01-01', periods=1000, freq='1min')
    np.random.seed(42)
    
    sample_data = pd.DataFrame({
        'open': 1.1000 + np.cumsum(np.random.randn(1000) * 0.001),
        'high': 1.1000 + np.cumsum(np.random.randn(1000) * 0.001) + np.abs(np.random.randn(1000) * 0.0005),
        'low': 1.1000 + np.cumsum(np.random.randn(1000) * 0.001) - np.abs(np.random.randn(1000) * 0.0005),
        'close': 1.1000 + np.cumsum(np.random.randn(1000) * 0.001),
        'tick_volume': np.random.randint(100, 1000, 1000)
    }, index=dates)
    
    # Ensure high > low and high > open/close, low < open/close
    sample_data['high'] = np.maximum(sample_data['high'], 
                                   np.maximum(sample_data['open'], sample_data['close']))
    sample_data['low'] = np.minimum(sample_data['low'], 
                                  np.minimum(sample_data['open'], sample_data['close']))
    
    processor = DataProcessor(config)
    processed_data = processor.process_market_data(sample_data, "EURUSD")
    
    print(f"Original data shape: {sample_data.shape}")
    print(f"Processed data shape: {processed_data.shape}")
    print(f"Generated features: {processed_data.shape[1] - 6}")  # Subtract price + volume + symbol + timestamp
    print("\nFirst 5 rows of processed data:")
    print(processed_data.head())