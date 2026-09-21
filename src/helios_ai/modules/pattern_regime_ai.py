"""
Helios AI - Pattern Recognition & Regime Detection
AI-powered candlestick pattern recognition and market regime classification
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.cluster import KMeans, DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.mixture import GaussianMixture
import joblib
import logging

logger = logging.getLogger(__name__)


class PatternRecognitionAI:
    """
    AI-enhanced candlestick pattern recognition
    Uses sequence analysis for pattern detection
    """
    
    def __init__(self, use_ai: bool = True, model_path: str = None):
        """
        Initialize Pattern AI
        
        Args:
            use_ai: Whether to use AI
            model_path: Model path
        """
        self.use_ai = use_ai
        self.model = None
        self.scaler = StandardScaler()
        self.is_trained = False
        
        if model_path:
            try:
                self.model = joblib.load(model_path)
                self.is_trained = True
            except:
                pass
        
        if not self.model and self.use_ai:
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
        
        # Pattern definitions
        self.patterns = {
            'hammer': self._detect_hammer,
            'shooting_star': self._detect_shooting_star,
            'bullish_engulfing': self._detect_bullish_engulfing,
            'bearish_engulfing': self._detect_bearish_engulfing,
            'morning_star': self._detect_morning_star,
            'evening_star': self._detect_evening_star,
            'doji': self._detect_doji,
            'three_white_soldiers': self._detect_three_white_soldiers,
            'three_black_crows': self._detect_three_black_crows
        }
    
    def prepare_sequence(self, df: pd.DataFrame, index: int, sequence_length: int = 10) -> np.ndarray:
        """
        Prepare candle sequence for pattern recognition
        
        Args:
            df: OHLCV data
            index: Current index
            sequence_length: Number of candles in sequence
            
        Returns:
            Feature array
        """
        if index < sequence_length:
            return None
        
        sequence = df.iloc[index-sequence_length:index]
        
        features = []
        
        # Normalize prices
        base_price = sequence['close'].iloc[0]
        
        for _, row in sequence.iterrows():
            # Normalized OHLC
            features.append((row['open'] - base_price) / base_price)
            features.append((row['high'] - base_price) / base_price)
            features.append((row['low'] - base_price) / base_price)
            features.append((row['close'] - base_price) / base_price)
            
            # Body and wick ratios
            body = abs(row['close'] - row['open'])
            total_range = row['high'] - row['low'] + 0.0001
            upper_wick = row['high'] - max(row['close'], row['open'])
            lower_wick = min(row['close'], row['open']) - row['low']
            
            features.append(body / total_range)
            features.append(upper_wick / total_range)
            features.append(lower_wick / total_range)
            
            # Is bullish
            features.append(1 if row['close'] > row['open'] else 0)
        
        # Add volume features if available
        if 'tick_volume' in df.columns:
            vol_ma = sequence['tick_volume'].mean()
            for _, row in sequence.iterrows():
                features.append(row['tick_volume'] / vol_ma if vol_ma > 0 else 1)
        
        return np.array(features).reshape(1, -1)
    
    def _detect_hammer(self, df: pd.DataFrame, index: int) -> Tuple[bool, float]:
        """Detect hammer pattern"""
        if index < 1:
            return False, 0.0
        
        open_p = df['open'].iloc[index]
        close = df['close'].iloc[index]
        high = df['high'].iloc[index]
        low = df['low'].iloc[index]
        
        body = abs(close - open_p)
        upper_wick = high - max(close, open_p)
        lower_wick = min(close, open_p) - low
        total_range = high - low + 0.0001
        
        # Hammer: small body at top, long lower wick
        if body / total_range < 0.3 and lower_wick / total_range > 0.6 and upper_wick / total_range < 0.1:
            return True, lower_wick / total_range
        
        return False, 0.0
    
    def _detect_shooting_star(self, df: pd.DataFrame, index: int) -> Tuple[bool, float]:
        """Detect shooting star pattern"""
        if index < 1:
            return False, 0.0
        
        open_p = df['open'].iloc[index]
        close = df['close'].iloc[index]
        high = df['high'].iloc[index]
        low = df['low'].iloc[index]
        
        body = abs(close - open_p)
        upper_wick = high - max(close, open_p)
        lower_wick = min(close, open_p) - low
        total_range = high - low + 0.0001
        
        # Shooting star: small body at bottom, long upper wick
        if body / total_range < 0.3 and upper_wick / total_range > 0.6 and lower_wick / total_range < 0.1:
            return True, upper_wick / total_range
        
        return False, 0.0
    
    def _detect_bullish_engulfing(self, df: pd.DataFrame, index: int) -> Tuple[bool, float]:
        """Detect bullish engulfing"""
        if index < 1:
            return False, 0.0
        
        prev_open = df['open'].iloc[index-1]
        prev_close = df['close'].iloc[index-1]
        curr_open = df['open'].iloc[index]
        curr_close = df['close'].iloc[index]
        
        # Previous bearish, current bullish, current engulfs previous
        if (prev_close < prev_open and 
            curr_close > curr_open and 
            curr_open < prev_close and 
            curr_close > prev_open):
            return True, 0.8
        
        return False, 0.0
    
    def _detect_bearish_engulfing(self, df: pd.DataFrame, index: int) -> Tuple[bool, float]:
        """Detect bearish engulfing"""
        if index < 1:
            return False, 0.0
        
        prev_open = df['open'].iloc[index-1]
        prev_close = df['close'].iloc[index-1]
        curr_open = df['open'].iloc[index]
        curr_close = df['close'].iloc[index]
        
        if (prev_close > prev_open and 
            curr_close < curr_open and 
            curr_open > prev_close and 
            curr_close < prev_open):
            return True, 0.8
        
        return False, 0.0
    
    def _detect_morning_star(self, df: pd.DataFrame, index: int) -> Tuple[bool, float]:
        """Detect morning star (3-candle bullish reversal)"""
        if index < 2:
            return False, 0.0
        
        # Candle -2: Bearish
        c1_open = df['open'].iloc[index-2]
        c1_close = df['close'].iloc[index-2]
        
        # Candle -1: Small body
        c2_open = df['open'].iloc[index-1]
        c2_close = df['close'].iloc[index-1]
        c2_body = abs(c2_close - c2_open)
        c2_range = df['high'].iloc[index-1] - df['low'].iloc[index-1] + 0.0001
        
        # Candle -0: Bullish
        c3_open = df['open'].iloc[index]
        c3_close = df['close'].iloc[index]
        
        if (c1_close < c1_open and  # Bear c2_body / c2_range ish first
           < 0.3 and  # Small middle
            c3_close > c3_open and  # Bullish third
            c3_close > (c1_open + c1_close) / 2):  # Above midpoint
            return True, 0.7
        
        return False, 0.0
    
    def _detect_evening_star(self, df: pd.DataFrame, index: int) -> Tuple[bool, float]:
        """Detect evening star (3-candle bearish reversal)"""
        if index < 2:
            return False, 0.0
        
        c1_open = df['open'].iloc[index-2]
        c1_close = df['close'].iloc[index-2]
        
        c2_open = df['open'].iloc[index-1]
        c2_close = df['close'].iloc[index-1]
        c2_body = abs(c2_close - c2_open)
        c2_range = df['high'].iloc[index-1] - df['low'].iloc[index-1] + 0.0001
        
        c3_open = df['open'].iloc[index]
        c3_close = df['close'].iloc[index]
        
        if (c1_close > c1_open and
            c2_body / c2_range < 0.3 and
            c3_close < c3_open and
            c3_close < (c1_open + c1_close) / 2):
            return True, 0.7
        
        return False, 0.0
    
    def _detect_doji(self, df: pd.DataFrame, index: int) -> Tuple[bool, float]:
        """Detect doji"""
        open_p = df['open'].iloc[index]
        close = df['close'].iloc[index]
        high = df['high'].iloc[index]
        low = df['low'].iloc[index]
        
        body = abs(close - open_p)
        total_range = high - low + 0.0001
        
        if body / total_range < 0.1:
            return True, 0.6
        
        return False, 0.0
    
    def _detect_three_white_soldiers(self, df: pd.DataFrame, index: int) -> Tuple[bool, float]:
        """Detect three white soldiers"""
        if index < 2:
            return False, 0.0
        
        # Check 3 consecutive bullish candles with higher closes
        for offset in range(3):
            i = index - offset
            if df['close'].iloc[i] <= df['open'].iloc[i]:
                return False, 0.0
            if offset > 0:
                if df['close'].iloc[i] <= df['close'].iloc[i+1]:
                    return False, 0.0
        
        return True, 0.8
    
    def _detect_three_black_crows(self, df: pd.DataFrame, index: int) -> Tuple[bool, float]:
        """Detect three black crows"""
        if index < 2:
            return False, 0.0
        
        for offset in range(3):
            i = index - offset
            if df['close'].iloc[i] >= df['open'].iloc[i]:
                return False, 0.0
            if offset > 0:
                if df['close'].iloc[i] >= df['close'].iloc[i+1]:
                    return False, 0.0
        
        return True, 0.8
    
    def detect_patterns(self, df: pd.DataFrame) -> List[Dict]:
        """
        Detect all patterns in recent data
        
        Args:
            df: OHLCV data
            
        Returns:
            List of detected patterns
        """
        patterns = []
        
        for index in range(max(2, len(df) - 50), len(df)):
            for pattern_name, detect_func in self.patterns.items():
                is_detected, confidence = detect_func(df, index)
                
                if is_detected:
                    direction = 'bullish' if pattern_name in [
                        'hammer', 'bullish_engulfing', 'morning_star', 
                        'three_white_soldiers'
                    ] else 'bearish' if pattern_name in [
                        'shooting_star', 'bearish_engulfing', 'evening_star',
                        'three_black_crows'
                    ] else 'neutral'
                    
                    patterns.append({
                        'pattern': pattern_name,
                        'direction': direction,
                        'index': index,
                        'confidence': confidence,
                        'price': df['close'].iloc[index]
                    })
        
        return patterns
    
    def predict_pattern_probability(self, df: pd.DataFrame, index: int) -> Dict:
        """
        Predict pattern with AI probability
        
        Args:
            df: OHLCV data
            index: Current index
            
        Returns:
            Pattern probability dictionary
        """
        sequence = self.prepare_sequence(df, index, 10)
        
        if sequence is None:
            return {'pattern': 'unknown', 'probability': 0.0}
        
        # Rule-based for now (AI training would require labeled data)
        patterns = []
        
        for pattern_name, detect_func in self.patterns.items():
            is_detected, confidence = detect_func(df, index)
            if is_detected:
                patterns.append({
                    'pattern': pattern_name,
                    'confidence': confidence
                })
        
        if patterns:
            # Return highest confidence pattern
            best = max(patterns, key=lambda x: x['confidence'])
            return best
        
        return {'pattern': 'none', 'confidence': 0.5}


class RegimeDetectionAI:
    """
    AI-powered market regime detection
    Uses clustering and mixture models for regime classification
    """
    
    def __init__(self, use_ai: bool = True, model_path: str = None):
        """
        Initialize Regime AI
        
        Args:
            use_ai: Whether to use AI
            model_path: Model path
        """
        self.use_ai = use_ai
        self.gmm = None
        self.kmeans = None
        self.scaler = StandardScaler()
        self.is_trained = False
        
        if model_path:
            try:
                self.gmm = joblib.load(model_path)
                self.is_trained = True
            except:
                pass
        
        if not self.gmm and self.use_ai:
            self.gmm = GaussianMixture(
                n_components=3,
                covariance_type='full',
                random_state=42
            )
        
        # Regime labels (will be determined after fitting)
        self.regime_labels = ['low_volatility', 'trending', 'high_volatility']
    
    def prepare_regime_features(self, df: pd.DataFrame) -> np.ndarray:
        """
        Prepare features for regime detection
        
        Args:
            df: OHLCV data
            
        Returns:
            Feature array
        """
        features = []
        
        # Calculate indicators
        returns = df['close'].pct_change().fillna(0)
        
        # Volatility features
        volatility_5 = returns.rolling(5).std()
        volatility_20 = returns.rolling(20).std()
        volatility_ratio = volatility_5 / volatility_20.replace(0, 1)
        
        features.append(volatility_20.fillna(0).values)
        features.append(volatility_ratio.fillna(1).values)
        
        # Trend features
        sma_9 = df['close'].rolling(9).mean()
        sma_21 = df['close'].rolling(21).mean()
        trend_strength = (sma_9 - sma_21) / sma_21.replace(0, 1)
        
        features.append(trend_strength.fillna(0).values)
        
        # Volume features
        if 'tick_volume' in df.columns:
            volume_ma = df['tick_volume'].rolling(20).mean()
            volume_ratio = df['tick_volume'] / volume_ma.replace(0, 1)
            features.append(volume_ratio.fillna(1).values)
        
        # Range features
        daily_range = (df['high'] - df['low']) / df['close']
        features.append(daily_range.fillna(0).values)
        
        return np.column_stack(features)
    
    def detect_regime(self, df: pd.DataFrame) -> Dict:
        """
        Detect current market regime
        
        Args:
            df: OHLCV data
            
        Returns:
            Regime detection result
        """
        if len(df) < 30:
            return self._rule_based_regime(df)
        
        features = self.prepare_regime_features(df)
        
        # Use recent data
        recent_features = features[-30:]
        
        # Remove NaN
        recent_features = np.nan_to_num(recent_features, 0)
        
        if self.use_ai and self.is_trained and self.gmm:
            try:
                # Scale features
                scaled = self.scaler.fit_transform(recent_features)
                
                # Get regime probabilities
                probs = self.gmm.predict_proba(scaled[-1:])
                regime_idx = np.argmax(probs[0])
                
                # Map to regime name
                regime = self.regime_labels[regime_idx]
                confidence = probs[0][regime_idx]
                
                return {
                    'regime': regime,
                    'confidence': float(confidence),
                    'probabilities': {
                        self.regime_labels[i]: float(probs[0][i])
                        for i in range(len(self.regime_labels))
                    }
                }
            except Exception as e:
                logger.warning(f"Regime AI failed: {e}")
        
        # Fallback to rule-based
        return self._rule_based_regime(df)
    
    def _rule_based_regime(self, df: pd.DataFrame) -> Dict:
        """
        Rule-based regime detection
        
        Args:
            df: OHLCV data
            
        Returns:
            Regime dictionary
        """
        if len(df) < 20:
            return {'regime': 'unknown', 'confidence': 0.0}
        
        # Calculate features
        returns = df['close'].pct_change().fillna(0)
        
        # Volatility
        volatility = returns.rolling(20).std().iloc[-1]
        avg_volatility = returns.std()
        
        # Trend
        sma_9 = df['close'].rolling(9).mean().iloc[-1]
        sma_21 = df['close'].rolling(21).mean().iloc[-1]
        
        # Determine regime
        if volatility < avg_volatility * 0.7:
            regime = 'low_volatility'
            confidence = 0.7
        elif volatility > avg_volatility * 1.3:
            regime = 'high_volatility'
            confidence = 0.7
        else:
            if sma_9 > sma_21:
                regime = 'trending'
                confidence = 0.6
            else:
                regime = 'low_volatility'
                confidence = 0.5
        
        return {
            'regime': regime,
            'confidence': confidence,
            'probabilities': {
                'low_volatility': 0.5,
                'trending': 0.3,
                'high_volatility': 0.2
            }
        }
    
    def get_regime_parameters(self, regime: str) -> Dict:
        """
        Get trading parameters for current regime
        
        Args:
            regime: Detected regime
            
        Returns:
            Dictionary of recommended parameters
        """
        regime_params = {
            'low_volatility': {
                'position_size_multiplier': 1.2,
                'stop_loss_pips': 15,
                'take_profit_pips': 25,
                'use_tight_stops': False,
                'recommended_strategies': ['mean_reversion', 'scalping']
            },
            'trending': {
                'position_size_multiplier': 1.0,
                'stop_loss_pips': 25,
                'take_profit_pips': 50,
                'use_tight_stops': False,
                'recommended_strategies': ['trend_following', 'breakout']
            },
            'high_volatility': {
                'position_size_multiplier': 0.5,
                'stop_loss_pips': 35,
                'take_profit_pips': 40,
                'use_tight_stops': True,
                'recommended_strategies': ['mean_reversion', 'contrarian']
            }
        }
        
        return regime_params.get(regime, regime_params['low_volatility'])
    
    def train(self, X: np.ndarray, regime_names: List[str] = None):
        """
        Train regime detection model
        
        Args:
            X: Training features
            regime_names: Optional regime names for labeling
        """
        if not self.use_ai or len(X) < 100:
            return
        
        try:
            # Scale features
            X_scaled = self.scaler.fit_transform(X)
            
            # Fit GMM
            self.gmm.fit(X_scaled)
            self.is_trained = True
            
            # Determine labels from data
            labels = self.gmm.predict(X_scaled[0:1])
            logger.info(f"Regime AI trained with {len(X)} samples")
        except Exception as e:
            logger.error(f"Training failed: {e}")
    
    def save(self, path: str):
        """Save model"""
        if self.gmm:
            joblib.dump(self.gmm, path)
    
    def load(self, path: str):
        """Load model"""
        self.gmm = joblib.load(path)
        self.is_trained = True


def main():
    """Test Pattern and Regime AI"""
    import random
    
    print("="*60)
    print("PATTERN & REGIME AI TEST")
    print("="*60)
    
    # Create sample data
    data = []
    price = 1.1000
    
    for i in range(300):
        price += random.uniform(-0.002, 0.002)
        
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
    
    # Test Pattern AI
    print("\n📊 Testing Pattern Recognition AI...")
    pattern_ai = PatternRecognitionAI()
    patterns = pattern_ai.detect_patterns(df)
    
    print(f"✅ Found {len(patterns)} patterns")
    
    # Show recent patterns
    recent = [p for p in patterns if p['index'] > len(df) - 10]
    for p in recent[:5]:
        print(f"  {p['pattern']}: {p['direction']} (conf: {p['confidence']:.2f})")
    
    # Test Regime AI
    print("\n📊 Testing Regime Detection AI...")
    regime_ai = RegimeDetectionAI(use_ai=False)
    regime = regime_ai.detect_regime(df)
    
    print(f"✅ Current Regime: {regime['regime']}")
    print(f"   Confidence: {regime['confidence']:.2f}")
    
    # Get parameters
    params = regime_ai.get_regime_parameters(regime['regime'])
    print(f"\n📋 Recommended Parameters:")
    for key, value in params.items():
        print(f"   {key}: {value}")
    
    print("\n✅ Pattern & Regime AI test complete!")


if __name__ == "__main__":
    main()
