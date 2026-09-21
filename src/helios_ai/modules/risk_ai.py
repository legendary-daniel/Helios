"""
Helios AI - Risk Management & Position Sizing AI
AI-driven risk management and dynamic position sizing
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
import joblib
import logging

logger = logging.getLogger(__name__)


class RiskManagementAI:
    """
    AI-enhanced risk management and position sizing
    Uses confidence scores and market conditions to optimize risk
    """
    
    def __init__(self, use_ai: bool = True, model_path: str = None):
        """
        Initialize Risk AI
        
        Args:
            use_ai: Whether to use AI
            model_path: Model path
        """
        self.use_ai = use_ai
        self.model = None
        self.scaler = StandardScaler()
        self.is_trained = False
        
        # Default risk parameters
        self.base_position_size = 1.0  # % of account
        self.max_position_size = 2.0
        self.min_position_size = 0.5
        
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
    
    def calculate_position_size(self, 
                              account_balance: float,
                              confidence: float,
                              regime: str,
                              volatility: float,
                              stop_loss_pips: int = 20) -> Dict:
        """
        Calculate optimal position size with AI
        
        Args:
            account_balance: Account balance
            confidence: Trade confidence (0-1)
            regime: Market regime
            volatility: Current volatility
            stop_loss_pips: Stop loss in pips
            
        Returns:
            Position size dictionary
        """
        # Base position size
        position_size = self.base_position_size
        
        # Adjust for confidence
        if confidence > 0.7:
            position_size *= 1.2  # Increase for high confidence
        elif confidence < 0.4:
            position_size *= 0.6  # Decrease for low confidence
        
        # Adjust for regime
        regime_multipliers = {
            'low_volatility': 1.2,
            'trending': 1.0,
            'high_volatility': 0.5
        }
        position_size *= regime_multipliers.get(regime, 1.0)
        
        # Adjust for volatility
        if volatility > 0.02:  # High volatility
            position_size *= 0.7
        elif volatility < 0.005:  # Low volatility
            position_size *= 1.1
        
        # Apply limits
        position_size = max(self.min_position_size, min(self.max_position_size, position_size))
        
        # Calculate actual lot size
        # Assuming $10 per pip per standard lot, and risk 1% per trade
        risk_amount = account_balance * 0.01  # 1% risk
        lot_size = (risk_amount / stop_loss_pips) / 10  # Simplified
        
        # Adjust lot size by position multiplier
        lot_size *= position_size
        
        return {
            'position_size_percent': position_size,
            'lot_size': round(lot_size, 2),
            'risk_amount': round(risk_amount, 2),
            'confidence': confidence,
            'regime': regime,
            'volatility': volatility,
            'adjustments': {
                'confidence_adjustment': 1.2 if confidence > 0.7 else 0.6 if confidence < 0.4 else 1.0,
                'regime_adjustment': regime_multipliers.get(regime, 1.0),
                'volatility_adjustment': 0.7 if volatility > 0.02 else 1.1 if volatility < 0.005 else 1.0
            }
        }
    
    def assess_trade_risk(self,
                         entry_price: float,
                         stop_loss: float,
                         take_profit: float,
                         confidence: float,
                         regime: str) -> Dict:
        """
        Assess overall trade risk
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            confidence: Trade confidence
            regime: Market regime
            
        Returns:
            Risk assessment dictionary
        """
        # Calculate risk/reward
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)
        
        if risk > 0:
            risk_reward = reward / risk
        else:
            risk_reward = 0
        
        # Base risk score
        risk_score = 0.5
        
        # Confidence factor
        if confidence > 0.7:
            risk_score -= 0.15
        elif confidence < 0.4:
            risk_score += 0.2
        
        # Risk/reward factor
        if risk_reward < 1:
            risk_score += 0.2
        elif risk_reward > 2:
            risk_score -= 0.1
        
        # Regime factor
        if regime == 'high_volatility':
            risk_score += 0.15
        elif regime == 'low_volatility':
            risk_score -= 0.1
        
        risk_score = max(0, min(1, risk_score))
        
        # Risk rating
        if risk_score < 0.3:
            rating = 'LOW'
            action = 'APPROVE'
        elif risk_score < 0.6:
            rating = 'MEDIUM'
            action = 'APPROVE_WITH_CAUTION'
        else:
            rating = 'HIGH'
            action = 'REJECT'
        
        return {
            'risk_score': round(risk_score, 2),
            'rating': rating,
            'action': action,
            'risk_reward': round(risk_reward, 2),
            'confidence': confidence,
            'regime': regime,
            'factors': {
                'confidence_factor': 'positive' if confidence > 0.5 else 'negative',
                'rr_factor': 'good' if risk_reward > 1.5 else 'poor',
                'regime_factor': regime
            }
        }
    
    def calculate_kelly_fraction(self,
                                 win_rate: float,
                                 avg_win: float,
                                 avg_loss: float,
                                 confidence: float = 1.0) -> float:
        """
        Calculate Kelly Criterion fraction
        
        Args:
            win_rate: Win rate (0-1)
            avg_win: Average winning trade amount
            avg_loss: Average losing trade amount
            confidence: System confidence (0-1)
            
        Returns:
            Kelly fraction (0-1)
        """
        if avg_loss == 0:
            return 0.02  # Default 2%
        
        # Win/loss ratio
        wl_ratio = avg_win / avg_loss
        
        # Kelly formula
        p = win_rate
        q = 1 - p
        b = wl_ratio
        
        kelly = (p * b - q) / b
        
        # Apply confidence multiplier (fractional Kelly)
        kelly *= confidence
        
        # Limit Kelly
        kelly = max(0.01, min(0.25, kelly))  # 1% to 25%
        
        return kelly
    
    def get_dynamic_stop_loss(self,
                            entry: float,
                            direction: str,
                            volatility: float,
                            regime: str,
                            atr: float = None) -> float:
        """
        Calculate dynamic stop loss based on AI
        
        Args:
            entry: Entry price
            direction: 'bullish' or 'bearish'
            volatility: Current volatility
            regime: Market regime
            atr: Average True Range (optional)
            
        Returns:
            Stop loss price
        """
        # Base stop multipliers
        base_multipliers = {
            'low_volatility': 1.5,
            'trending': 2.0,
            'high_volatility': 2.5
        }
        
        multiplier = base_multipliers.get(regime, 2.0)
        
        # Use ATR if available
        if atr:
            stop_distance = atr * multiplier
        else:
            # Use volatility
            stop_distance = entry * volatility * multiplier
        
        if direction == 'bullish':
            stop_loss = entry - stop_distance
        else:
            stop_loss = entry + stop_distance
        
        return stop_loss
    
    def get_dynamic_take_profit(self,
                              entry: float,
                              direction: str,
                              stop_loss: float,
                              risk_reward_target: float = 2.0,
                              regime: str = 'trending') -> float:
        """
        Calculate dynamic take profit
        
        Args:
            entry: Entry price
            direction: Trade direction
            stop_loss: Stop loss price
            risk_reward_target: Target R:R ratio
            regime: Market regime
            
        Returns:
            Take profit price
        """
        risk = abs(entry - stop_loss)
        
        # Adjust R:R based on regime
        rr_adjustments = {
            'low_volatility': 1.5,
            'trending': 2.5,
            'high_volatility': 1.5
        }
        
        adjusted_rr = risk_reward_target * rr_adjustments.get(regime, 2.0)
        
        reward = risk * adjusted_rr
        
        if direction == 'bullish':
            take_profit = entry + reward
        else:
            take_profit = entry - reward
        
        return take_profit
    
    def should_close_position(self,
                            current_profit_percent: float,
                            time_in_trade: int,  # minutes
                            regime: str,
                            hit_stop_loss: bool = False) -> Dict:
        """
        AI decision on whether to close position
        
        Args:
            current_profit_percent: Current profit %
            time_in_trade: Time in trade (minutes)
            regime: Current regime
            hit_stop_loss: Whether stop loss was hit
            
        Returns:
            Close decision dictionary
        """
        # Base decision
        close = False
        reason = ""
        
        # Stop loss hit
        if hit_stop_loss:
            close = True
            reason = "Stop loss hit"
        
        # Time-based exit
        time_thresholds = {
            'low_volatility': 30,   # 30 minutes
            'trending': 120,         # 2 hours
            'high_volatility': 15    # 15 minutes
        }
        
        max_time = time_thresholds.get(regime, 60)
        if time_in_trade > max_time:
            close = True
            reason = f"Time exit ({time_in_trade} min)"
        
        # Profit-based exit
        if current_profit_percent > 2.0:  # 2% profit
            # Partial exit?
            if current_profit_percent > 3.0:
                close = True
                reason = "Target reached"
        
        # Trailing stop logic
        if current_profit_percent < -0.5:  # 0.5% loss
            close = True
            reason = "Trailing stop hit"
        
        return {
            'close': close,
            'reason': reason,
            'profit_percent': current_profit_percent,
            'time_minutes': time_in_trade,
            'regime': regime
        }
    
    def calculate_max_daily_risk(self,
                               account_balance: float,
                               current_daily_loss: float,
                               consecutive_losses: int) -> Dict:
        """
        Calculate maximum daily risk allowed
        
        Args:
            account_balance: Account balance
            current_daily_loss: Current daily loss %
            consecutive_losses: Number of consecutive losses
            
        Returns:
            Risk limit dictionary
        """
        # Base daily risk limit
        max_daily_loss = 3.0  # 3% of account
        
        # Adjust for consecutive losses
        if consecutive_losses >= 3:
            max_daily_loss = 1.0  # Reduce to 1%
        elif consecutive_losses >= 2:
            max_daily_loss = 2.0  # Reduce to 2%
        
        # Check if limit reached
        remaining_risk = max(0, max_daily_loss - current_daily_loss)
        
        can_trade = remaining_risk > 0.5  # Minimum 0.5% to trade
        
        return {
            'max_daily_loss_percent': max_daily_loss,
            'current_daily_loss_percent': current_daily_loss,
            'remaining_risk_percent': remaining_risk,
            'consecutive_losses': consecutive_losses,
            'can_trade': can_trade,
            'recommended_action': 'STOP' if not can_trade else 'CONTINUE' if remaining_risk > 1.5 else 'REDUCE_SIZE'
        }
    
    def optimize_for_market(self, regime: str) -> Dict:
        """
        Get AI-optimized parameters for current regime
        
        Args:
            regime: Current market regime
            
        Returns:
            Optimized parameters
        """
        regime_params = {
            'low_volatility': {
                'position_size': 1.2,
                'stop_multiplier': 1.5,
                'target_rr': 1.5,
                'max_spread': 2,
                'strategy': 'mean_reversion'
            },
            'trending': {
                'position_size': 1.0,
                'stop_multiplier': 2.0,
                'target_rr': 2.5,
                'max_spread': 3,
                'strategy': 'trend_following'
            },
            'high_volatility': {
                'position_size': 0.5,
                'stop_multiplier': 2.5,
                'target_rr': 1.5,
                'max_spread': 4,
                'strategy': 'contrarian'
            }
        }
        
        return regime_params.get(regime, regime_params['trending'])
    
    def train(self, X: np.ndarray, y: np.ndarray):
        """
        Train the risk model
        
        Args:
            X: Features (confidence, volatility, regime, etc.)
            y: Target (optimal position size)
        """
        if not self.use_ai or len(X) < 100:
            return
        
        try:
            X_scaled = self.scaler.fit_transform(X)
            self.model.fit(X_scaled, y)
            self.is_trained = True
            logger.info(f"Risk AI trained on {len(X)} samples")
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


class DynamicLevelsAI:
    """
    AI-enhanced dynamic support/resistance levels
    Uses clustering for intelligent level detection
    """
    
    def __init__(self, use_ai: bool = True, n_clusters: int = 5):
        """
        Initialize Levels AI
        
        Args:
            use_ai: Whether to use AI clustering
            n_clusters: Number of S/R clusters
        """
        self.use_ai = use_ai
        self.n_clusters = n_clusters
        self.kmeans = None
        
        if use_ai:
            from sklearn.cluster import KMeans
            self.kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        
        self.scaler = StandardScaler()
    
    def find_support_resistance(self, df: pd.DataFrame) -> Dict:
        """
        Find S/R levels using AI clustering
        
        Args:
            df: OHLCV data
            
        Returns:
            S/R levels dictionary
        """
        if len(df) < 50:
            return self._rule_based_levels(df)
        
        # Extract swing points
        highs = []
        lows = []
        
        for i in range(10, len(df) - 10):
            # Swing high
            is_high = True
            for j in range(1, 6):
                if df['high'].iloc[i] <= df['high'].iloc[i-j] or df['high'].iloc[i] <= df['high'].iloc[i+j]:
                    is_high = False
                    break
            if is_high:
                highs.append(df['high'].iloc[i])
            
            # Swing low
            is_low = True
            for j in range(1, 6):
                if df['low'].iloc[i] >= df['low'].iloc[i-j] or df['low'].iloc[i] >= df['low'].iloc[i+j]:
                    is_low = False
                    break
            if is_low:
                lows.append(df['low'].iloc[i])
        
        levels = {
            'resistance': [],
            'support': []
        }
        
        # Cluster highs (resistance)
        if len(highs) >= self.n_clusters:
            try:
                X = np.array(highs).reshape(-1, 1)
                if self.use_ai and self.kmeans:
                    clusters = self.kmeans.fit_predict(X)
                    centers = self.kmeans.cluster_centers_
                    
                    for i, center in enumerate(centers):
                        strength = np.sum(clusters == i)
                        levels['resistance'].append({
                            'price': float(center[0]),
                            'strength': int(strength),
                            'type': 'cluster'
                        })
            except:
                levels['resistance'] = self._simple_levels(highs, 'resistance')
        else:
            levels['resistance'] = self._simple_levels(highs, 'resistance')
        
        # Cluster lows (support)
        if len(lows) >= self.n_clusters:
            try:
                X = np.array(lows).reshape(-1, 1)
                if self.use_ai and self.kmeans:
                    clusters = self.kmeans.fit_predict(X)
                    centers = self.kmeans.cluster_centers_
                    
                    for i, center in enumerate(centers):
                        strength = np.sum(clusters == i)
                        levels['support'].append({
                            'price': float(center[0]),
                            'strength': int(strength),
                            'type': 'cluster'
                        })
            except:
                levels['support'] = self._simple_levels(lows, 'support')
        else:
            levels['support'] = self._simple_levels(lows, 'support')
        
        # Sort by strength
        levels['resistance'].sort(key=lambda x: x['strength'], reverse=True)
        levels['support'].sort(key=lambda x: x['strength'], reverse=True)
        
        return levels
    
    def _simple_levels(self, prices: List[float], level_type: str) -> List[Dict]:
        """Simple S/R level extraction"""
        if not prices:
            return []
        
        # Average price
        avg_price = np.mean(prices)
        
        # Standard deviation
        std = np.std(prices)
        
        # Levels within 1 std
        levels = []
        for p in prices:
            if abs(p - avg_price) < std:
                levels.append({
                    'price': float(p),
                    'strength': 1,
                    'type': 'simple'
                })
        
        return levels[:self.n_clusters]
    
    def _rule_based_levels(self, df: pd.DataFrame) -> Dict:
        """Fallback rule-based levels"""
        recent = df.iloc[-20:]
        
        return {
            'resistance': [{'price': float(recent['high'].max()), 'strength': 3, 'type': 'recent_high'}],
            'support': [{'price': float(recent['low'].min()), 'strength': 3, 'type': 'recent_low'}]
        }


def main():
    """Test Risk Management AI"""
    print("="*60)
    print("RISK MANAGEMENT AI TEST")
    print("="*60)
    
    # Test position sizing
    print("\n📊 Testing Position Sizing...")
    risk_ai = RiskManagementAI(use_ai=False)
    
    position = risk_ai.calculate_position_size(
        account_balance=10000,
        confidence=0.75,
        regime='trending',
        volatility=0.01,
        stop_loss_pips=20
    )
    
    print(f"✅ Position Size: {position['position_size_percent']:.1f}%")
    print(f"   Lot Size: {position['lot_size']:.2f}")
    print(f"   Risk Amount: ${position['risk_amount']:.2f}")
    
    # Test risk assessment
    print("\n📊 Testing Risk Assessment...")
    assessment = risk_ai.assess_trade_risk(
        entry_price=1.1000,
        stop_loss=1.0980,
        take_profit=1.1050,
        confidence=0.7,
        regime='trending'
    )
    
    print(f"✅ Risk Score: {assessment['risk_score']}")
    print(f"   Rating: {assessment['rating']}")
    print(f"   Action: {assessment['action']}")
    print(f"   R:R: {assessment['risk_reward']:.1f}")
    
    # Test regime optimization
    print("\n📊 Testing Regime Optimization...")
    params = risk_ai.optimize_for_market('trending')
    
    print(f"✅ Optimized Parameters for trending:")
    for key, value in params.items():
        print(f"   {key}: {value}")
    
    # Test dynamic levels
    print("\n📊 Testing Dynamic Levels...")
    import random
    data = []
    price = 1.1000
    
    for i in range(200):
        price += random.uniform(-0.001, 0.001)
        data.append({
            "time": 1700000000 + i * 900,
            "open": price - 0.0005,
            "high": price + 0.001,
            "low": price - 0.001,
            "close": price + random.uniform(-0.0003, 0.0003),
            "tick_volume": random.randint(100, 1000)
        })
    
    df = pd.DataFrame(data)
    levels_ai = DynamicLevelsAI(use_ai=False)
    levels = levels_ai.find_support_resistance(df)
    
    print(f"✅ Support Levels: {len(levels['support'])}")
    print(f"✅ Resistance Levels: {len(levels['resistance'])}")
    
    for sup in levels['support'][:3]:
        print(f"   Support: {sup['price']:.5f} (strength: {sup['strength']})")
    
    for res in levels['resistance'][:3]:
        print(f"   Resistance: {res['price']:.5f} (strength: {res['strength']})")
    
    print("\n✅ Risk Management AI test complete!")


if __name__ == "__main__":
    main()
