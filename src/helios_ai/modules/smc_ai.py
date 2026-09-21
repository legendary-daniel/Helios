"""
Helios AI - Smart Money Concepts AI
AI-enhanced Fair Value Gap and Order Block analysis
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from sklearn.ensemble import GradientBoostingRegressor, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib
import logging

logger = logging.getLogger(__name__)


class FVGAI:
    """
    AI-enhanced Fair Value Gap analysis
    Predicts FVG quality and fill probability
    """
    
    def __init__(self, use_ai: bool = True, model_path: str = None):
        """
        Initialize FVG AI
        
        Args:
            use_ai: Whether to use AI models
            model_path: Path to saved model
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
            self.model = GradientBoostingRegressor(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                random_state=42
            )
    
    def find_fvgs(self, df: pd.DataFrame) -> List[Dict]:
        """
        Find Fair Value Gaps
        
        Args:
            df: OHLCV data
            
        Returns:
            List of FVG dictionaries
        """
        fvgs = []
        
        if len(df) < 3:
            return fvgs
        
        highs = df['high'].values
        lows = df['low'].values
        
        for i in range(2, len(df)):
            # Bullish FVG: Low[i-2] > High[i]
            if lows[i-2] > highs[i]:
                gap_size = lows[i-2] - highs[i]
                
                fvgs.append({
                    'index': i,
                    'type': 'bullish',
                    'top': lows[i-2],
                    'bottom': highs[i],
                    'mid': (lows[i-2] + highs[i]) / 2,
                    'size': gap_size,
                    'created_at': i
                })
            
            # Bearish FVG: High[i-2] < Low[i]
            elif highs[i-2] < lows[i]:
                gap_size = lows[i] - highs[i-2]
                
                fvgs.append({
                    'index': i,
                    'type': 'bearish',
                    'top': lows[i],
                    'bottom': highs[i-2],
                    'mid': (lows[i] + highs[i-2]) / 2,
                    'size': gap_size,
                    'created_at': i
                })
        
        return fvgs
    
    def prepare_fvg_features(self, fvg: Dict, df: pd.DataFrame, current_index: int) -> np.ndarray:
        """
        Prepare features for FVG quality prediction
        
        Args:
            fvg: FVG dictionary
            df: OHLCV data
            current_index: Current candle index
            
        Returns:
            Feature array
        """
        features = []
        
        # FVG size features
        features.extend([
            fvg['size'],
            fvg['size'] * 10000,  # Size in pips (for forex)
            fvg['size'] / df['close'].iloc[current_index]  # Size as % of price
        ])
        
        # Volume features
        if 'tick_volume' in df.columns:
            # Volume during FVG creation
            fvg_volume = df['tick_volume'].iloc[fvg['created_at']:current_index].mean()
            avg_volume = df['tick_volume'].iloc[-20:].mean()
            features.extend([
                fvg_volume / avg_volume if avg_volume > 0 else 1,
                fvg_volume
            ])
        
        # Time features
        age = current_index - fvg['created_at']
        features.append(age)
        
        # Volatility features
        recent_volatility = df['close'].iloc[max(0, current_index-20):current_index].std()
        features.append(recent_volatility)
        
        # Current price position relative to FVG
        current_price = df['close'].iloc[current_index]
        
        if fvg['type'] == 'bullish':
            distance = (current_price - fvg['bottom']) / fvg['size'] if fvg['size'] > 0 else 0
        else:
            distance = (fvg['top'] - current_price) / fvg['size'] if fvg['size'] > 0 else 0
        
        features.append(distance)
        
        return np.array(features).reshape(1, -1)
    
    def predict_fill_probability(self, fvg: Dict, df: pd.DataFrame, current_index: int) -> float:
        """
        Predict probability that FVG will be filled
        
        Args:
            fvg: FVG dictionary
            df: OHLCV data
            current_index: Current index
            
        Returns:
            Probability (0-1)
        """
        if not self.use_ai or not self.is_trained or not self.model:
            return self._rule_based_fill_probability(fvg, df, current_index)
        
        try:
            features = self.prepare_fvg_features(fvg, df, current_index)
            features_scaled = self.scaler.transform(features)
            probability = self.model.predict(features_scaled)[0]
            return max(0, min(1, probability))
        except Exception as e:
            logger.warning(f"FVG AI prediction failed: {e}")
            return self._rule_based_fill_probability(fvg, df, current_index)
    
    def _rule_based_fill_probability(self, fvg: Dict, df: pd.DataFrame, current_index: int) -> float:
        """
        Rule-based fill probability
        
        Args:
            fvg: FVG dictionary
            df: OHLCV data
            current_index: Current index
            
        Returns:
            Probability (0-1)
        """
        # Base probability
        prob = 0.5
        
        # Age factor - older FVGs more likely to be filled
        age = current_index - fvg['created_at']
        if age > 20:
            prob += 0.2
        elif age > 10:
            prob += 0.1
        elif age < 3:
            prob -= 0.1
        
        # Size factor - larger FVGs more likely to attract price
        size_pips = fvg['size'] * 10000
        if size_pips > 10:
            prob += 0.1
        elif size_pips < 3:
            prob -= 0.1
        
        # Current price proximity
        current_price = df['close'].iloc[current_index]
        
        if fvg['type'] == 'bullish':
            distance_pct = (current_price - fvg['bottom']) / fvg['size'] if fvg['size'] > 0 else 1
            if 0.8 < distance_pct < 1.2:  # Near the gap
                prob += 0.15
        else:
            distance_pct = (fvg['top'] - current_price) / fvg['size'] if fvg['size'] > 0 else 1
            if 0.8 < distance_pct < 1.2:
                prob += 0.15
        
        return max(0, min(1, prob))
    
    def score_fvg_quality(self, fvg: Dict, df: pd.DataFrame, current_index: int) -> Dict:
        """
        Score FVG quality with AI confidence
        
        Args:
            fvg: FVG dictionary
            df: OHLCV data
            current_index: Current index
            
        Returns:
            Quality score dictionary
        """
        fill_prob = self.predict_fill_probability(fvg, df, current_index)
        
        # Quality factors
        quality_score = 0.5
        
        # Size quality
        size_pips = fvg['size'] * 10000
        if 5 <= size_pips <= 20:
            quality_score += 0.2
        elif size_pips > 20:
            quality_score += 0.1
        
        # Freshness quality
        age = current_index - fvg['created_at']
        if 3 <= age <= 10:
            quality_score += 0.2
        elif age > 20:
            quality_score -= 0.1
        
        # Volume quality
        if 'tick_volume' in df.columns:
            fvg_volume = df['tick_volume'].iloc[fvg['created_at']:current_index].mean()
            avg_volume = df['tick_volume'].iloc[-20:].mean()
            if fvg_volume > avg_volume * 1.5:
                quality_score += 0.1
        
        quality_score = max(0, min(1, quality_score))
        
        return {
            'fvg': fvg,
            'quality_score': quality_score,
            'fill_probability': fill_prob,
            'confidence': quality_score * fill_prob,
            'recommendation': 'TRADE' if quality_score * fill_prob > 0.5 else 'WAIT'
        }
    
    def analyze_fvgs(self, df: pd.DataFrame) -> List[Dict]:
        """
        Complete FVG analysis with AI
        
        Args:
            df: OHLCV data
            
        Returns:
            List of analyzed FVGs
        """
        fvgs = self.find_fvgs(df)
        current_index = len(df) - 1
        
        analyzed = []
        for fvg in fvgs:
            scored = self.score_fvg_quality(fvg, df, current_index)
            analyzed.append(scored)
        
        # Sort by confidence
        analyzed.sort(key=lambda x: x['confidence'], reverse=True)
        
        return analyzed
    
    def train(self, X: np.ndarray, y: np.ndarray):
        """
        Train the model
        
        Args:
            X: Features
            y: Target (fill probability 0-1)
        """
        if not self.use_ai or len(X) < 100:
            return
        
        try:
            X_scaled = self.scaler.fit_transform(X)
            self.model.fit(X_scaled, y)
            self.is_trained = True
            logger.info(f"FVG AI trained on {len(X)} samples")
        except Exception as e:
            logger.error(f"Training failed: {e}")
    
    def save(self, path: str):
        """Save model"""
        if self.model:
            joblib.dump(self.model, path)
    
    def load(self, path: str):
        """Load model"""
        self.model = joblib.load(path)
        self.is_trained = True


