"""
Helios ML Trading System - Neural Sentiment Analysis
Local AI-powered sentiment analysis using Hugging Face transformers
Analyzes news headlines and provides market sentiment scores
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import numpy as np
from collections import deque

class NeuralSentiment:
    """Local sentiment analysis using Hugging Face transformers"""
    
    def __init__(self, config: dict = None, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.config = config or {}
        
        # Sentiment tracking
        self.sentiment_history = deque(maxlen=100)  # Keep last 100 readings
        self.current_sentiment = 0.0
        self.last_update = None
        
        # Model and pipeline
        self.model = None
        self.tokenizer = None
        self.sentiment_pipeline = None
        self.is_loaded = False
        
        # Sentiment weights (recent = more important)
        self.recent_weight = 0.7
        self.older_weight = 0.3
        
    def load_model(self, model_name: str = "ProsusAI/finbert"):
        """Load the sentiment analysis model"""
        try:
            # Try to import transformers
            from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
            import torch
            
            self.logger.info(f"Loading sentiment model: {model_name}")
            
            # Try to load the model
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(model_name)
                self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
                self.sentiment_pipeline = pipeline(
                    "sentiment-analysis",
                    model=self.model,
                    tokenizer=self.tokenizer,
                    device=-1  # CPU
                )
            except Exception as e:
                self.logger.warning(f"FinBERT not available, trying DistilBERT: {e}")
                # Fallback to a simpler model
                self.sentiment_pipeline = pipeline(
                    "sentiment-analysis",
                    model="distilbert-base-uncased-finetuned-sst-2-english",
                    device=-1
                )
            
            self.is_loaded = True
            self.logger.info("✅ Sentiment model loaded successfully")
            return True
            
        except ImportError:
            self.logger.error("transformers library not installed")
            self.logger.info("Install with: uv pip install transformers torch")
            return False
        except Exception as e:
            self.logger.error(f"Error loading sentiment model: {e}")
            return False
    
    def analyze_headline(self, headline: str) -> Dict:
        """Analyze a single headline"""
        if not self.is_loaded:
            return self._get_fallback_sentiment(headline)
        
        try:
            from transformers import pipeline
            
            # Truncate headline if too long
            headline = headline[:512]
            
            # Get sentiment
            result = self.sentiment_pipeline(headline)[0]
            
            # Convert to score (-1 to 1)
            score = result['score']
            if result['label'] == 'NEGATIVE':
                score = -score
            
            return {
                "headline": headline,
                "sentiment": result['label'],
                "score": score,
                "confidence": result['score'],
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.warning(f"Error analyzing headline: {e}")
            return self._get_fallback_sentiment(headline)
    
    def _get_fallback_sentiment(self, headline: str) -> Dict:
        """Fallback sentiment based on keywords when model unavailable"""
        headline_lower = headline.lower()
        
        # Simple keyword-based sentiment
        bullish_keywords = [
            "surge", "rally", "bullish", "gain", "profit", "growth",
            "up", "rise", "higher", "positive", "beat", "exceed"
        ]
        
        bearish_keywords = [
            "crash", "fall", "bearish", "loss", "decline", "drop",
            "down", "lower", "negative", "miss", "below", "fear"
        ]
        
        bullish_count = sum(1 for kw in bullish_keywords if kw in headline_lower)
        bearish_count = sum(1 for kw in bearish_keywords if kw in headline_lower)
        
        if bullish_count > bearish_count:
            score = 0.3
            sentiment = "POSITIVE"
        elif bearish_count > bullish_count:
            score = -0.3
            sentiment = "NEGATIVE"
        else:
            score = 0.0
            sentiment = "NEUTRAL"
        
        return {
            "headline": headline,
            "sentiment": sentiment,
            "score": score,
            "confidence": 0.5,
            "timestamp": datetime.now().isoformat(),
            "fallback": True
        }
    
    def analyze_headlines(self, headlines: List[str]) -> Dict:
        """Analyze multiple headlines and return aggregate sentiment"""
        if not headlines:
            return self._empty_sentiment_result()
        
        results = []
        for headline in headlines:
            result = self.analyze_headline(headline)
            results.append(result)
        
        # Calculate weighted average (more recent = more weight)
        if not results:
            return self._empty_sentiment_result()
        
        # Simple average for now
        avg_score = np.mean([r['score'] for r in results])
        
        # Determine overall sentiment
        if avg_score > 0.2:
            overall = "BULLISH"
        elif avg_score < -0.2:
            overall = "BEARISH"
        else:
            overall = "NEUTRAL"
        
        # Store in history
        sentiment_reading = {
            "score": avg_score,
            "overall": overall,
            "headlines_analyzed": len(headlines),
            "timestamp": datetime.now().isoformat()
        }
        self.sentiment_history.append(sentiment_reading)
        
        # Update current sentiment
        self.current_sentiment = avg_score
        self.last_update = datetime.now()
        
        return {
            "overall_sentiment": overall,
            "sentiment_score": avg_score,
            "headlines_analyzed": len(headlines),
            "individual_results": results,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_market_mood(self, lookback_minutes: int = 60) -> Dict:
        """Get the current market mood based on recent sentiment history"""
        if not self.sentiment_history:
            return {
                "mood": "NEUTRAL",
                "score": 0.0,
                "trend": "stable",
                "readings": 0
            }
        
        # Get readings within lookback period
        cutoff_time = datetime.now() - timedelta(minutes=lookback_minutes)
        recent_readings = [
            r for r in self.sentiment_history
            if datetime.fromisoformat(r['timestamp']) >= cutoff_time
        ]
        
        if not recent_readings:
            # Use all history if no recent readings
            recent_readings = list(self.sentiment_history)
        
        if not recent_readings:
            return self._empty_sentiment_result()
        
        # Calculate mood
        avg_score = np.mean([r['score'] for r in recent_readings])
        
        # Determine trend
        if len(recent_readings) >= 3:
            recent_avg = np.mean([r['score'] for r in recent_readings[-3:]])
            older_avg = np.mean([r['score'] for r in recent_readings[:-3]]) if len(recent_readings) > 3 else recent_avg
            
            if recent_avg > older_avg + 0.1:
                trend = "improving"
            elif recent_avg < older_avg - 0.1:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        # Determine mood
        if avg_score > 0.3:
            mood = "BULLISH"
        elif avg_score < -0.3:
            mood = "BEARISH"
        elif avg_score > 0.1:
            mood = "SLIGHTLY_BULLISH"
        elif avg_score < -0.1:
            mood = "SLIGHTLY_BEARISH"
        else:
            mood = "NEUTRAL"
        
        return {
            "mood": mood,
            "score": avg_score,
            "trend": trend,
            "readings": len(recent_readings),
            "timestamp": datetime.now().isoformat()
        }
    
    def _empty_sentiment_result(self) -> Dict:
        """Return empty sentiment result"""
        return {
            "overall_sentiment": "NEUTRAL",
            "sentiment_score": 0.0,
            "headlines_analyzed": 0,
            "individual_results": [],
            "timestamp": datetime.now().isoformat()
        }
    
    def should_filter_trade(self, ml_signal: str, sentiment_threshold: float = 0.5) -> Dict:
        """
        Determine if a trade should be filtered based on sentiment
        
        Args:
            ml_signal: Signal from ML model (BUY/SELL/HOLD)
            sentiment_threshold: Minimum sentiment score to allow trade
            
        Returns:
            dict with filter decision
        """
        current_mood = self.get_market_mood()
        sentiment_score = abs(current_mood['score'])
        
        # If sentiment is extremely bearish/bullish
        if current_mood['mood'] == "BEARISH" and ml_signal == "BUY":
            return {
                "filter_trade": True,
                "reason": f"Market is BEARISH ({current_mood['score']:.2f}) but signal is BUY",
                "sentiment_score": current_mood['score'],
                "mood": current_mood['mood']
            }
        
        if current_mood['mood'] == "BULLISH" and ml_signal == "SELL":
            return {
                "filter_trade": True,
                "reason": f"Market is BULLISH ({current_mood['score']:.2f}) but signal is SELL",
                "sentiment_score": current_mood['score'],
                "mood": current_mood['mood']
            }
        
        return {
            "filter_trade": False,
            "reason": "Sentiment aligns with trade signal",
            "sentiment_score": current_mood['score'],
            "mood": current_mood['mood']
        }
    
    def get_status(self) -> Dict:
        """Get current sentiment engine status"""
        mood = self.get_market_mood()
        
        return {
            "model_loaded": self.is_loaded,
            "current_sentiment": self.current_sentiment,
            "mood": mood['mood'],
            "score": mood['score'],
            "trend": mood['trend'],
            "history_size": len(self.sentiment_history),
            "last_update": self.last_update.isoformat() if self.last_update else None
        }


def main():
    """Test the sentiment analyzer"""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    print("=" * 60)
    print("NEURAL SENTIMENT TEST")
    print("=" * 60)
    
    sentiment = NeuralSentiment(logger=logger)
    
    # Try to load model
    print("\n🤖 Loading sentiment model...")
    model_loaded = sentiment.load_model()
    
    if not model_loaded:
        print("⚠️  Model not loaded, using keyword fallback")
    
    # Test with sample headlines
    test_headlines = [
        "Fed signals interest rate hike amid inflation concerns",
        "Stock market rallies to new all-time high",
        "Economic data shows unexpected decline in consumer spending",
        "Tech companies report record quarterly profits",
        "Unemployment claims fall more than expected"
    ]
    
    print("\n📰 Analyzing sample headlines...")
    result = sentiment.analyze_headlines(test_headlines)
    
    print(f"\n📊 Results:")
    print(f"  Overall Sentiment: {result['overall_sentiment']}")
    print(f"  Sentiment Score: {result['sentiment_score']:.3f}")
    print(f"  Headlines Analyzed: {result['headlines_analyzed']}")
    
    print("\n🎯 Individual Headlines:")
    for i, r in enumerate(result['individual_results'][:5]):
        print(f"  {i+1}. [{r['sentiment']:8s}] {r['score']:+.2f} - {r['headline'][:50]}...")
    
    # Test market mood
    print("\n� Market Mood (last 60 min):")
    mood = sentiment.get_market_mood()
    print(f"  Mood: {mood['mood']}")
    print(f"  Score: {mood['score']:.3f}")
    print(f"  Trend: {mood['trend']}")
    
    # Test trade filtering
    print("\n🛡️ Trade Filter Test:")
    filter_result = sentiment.should_filter_trade("BUY")
    print(f"  Signal: BUY")
    print(f"  Filter: {filter_result['filter_trade']}")
    print(f"  Reason: {filter_result['reason']}")
    
    # Status
    print("\n📊 Engine Status:")
    status = sentiment.get_status()
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    print("\n✅ Sentiment analysis test complete!")


if __name__ == "__main__":
    main()
