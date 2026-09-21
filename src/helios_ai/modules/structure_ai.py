"""
Helios AI - Market Structure Analysis with AI
Predicts swing points and market structure using ML
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
import joblib
import logging

logger = logging.getLogger(__name__)


class StructureAI:
    """
    AI-enhanced market structure analysis
    Uses Random Forest to identify major swing points
    """
    
    def __init__(self, use_ai: bool = True, model_path: str = None):
        """
        Initialize Structure AI
        
        Args:
            use_ai: Whether to use AI models
            model_path: Path to saved model
        """
        self.use_ai = use_ai
        self.model = None
        self.scaler = StandardScaler()
        self.is_trained = False
        
        # Try to load existing model
        if model_path:
            try:
                self.model = joblib.load(model_path)
                self.is_trained = True
            except:
                pass
        
        # Default to Random Forest if not loaded
        if not self.model and self.use_ai:
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                random_state=42,
                n_jobs=-1
            )
    
    def prepare_features(self, df: pd.DataFrame, index: int, window: int = 10) -> np.ndarray:
        """
        Prepare features for swing point prediction
        
        Args:
            df: OHLCV data
            index: Current candle index
            window: Lookback window
            
        Returns:
            Feature array
        """
        if index < window:
            return None
        
        features = []
        
        # Get window data
        window_data = df.iloc[index-window:index]
        
        # Price momentum features
        returns = df['close'].pct_change().iloc[index-window:index].values
        features.extend([
            np.mean(returns),
            np.std(returns),
            np.min(returns),
            np.max(returns),
            returns[-1] if len(returns) > 0 else 0
        ])
        
        # Volume features
        if 'tick_volume' in df.columns:
            volumes = df['tick_volume'].iloc[index-window:index].values
            vol_ma = np.mean(volumes)
            features.extend([
                volumes[-1] if len(volumes) > 0 else 0,
                vol_ma,
                volumes[-1] / vol_ma if vol_ma > 0 else 1
            ])
        
        # Price position features
        highs = df['high'].iloc[index-window:index].values
        lows = df['low'].iloc[index-window:index].values
        closes = df['close'].iloc[index-window:index].values
        
        features.extend([
            (closes[-1] - np.min(lows)) / (np.max(highs) - np.min(lows) + 0.0001) if len(closes) > 0 else 0.5,
            (np.max(highs) - closes[-1]) / (np.max(highs) - np.min(lows) + 0.0001) if len(closes) > 0 else 0.5,
            (closes[-1] - np.mean(closes)) / (np.std(closes) + 0.0001) if len(closes) > 1 and np.std(closes) > 0 else 0
        ])
        
        # Wick features
        for i in range(max(0, index-5), index):
            high = df['high'].iloc[i]
            low = df['low'].iloc[i]
            close = df['close'].iloc[i]
            open_price = df['open'].iloc[i]
            
            body = abs(close - open_price)
            upper_wick = high - max(close, open_price)
            lower_wick = min(close, open_price) - low
            total_range = high - low + 0.0001
            
            features.extend([
                upper_wick / total_range,
                lower_wick / total_range,
                body / total_range
            ])
        
        return np.array(features).reshape(1, -1)
    
    def is_swing_point(self, df: pd.DataFrame, index: int, window: int = 5) -> Tuple[bool, float]:
        """
        Determine if current candle is a swing point with AI confidence
        
        Args:
            df: OHLCV data
            index: Current index
            window: Swing detection window
            
        Returns:
            Tuple of (is_swing_point, confidence)
        """
        if index < window * 2:
            return self._rule_based_swing(df, index, window)
        
        if self.use_ai and self.is_trained and self.model:
            try:
                features = self.prepare_features(df, index, window * 2)
                if features is not None:
                    features_scaled = self.scaler.transform(features)
                    prob = self.model.predict_proba(features_scaled)[0]
                    prediction = self.model.predict(features_scaled)[0]
                    confidence = max(prob)
                    
                    if confidence > 0.6:
                        is_swing = prediction == 1
                        return is_swing, confidence
            except Exception as e:
                logger.warning(f"AI prediction failed: {e}")
        
        # Fallback to rule-based
        return self._rule_based_swing(df, index, window)
    
    def _rule_based_swing(self, df: pd.DataFrame, index: int, window: int) -> Tuple[bool, float]:
        """
        Rule-based swing point detection
        
        Args:
            df: OHLCV data
            index: Current index
            window: Detection window
            
        Returns:
            Tuple of (is_swing_point, confidence)
        """
        if index < window or index >= len(df) - window:
            return False, 0.0
        
        highs = df['high'].values
        lows = df['low'].values
        
        # Check for swing high
        is_high = True
        for j in range(1, window + 1):
            if highs[index] <= highs[index-j] or highs[index] <= highs[index+j]:
                is_high = False
                break
        
        if is_high:
            return True, 0.8
        
        # Check for swing low
        is_low = True
        for j in range(1, window + 1):
            if lows[index] >= lows[index-j] or lows[index] >= lows[index+j]:
                is_low = False
                break
        
        if is_low:
            return True, 0.8
        
        return False, 0.0
    
    def identify_bos(self, df: pd.DataFrame, swing_points: List[Dict]) -> List[Dict]:
        """
        Identify Break of Structure with AI scoring
        
        Args:
            df: OHLCV data
            swing_points: List of swing points
            
        Returns:
            List of BOS events with confidence scores
        """
        bos_events = []
        
        if len(swing_points) < 2:
            return bos_events
        
        closes = df['close'].values
        
        for i in range(1, len(swing_points)):
            prev = swing_points[i-1]
            curr = swing_points[i]
            
            # Bullish BOS
            if prev['type'] == 'high' and curr['type'] == 'high':
                if curr['price'] > prev['price']:
                    # Calculate confidence
                    displacement = (curr['price'] - prev['price']) / prev['price']
                    
                    # Simple confidence based on displacement
                    confidence = min(displacement * 100, 0.99)
                    
                    bos_events.append({
                        'type': 'bullish',
                        'start_index': prev['index'],
                        'end_index': curr['index'],
                        'start_price': prev['price'],
                        'end_price': curr['price'],
                        'confidence': confidence,
                        'momentum': displacement * 100
                    })
            
            # Bearish BOS
            elif prev['type'] == 'low' and curr['type'] == 'low':
                if curr['price'] < prev['price']:
                    displacement = (prev['price'] - curr['price']) / prev['price']
                    confidence = min(displacement * 100, 0.99)
                    
                    bos_events.append({
                        'type': 'bearish',
                        'start_index': prev['index'],
                        'end_index': curr['index'],
                        'start_price': prev['price'],
                        'end_price': curr['price'],
                        'confidence': confidence,
                        'momentum': displacement * 100
                    })
        
        return bos_events
    
    def predict_trend(self, df: pd.DataFrame, lookback: int = 50) -> Dict:
        """
        Predict current trend with AI confidence
        
        Args:
            df: OHLCV data
            lookback: Bars to look back
            
        Returns:
            Dictionary with trend prediction
        """
        if len(df) < lookback:
            return {'direction': 'neutral', 'confidence': 0.0}
        
        recent = df.iloc[-lookback:]
        
        # Simple trend calculation
        first_close = recent['close'].iloc[0]
        last_close = recent['close'].iloc[-1]
        
        change_pct = (last_close - first_close) / first_close
        
        if change_pct > 0.02:  # 2% threshold
            direction = 'bullish'
            confidence = min(abs(change_pct) * 10, 0.99)
        elif change_pct < -0.02:
            direction = 'bearish'
            confidence = min(abs(change_pct) * 10, 0.99)
        else:
            direction = 'neutral'
            confidence = 0.5
        
        return {
            'direction': direction,
            'confidence': confidence,
            'change_pct': change_pct
        }
    
    def train(self, df: pd.DataFrame, labels: np.ndarray):
        """
        Train the model on labeled data
        
        Args:
            df: Training data
            labels: Swing point labels (1 = swing, 0 = not swing)
        """
        if not self.use_ai:
            return
        
        # Prepare training data
        X = []
        y = []
        
        window = 10
        for i in range(window, len(df) - window):
            features = self.prepare_features(df, i, window)
            if features is not None:
                X.append(features[0])
                y.append(labels[i])
        
        X = np.array(X)
        y = np.array(y)
        
        if len(X) < 100:
            logger.warning("Insufficient training data")
            return
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train model
        self.model.fit(X_scaled, y)
        self.is_trained = True
        
        logger.info(f"Structure AI trained on {len(X)} samples")
    
    def save(self, path: str):
        """Save model"""
        if self.model:
            joblib.dump(self.model, path)
            logger.info(f"Model saved to {path}")
    
    def load(self, path: str):
        """Load model"""
        self.model = joblib.load(path)
        self.is_trained = True
        logger.info(f"Model loaded from {path}")


def main():
    """Test Structure AI"""
    import random
    
    print("="*60)
    print("STRUCTURE AI TEST")
    print("="*60)
    
    # Create sample data
    data = []
    price = 1.1000
    
    for i in range(500):
        price += random.uniform(-0.001, 0.001)
        data.append({
            "time": 1700000000 + i * 900,
            "open": price - random.uniform(0, 0.0005),
            "high": price + random.uniform(0, 0.001),
            "low": price - random.uniform(0, 0.001),
            "close": price + random.uniform(-0.0005, 0.0005),
            "tick_volume": random.randint(100, 1000)
        })
    
    df = pd.DataFrame(data)
    
    # Initialize AI
    ai = StructureAI(use_ai=False)  # Use rule-based for test
    
    # Test swing detection
    print("\n📊 Testing swing point detection...")
    
    swing_points = []
    for i in range(20, len(df) - 20):
        is_swing, confidence = ai.is_swing_point(df, i, window=5)
        if is_swing:
            swing_type = "HIGH" if df['high'].iloc[i] > df['close'].iloc[i] else "LOW"
            swing_points.append({
                'index': i,
                'type': 'high' if swing_type == "HIGH" else 'low',
                'price': df['high'].iloc[i] if swing_type == "HIGH" else df['low'].iloc[i],
                'confidence': confidence
            })
    
    print(f"✅ Found {len(swing_points)} swing points")
    
    # Show recent swings
    print(f"\n📈 Recent Swing Points:")
    for sp in swing_points[-5:]:
        print(f"  {sp['type'].upper()}: {sp['price']:.5f} (conf: {sp['confidence']:.2f})")
    
    # Test BOS detection
    print("\n🔄 Testing BOS detection...")
    bos_events = ai.identify_bos(df, swing_points)
    print(f"✅ Found {len(bos_events)} BOS events")
    
    # Test trend prediction
    print("\n📊 Testing trend prediction...")
    trend = ai.predict_trend(df)
    print(f"✅ Trend: {trend['direction']} (confidence: {trend['confidence']:.2f})")
    
    print("\n✅ Structure AI test complete!")


if __name__ == "__main__":
    main()