class OBValidationAI:
    """
    AI-enhanced Order Block validation
    Predicts Order Block strength and success probability
    """
    
    def __init__(self, use_ai: bool = True, model_path: str = None):
        """
        Initialize OB AI
        
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
                max_depth=8,
                random_state=42
            )
    
    def find_order_blocks(self, df: pd.DataFrame) -> List[Dict]:
        """
        Find potential Order Blocks
        
        Args:
            df: OHLCV data
            
        Returns:
            List of OB dictionaries
        """
        obs = []
        
        if len(df) < 10:
            return obs
        
        closes = df['close'].values
        opens = df['open'].values
        highs = df['high'].values
        lows = df['low'].values
        
        # Look for strong moves
        for i in range(10, len(df) - 5):
            # Check for bullish sequence
            bullish_count = 0
            for j in range(1, 5):
                if i + j < len(closes):
                    if closes[i + j] > closes[i + j - 1]:
                        bullish_count += 1
            
            if bullish_count >= 4:  # 4+ consecutive higher closes
                # Find the last bearish candle before the move
                for k in range(i - 1, max(0, i - 5), -1):
                    if closes[k] < opens[k]:  # Bearish candle
                        obs.append({
                            'index': k,
                            'type': 'bullish',
                            'start_price': highs[k],
                            'end_price': lows[k],
                            'midpoint': (highs[k] + lows[k]) / 2,
                            'size': highs[k] - lows[k],
                            'created_at': k
                        })
                        break
            
            # Check for bearish sequence
            bearish_count = 0
            for j in range(1, 5):
                if i + j < len(closes):
                    if closes[i + j] < closes[i + j - 1]:
                        bearish_count += 1
            
            if bearish_count >= 4:
                for k in range(i - 1, max(0, i - 5), -1):
                    if closes[k] > opens[k]:  # Bullish candle
                        obs.append({
                            'index': k,
                            'type': 'bearish',
                            'start_price': highs[k],
                            'end_price': lows[k],
                            'midpoint': (highs[k] + lows[k]) / 2,
                            'size': highs[k] - lows[k],
                            'created_at': k
                        })
                        break
        
        return obs
    
    def validate_order_block(self, ob: Dict, df: pd.DataFrame, current_index: int) -> Dict:
        """
        Validate Order Block with AI confidence
        
        Args:
            ob: Order Block dictionary
            df: OHLCV data
            current_index: Current index
            
        Returns:
            Validation result
        """
        # Calculate strength factors
        strength = 0.5
        
        # Age factor
        age = current_index - ob['created_at']
        if age < 5:
            strength += 0.2
        elif age > 15:
            strength -= 0.2
        
        # Size factor
        size_pips = ob['size'] * 10000
        if 5 <= size_pips <= 15:
            strength += 0.15
        
        # Volume factor
        if 'tick_volume' in df.columns and ob['created_at'] > 0:
            ob_volume = df['tick_volume'].iloc[ob['created_at']]
            avg_volume = df['tick_volume'].iloc[-20:].mean()
            if ob_volume > avg_volume:
                strength += 0.15
        
        # Proximity to current price
        current_price = df['close'].iloc[current_index]
        
        if ob['type'] == 'bullish':
            distance_pct = abs(current_price - ob['midpoint']) / current_price
        else:
            distance_pct = abs(current_price - ob['midpoint']) / current_price
        
        if distance_pct < 0.01:  # Within 1%
            strength += 0.1
        elif distance_pct > 0.03:  # More than 3% away
            strength -= 0.1
        
        strength = max(0, min(1, strength))
        
        return {
            'ob': ob,
            'strength': strength,
            'valid': strength > 0.5,
            'age': age,
            'recommendation': 'USE' if strength > 0.6 else 'CAUTION' if strength > 0.4 else 'AVOID'
        }
    
    def analyze_order_blocks(self, df: pd.DataFrame) -> List[Dict]:
        """
        Complete OB analysis
        
        Args:
            df: OHLCV data
            
        Returns:
            List of validated OBs
        """
        obs = self.find_order_blocks(df)
        current_index = len(df) - 1
        
        validated = []
        for ob in obs:
            validation = self.validate_order_block(ob, df, current_index)
            validated.append(validation)
        
        # Sort by strength
        validated.sort(key=lambda x: x['strength'], reverse=True)
        
        return validated


def main():
    """Test FVG and OB AI"""
    import random
    
    print("="*60)
    print("FVG & ORDER BLOCK AI TEST")
    print("="*60)
    
    # Create sample data
    data = []
    price = 1.1000
    
    for i in range(300):
        price += random.uniform(-0.001, 0.001)
        
        # Create some gaps
        if 50 <= i <= 55:
            if i == 52:
                price += 0.005  # Gap up
            else:
                price += random.uniform(-0.001, 0.002)
        
        high = price + random.uniform(0.0005, 0.001)
        low = price - random.uniform(0.0005, 0.001)
        close = price + random.uniform(-0.0003, 0.0003)
        open_price = price - random.uniform(-0.0002, 0.0002)
        
        data.append({
            "time": 1700000000 + i * 900,
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "tick_volume": random.randint(100, 1000)
        })
    
    df = pd.DataFrame(data)
    
    # Test FVG AI
    print("\n📊 Testing FVG AI...")
    fvg_ai = FVGAI(use_ai=False)
    fvgs = fvg_ai.analyze_fvgs(df)
    
    print(f"✅ Found {len(fvgs)} FVGs")
    
    for fvg in fvgs[:3]:
        print(f"\n  {fvg['fvg']['type'].upper()} FVG:")
        print(f"    Quality: {fvg['quality_score']:.2f}")
        print(f"    Fill Prob: {fvg['fill_probability']:.2f}")
        print(f"    Recommendation: {fvg['recommendation']}")
    
    # Test OB AI
    print("\n📊 Testing Order Block AI...")
    ob_ai = OBValidationAI()
    obs = ob_ai.analyze_order_blocks(df)
    
    print(f"✅ Found {len(obs)} Order Blocks")
    
    for ob in obs[:3]:
        print(f"\n  {ob['ob']['type'].upper()} OB:")
        print(f"    Strength: {ob['strength']:.2f}")
        print(f"    Valid: {ob['valid']}")
        print(f"    Recommendation: {ob['recommendation']}")
    
    print("\n✅ FVG & OB AI test complete!")


if __name__ == "__main__":
    main()
