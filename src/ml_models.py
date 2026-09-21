"""
Helios ML Trading System - Machine Learning Models
Advanced ML models including LSTM, Random Forest, and Ensemble methods
"""

import numpy as np
import pandas as pd
import joblib
import logging
from typing import Dict, List, Tuple, Optional, Any, Union
import warnings
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

warnings.filterwarnings('ignore')

# ML Libraries
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, VotingRegressor
from sklearn.linear_model import Ridge, ElasticNet
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.preprocessing import RobustScaler
import lightgbm as lgb
import xgboost as xgb

# Deep Learning
try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential, Model
    from tensorflow.keras.layers import LSTM, Dense, Dropout, Attention, MultiHeadAttention, LayerNormalization
    from tensorflow.keras.optimizers import Adam
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    logging.warning("TensorFlow not available. LSTM models will not work.")

class BaseModel:
    """Base model class for all ML models"""
    
    def __init__(self, name: str, config, logger=None):
        self.name = name
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.model = None
        self.scaler = None
        self.feature_names = None
        self.performance_metrics = {}
        
    def fit(self, X: Union[np.ndarray, pd.DataFrame], y: Union[np.ndarray, pd.Series]):
        """Train the model"""
        raise NotImplementedError
        
    def predict(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        """Make predictions"""
        raise NotImplementedError
        
    def predict_proba(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        """Predict probabilities (for classification models)"""
        raise NotImplementedError
        
    def save_model(self, filepath: str):
        """Save the trained model"""
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'performance_metrics': self.performance_metrics,
            'model_type': self.name
        }
        joblib.dump(model_data, filepath)
        self.logger.info(f"Model {self.name} saved to {filepath}")
        
    def load_model(self, filepath: str):
        """Load a trained model"""
        model_data = joblib.load(filepath)
        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.feature_names = model_data['feature_names']
        self.performance_metrics = model_data['performance_metrics']
        self.logger.info(f"Model {self.name} loaded from {filepath}")
        
    def evaluate(self, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        """Evaluate model performance"""
        predictions = self.predict(X)
        
        metrics = {
            'mse': mean_squared_error(y, predictions),
            'mae': mean_absolute_error(y, predictions),
            'r2': r2_score(y, predictions),
            'rmse': np.sqrt(mean_squared_error(y, predictions))
        }
        
        # Calculate directional accuracy
        actual_direction = np.sign(y)
        predicted_direction = np.sign(predictions)
        directional_accuracy = np.mean(actual_direction == predicted_direction)
        metrics['directional_accuracy'] = directional_accuracy
        
        return metrics

class RandomForestModel(BaseModel):
    """Random Forest model for trading predictions"""
    
    def __init__(self, config, logger=None):
        super().__init__("RandomForest", config, logger)
        
        # Model parameters optimized for financial data
        self.model = RandomForestRegressor(
            n_estimators=200,
            max_depth=15,
            min_samples_split=5,
            min_samples_leaf=2,
            max_features='sqrt',
            bootstrap=True,
            random_state=42,
            n_jobs=-1
        )
        self.scaler = RobustScaler()
        
    def fit(self, X: Union[np.ndarray, pd.DataFrame], y: Union[np.ndarray, pd.Series]):
        """Train Random Forest model"""
        self.logger.info("Training Random Forest model...")
        
        # Prepare data
        if isinstance(X, pd.DataFrame):
            self.feature_names = X.columns.tolist()
            X_array = X.values
        else:
            self.feature_names = [f'feature_{i}' for i in range(X.shape[1])]
            X_array = X
            
        # Scale features
        X_scaled = self.scaler.fit_transform(X_array)
        
        # Train model
        self.model.fit(X_scaled, y)
        
        # Evaluate on training data
        train_predictions = self.predict(X_scaled)
        self.performance_metrics = self.evaluate(y.values, train_predictions)
        
        self.logger.info(f"Random Forest training completed. R²: {self.performance_metrics['r2']:.4f}")
        
    def predict(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        """Make predictions"""
        if isinstance(X, pd.DataFrame):
            X_array = X.values
        else:
            X_array = X
            
        X_scaled = self.scaler.transform(X_array)
        return self.model.predict(X_scaled)

class LightGBMModel(BaseModel):
    """LightGBM model for fast training and inference"""
    
    def __init__(self, config, logger=None):
        super().__init__("LightGBM", config, logger)
        
        # LightGBM parameters optimized for financial data
        self.model = lgb.LGBMRegressor(
            n_estimators=1000,
            learning_rate=0.01,
            max_depth=8,
            num_leaves=255,
            feature_fraction=0.8,
            bagging_fraction=0.8,
            bagging_freq=1,
            min_child_samples=20,
            random_state=42,
            n_jobs=-1,
            verbose=-1
        )
        self.scaler = RobustScaler()
        
    def fit(self, X: Union[np.ndarray, pd.DataFrame], y: Union[np.ndarray, pd.Series]):
        """Train LightGBM model"""
        self.logger.info("Training LightGBM model...")
        
        # Prepare data
        if isinstance(X, pd.DataFrame):
            self.feature_names = X.columns.tolist()
            X_array = X.values
        else:
            self.feature_names = [f'feature_{i}' for i in range(X.shape[1])]
            X_array = X
            
        # Scale features
        X_scaled = self.scaler.fit_transform(X_array)
        
        # Train model with early stopping
        self.model.fit(
            X_scaled, y,
            eval_set=[(X_scaled, y)],
            callbacks=[lgb.early_stopping(50), lgb.log_evaluation(0)]
        )
        
        # Evaluate
        train_predictions = self.predict(X_scaled)
        self.performance_metrics = self.evaluate(y.values, train_predictions)
        
        self.logger.info(f"LightGBM training completed. R²: {self.performance_metrics['r2']:.4f}")
        
    def predict(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        """Make predictions"""
        if isinstance(X, pd.DataFrame):
            X_array = X.values
        else:
            X_array = X
            
        X_scaled = self.scaler.transform(X_array)
        return self.model.predict(X_scaled)

class XGBoostModel(BaseModel):
    """XGBoost model for gradient boosting"""
    
    def __init__(self, config, logger=None):
        super().__init__("XGBoost", config, logger)
        
        # XGBoost parameters
        self.model = xgb.XGBRegressor(
            n_estimators=1000,
            learning_rate=0.01,
            max_depth=8,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1,
            verbosity=0
        )
        self.scaler = RobustScaler()
        
    def fit(self, X: Union[np.ndarray, pd.DataFrame], y: Union[np.ndarray, pd.Series]):
        """Train XGBoost model"""
        self.logger.info("Training XGBoost model...")
        
        # Prepare data
        if isinstance(X, pd.DataFrame):
            self.feature_names = X.columns.tolist()
            X_array = X.values
        else:
            self.feature_names = [f'feature_{i}' for i in range(X.shape[1])]
            X_array = X
            
        # Scale features
        X_scaled = self.scaler.fit_transform(X_array)
        
        # Train model with early stopping
        self.model.fit(
            X_scaled, y,
            eval_set=[(X_scaled, y)],
            early_stopping_rounds=50,
            verbose=False
        )
        
        # Evaluate
        train_predictions = self.predict(X_scaled)
        self.performance_metrics = self.evaluate(y.values, train_predictions)
        
        self.logger.info(f"XGBoost training completed. R²: {self.performance_metrics['r2']:.4f}")
        
    def predict(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        """Make predictions"""
        if isinstance(X, pd.DataFrame):
            X_array = X.values
        else:
            X_array = X
            
        X_scaled = self.scaler.transform(X_array)
        return self.model.predict(X_scaled)

class LSTMModel(BaseModel):
    """LSTM model for time series prediction"""
    
    def __init__(self, config, logger=None):
        super().__init__("LSTM", config, logger)
        
        if not TENSORFLOW_AVAILABLE:
            raise ImportError("TensorFlow is required for LSTM models")
            
        self.sequence_length = config.ml.feature_window
        self.model = None
        self.scaler = RobustScaler()
        
    def _build_model(self, input_shape: Tuple[int, int]):
        """Build LSTM architecture"""
        model = Sequential([
            # First LSTM layer with dropout
            LSTM(128, return_sequences=True, input_shape=input_shape),
            Dropout(0.2),
            
            # Second LSTM layer
            LSTM(64, return_sequences=True),
            Dropout(0.2),
            
            # Third LSTM layer
            LSTM(32, return_sequences=False),
            Dropout(0.2),
            
            # Dense layers
            Dense(25, activation='relu'),
            Dropout(0.2),
            Dense(1)
        ])
        
        model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss='mse',
            metrics=['mae']
        )
        
        return model
    
    def fit(self, X: Union[np.ndarray, pd.DataFrame], y: Union[np.ndarray, pd.Series]):
        """Train LSTM model"""
        if not TENSORFLOW_AVAILABLE:
            self.logger.error("TensorFlow not available")
            return
            
        self.logger.info("Training LSTM model...")
        
        # Prepare data
        if isinstance(X, pd.DataFrame):
            X_array = X.values
        else:
            X_array = X
            
        # Scale features
        X_scaled = self.scaler.fit_transform(X_array.reshape(-1, X_scaled.shape[-1]))
        X_scaled = X_scaled.reshape(-1, self.sequence_length, X_scaled.shape[-1])
        
        # Reshape y for sequence model
        if isinstance(y, pd.Series):
            y_array = y.values
        else:
            y_array = y
        
        # Build model
        self.model = self._build_model((self.sequence_length, X_scaled.shape[2]))
        
        # Callbacks
        early_stopping = EarlyStopping(
            monitor='val_loss',
            patience=20,
            restore_best_weights=True
        )
        
        reduce_lr = ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=10,
            min_lr=0.0001
        )
        
        # Train model
        history = self.model.fit(
            X_scaled, y_array,
            epochs=100,
            batch_size=32,
            validation_split=0.2,
            callbacks=[early_stopping, reduce_lr],
            verbose=0
        )
        
        # Evaluate
        train_predictions = self.predict(X_scaled)
        self.performance_metrics = self.evaluate(y_array, train_predictions)
        
        self.logger.info(f"LSTM training completed. R²: {self.performance_metrics['r2']:.4f}")
        
    def predict(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        """Make predictions"""
        if not TENSORFLOW_AVAILABLE or self.model is None:
            return np.zeros(len(X))
            
        # Prepare data
        if isinstance(X, pd.DataFrame):
            X_array = X.values
        else:
            X_array = X
            
        # Scale and reshape
        X_scaled = self.scaler.transform(X_array.reshape(-1, X_array.shape[-1]))
        X_scaled = X_scaled.reshape(-1, self.sequence_length, X_scaled.shape[-1])
        
        # Predict
        predictions = self.model.predict(X_scaled, verbose=0)
        return predictions.flatten()

class EnsembleModel(BaseModel):
    """Ensemble model combining multiple algorithms"""
    
    def __init__(self, config, logger=None):
        super().__init__("Ensemble", config, logger)
        
        # Initialize base models
        self.models = {
            'rf': RandomForestModel(config, logger),
            'lgb': LightGBMModel(config, logger),
            'xgb': XGBoostModel(config, logger)
        }
        
        # Add LSTM if available
        if TENSORFLOW_AVAILABLE:
            self.models['lstm'] = LSTMModel(config, logger)
            
        self.weights = {}
        self.scaler = RobustScaler()
        
    def fit(self, X: Union[np.ndarray, pd.DataFrame], y: Union[np.ndarray, pd.Series]):
        """Train ensemble model"""
        self.logger.info("Training Ensemble model...")
        
        # Prepare data
        if isinstance(X, pd.DataFrame):
            X_array = X.values
            feature_names = X.columns.tolist()
        else:
            X_array = X
            feature_names = [f'feature_{i}' for i in range(X.shape[1])]
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X_array)
        
        # Train individual models
        predictions = {}
        for name, model in self.models.items():
            self.logger.info(f"Training {name} component...")
            try:
                if name == 'lstm':
                    # LSTM needs sequence data
                    model.fit(X_array, y)
                else:
                    model.fit(X_scaled, y)
                    
                # Get predictions from this model
                if name == 'lstm':
                    pred = model.predict(X_array)
                else:
                    pred = model.predict(X_scaled)
                    
                predictions[name] = pred
                
                # Store individual model performance
                metrics = model.evaluate(X_scaled if name != 'lstm' else X_array, y.values)
                self.logger.info(f"{name} R²: {metrics['r2']:.4f}")
                
            except Exception as e:
                self.logger.error(f"Failed to train {name}: {e}")
                continue
        
        # Calculate ensemble weights based on performance
        self._calculate_weights(predictions, y.values)
        
        # Create ensemble predictions
        ensemble_pred = self._create_ensemble_prediction(predictions)
        self.performance_metrics = self.evaluate(y.values, ensemble_pred)
        
        self.logger.info(f"Ensemble training completed. R²: {self.performance_metrics['r2']:.4f}")
        self.logger.info(f"Model weights: {self.weights}")
        
    def predict(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        """Make ensemble predictions"""
        if isinstance(X, pd.DataFrame):
            X_array = X.values
        else:
            X_array = X
            
        # Scale features
        X_scaled = self.scaler.transform(X_array)
        
        # Get predictions from all models
        predictions = {}
        for name, model in self.models.items():
            try:
                if name == 'lstm':
                    pred = model.predict(X_array)
                else:
                    pred = model.predict(X_scaled)
                predictions[name] = pred
            except Exception as e:
                self.logger.error(f"Failed to get prediction from {name}: {e}")
                continue
        
        # Create ensemble prediction
        ensemble_pred = self._create_ensemble_prediction(predictions)
        return ensemble_pred
        
    def _calculate_weights(self, predictions: Dict[str, np.ndarray], y_true: np.ndarray):
        """Calculate ensemble weights based on model performance"""
        total_weight = 0
        for name, pred in predictions.items():
            try:
                # Calculate R² score
                r2 = r2_score(y_true, pred)
                # Convert to positive weight (add small constant to avoid zero)
                weight = max(r2 + 1e-6, 0.01)
                self.weights[name] = weight
                total_weight += weight
            except Exception:
                self.weights[name] = 0.01
                total_weight += 0.01
        
        # Normalize weights
        if total_weight > 0:
            for name in self.weights:
                self.weights[name] /= total_weight
        
    def _create_ensemble_prediction(self, predictions: Dict[str, np.ndarray]) -> np.ndarray:
        """Create weighted ensemble prediction"""
        if not predictions:
            return np.zeros(len(list(predictions.values())[0]))
            
        weighted_sum = np.zeros(len(list(predictions.values())[0]))
        total_weight = sum(self.weights.values())
        
        for name, pred in predictions.items():
            weight = self.weights.get(name, 0) / total_weight
            weighted_sum += weight * pred
            
        return weighted_sum
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance from Random Forest model"""
        if 'rf' in self.models:
            return dict(zip(
                self.models['rf'].feature_names,
                self.models['rf'].model.feature_importances_
            ))
        return {}

class ModelFactory:
    """Factory for creating ML models"""
    
    @staticmethod
    def create_model(model_type: str, config, logger=None) -> BaseModel:
        """Create a model instance based on type"""
        
        models = {
            'random_forest': RandomForestModel,
            'lightgbm': LightGBMModel,
            'xgboost': XGBoostModel,
            'lstm': LSTMModel,
            'ensemble': EnsembleModel
        }
        
        if model_type.lower() not in models:
            raise ValueError(f"Unknown model type: {model_type}")
        
        return models[model_type.lower()](config, logger)

if __name__ == "__main__":
    # Test the ML models
    import logging
    logging.basicConfig(level=logging.INFO)
    
    from config.config import config
    
    # Create sample data
    n_samples, n_features = 1000, 50
    np.random.seed(42)
    
    X = np.random.randn(n_samples, n_features)
    y = np.random.randn(n_samples)
    
    # Add some pattern to make it more realistic
    y = 0.5 * X[:, 0] + 0.3 * X[:, 1] + 0.2 * X[:, 2] + np.random.randn(n_samples) * 0.1
    
    X_df = pd.DataFrame(X, columns=[f'feature_{i}' for i in range(n_features)])
    
    # Test different models
    model_types = ['random_forest', 'lightgbm', 'xgboost', 'ensemble']
    
    for model_type in model_types:
        try:
            print(f"\nTesting {model_type}...")
            
            model = ModelFactory.create_model(model_type, config)
            model.fit(X_df, y)
            
            # Test prediction
            predictions = model.predict(X_df[:10])
            print(f"Predictions shape: {predictions.shape}")
            print(f"Sample predictions: {predictions[:5]}")
            
        except Exception as e:
            print(f"Error with {model_type}: {e}")