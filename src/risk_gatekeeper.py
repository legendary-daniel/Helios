"""
Helios ML Trading System - Risk Gatekeeper
The core decision engine that integrates events, sentiment, and market sessions
Determines whether trading is allowed based on multiple risk factors
"""

import logging
from datetime import datetime, time
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

class TradeDecision(Enum):
    """Trading decision outcomes"""
    ALLOW = "allow"
    BLOCK = "block"
    CAUTION = "caution"

class MarketSession(Enum):
    """Major trading sessions"""
    SYDNEY = "sydney"
    TOKYO = "tokyo"
    LONDON = "london"
    NEW_YORK = "new_york"
    OFF_PEAK = "off_peak"

@dataclass
class TradeStatus:
    """Current trading status"""
    can_trade: bool
    decision: str
    reason: str
    confidence: float
    market_session: str
    sentiment_score: float
    sentiment_mood: str
    upcoming_events: int
    next_event: Optional[Dict]
    volatility_level: str

class RiskGatekeeper:
    """
    Central decision engine for event-driven trading
    Integrates market sessions, economic events, and sentiment analysis
    """
    
    def __init__(self, config: dict = None, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.config = config or {}
        
        # Risk parameters
        self.event_block_minutes_before = self.config.get('event_block_minutes_before', 30)
        self.event_block_minutes_after = self.config.get('event_block_minutes_after', 15)
        self.min_sentiment_confidence = self.config.get('min_sentiment_confidence', 0.3)
        self.enable_session_filter = self.config.get('enable_session_filter', True)
        self.enable_event_filter = self.config.get('enable_event_filter', True)
        self.enable_sentiment_filter = self.config.get('enable_sentiment_filter', False)
        
        # Allowed trading sessions (default: high liquidity sessions)
        self.allowed_sessions = [
            MarketSession.LONDON,
            MarketSession.NEW_YORK,
            MarketSession.TOKYO
        ]
        
        # Session overlaps (highest liquidity)
        self.session_overlaps = [
            (MarketSession.LONDON, MarketSession.NEW_YORK),  # 13:00-16:00 UTC
            (MarketSession.TOKYO, MarketSession.LONDON),      # 08:00-09:00 UTC
        ]
        
        # Session time ranges (UTC)
        self.session_times = {
            MarketSession.SYDNEY: (time(22, 0), time(7, 0)),
            MarketSession.TOKYO: (time(0, 0), time(6, 0)),
            MarketSession.LONDON: (time(7, 0), time(16, 0)),
            MarketSession.NEW_YORK: (time(13, 0), time(21, 0)),
        }
        
        # Components (will be set by integrate_with_system)
        self.market_watchdog = None
        self.sentiment_engine = None
        
    def integrate_with_system(self, market_watchdog, sentiment_engine):
        """Integrate with other system components"""
        self.market_watchdog = market_watchdog
        self.sentiment_engine = sentiment_engine
        self.logger.info("RiskGatekeeper integrated with system components")
    
    def get_current_session(self) -> MarketSession:
        """Get the current market session"""
        current_time = datetime.utcnow().time()
        
        for session, (start, end) in self.session_times.items():
            if start <= current_time <= end:
                return session
            # Handle overnight sessions
            if start > end:  # Sydney wraps around midnight
                if current_time >= start or current_time <= end:
                    return session
        
        return MarketSession.OFF_PEAK
    
    def is_in_session_overlap(self) -> bool:
        """Check if currently in a high-liquidity session overlap"""
        current_session = self.get_current_session()
        
        for session1, session2 in self.session_overlaps:
            if current_session in [session1, session2]:
                # Check if we're in the actual overlap time
                current_hour = datetime.utcnow().hour
                
                # London-NY overlap: 13:00-16:00 UTC
                if session1 == MarketSession.LONDON and session2 == MarketSession.NEW_YORK:
                    if 13 <= current_hour < 16:
                        return True
                
                # Tokyo-London overlap: 08:00-09:00 UTC
                if session1 == MarketSession.TOKYO and session2 == MarketSession.LONDON:
                    if 8 <= current_hour < 9:
                        return True
        
        return False
    
    def check_event_risk(self) -> Dict:
        """Check if high-impact events are imminent"""
        if not self.market_watchdog:
            return {"has_risk": False, "reason": "No watchdog"}
        
        try:
            # Get events in the next hour
            upcoming = self.market_watchdog.get_upcoming_high_impact_events(hours_ahead=1)
            
            if not upcoming:
                return {
                    "has_risk": False,
                    "reason": "No upcoming high-impact events"
                }
            
            # Check each event
            for event in upcoming:
                event_time = datetime.fromisoformat(event['time'])
                time_until = (event_time - datetime.now()).total_seconds() / 60
                
                # During event or too close
                if -self.event_block_minutes_after <= time_until <= self.event_block_minutes_before:
                    return {
                        "has_risk": True,
                        "reason": f"High-impact event: {event['title']}",
                        "event": event,
                        "minutes_until": int(time_until)
                    }
            
            return {
                "has_risk": False,
                "reason": "No immediate high-impact events"
            }
            
        except Exception as e:
            self.logger.warning(f"Error checking event risk: {e}")
            return {"has_risk": False, "reason": "Error checking events"}
    
    def check_sentiment_risk(self, ml_signal: str = None) -> Dict:
        """Check sentiment-based risk"""
        if not self.sentiment_engine:
            return {"has_risk": False, "reason": "No sentiment engine"}
        
        try:
            mood = self.sentiment_engine.get_market_mood()
            
            # If sentiment is too extreme
            if abs(mood['score']) > 0.7:
                return {
                    "has_risk": True,
                    "reason": f"Extreme sentiment: {mood['mood']}",
                    "mood": mood
                }
            
            # If ML signal contradicts sentiment (optional filter)
            if ml_signal and self.enable_sentiment_filter:
                filter_result = self.sentiment_engine.should_filter_trade(ml_signal)
                if filter_result['filter_trade']:
                    return {
                        "has_risk": True,
                        "reason": filter_result['reason'],
                        "mood": mood
                    }
            
            return {
                "has_risk": False,
                "reason": "Sentiment acceptable",
                "mood": mood
            }
            
        except Exception as e:
            self.logger.warning(f"Error checking sentiment risk: {e}")
            return {"has_risk": False, "reason": "Error checking sentiment"}
    
    def check_session_risk(self) -> Dict:
        """Check if current session is suitable for trading"""
        if not self.enable_session_filter:
            return {"has_risk": False, "reason": "Session filter disabled"}
        
        current_session = self.get_current_session()
        
        # Check if in allowed session
        if current_session not in self.allowed_sessions:
            return {
                "has_risk": True,
                "reason": f"Off-peak session: {current_session.value}",
                "session": current_session.value
            }
        
        # Check for overlap (positive!)
        if self.is_in_session_overlap():
            return {
                "has_risk": False,
                "reason": "High-liquidity session overlap",
                "session": current_session.value,
                "overlap": True
            }
        
        return {
            "has_risk": False,
            "reason": f"Active trading session: {current_session.value}",
            "session": current_session.value
        }
    
    def get_trade_decision(self, ml_signal: str = None) -> TradeStatus:
        """
        Get the comprehensive trade decision based on all risk factors
        
        Args:
            ml_signal: Optional ML signal (BUY/SELL) for sentiment filtering
            
        Returns:
            TradeStatus with decision and details
        """
        reasons = []
        risk_level = "low"
        
        # Check session
        session_check = self.check_session_risk()
        if session_check['has_risk']:
            reasons.append(f"Session: {session_check['reason']}")
            risk_level = "medium"
        
        # Check events
        event_check = self.check_event_risk()
        if event_check['has_risk']:
            reasons.append(f"Event: {event_check['reason']}")
            risk_level = "high"
        
        # Check sentiment
        sentiment_check = self.check_sentiment_risk(ml_signal)
        if sentiment_check['has_risk']:
            reasons.append(f"Sentiment: {sentiment_check['reason']}")
            if risk_level == "low":
                risk_level = "medium"
        
        # Determine overall decision
        if risk_level == "high":
            decision = TradeDecision.BLOCK
            can_trade = False
            confidence = 0.9
        elif risk_level == "medium":
            decision = TradeDecision.CAUTION
            can_trade = True  # Allow but with caution
            confidence = 0.6
        else:
            decision = TradeDecision.ALLOW
            can_trade = True
            confidence = 0.85
        
        # Get sentiment data
        sentiment_score = 0.0
        sentiment_mood = "NEUTRAL"
        if self.sentiment_engine:
            try:
                mood = self.sentiment_engine.get_market_mood()
                sentiment_score = mood['score']
                sentiment_mood = mood['mood']
            except:
                pass
        
        # Get event data
        upcoming_events = 0
        next_event = None
        if self.market_watchdog:
            try:
                events = self.market_watchdog.get_upcoming_high_impact_events(hours_ahead=24)
                upcoming_events = len(events)
                next_event = events[0] if events else None
            except:
                pass
        
        return TradeStatus(
            can_trade=can_trade,
            decision=decision.value,
            reason="; ".join(reasons) if reasons else "All clear for trading",
            confidence=confidence,
            market_session=self.get_current_session().value,
            sentiment_score=sentiment_score,
            sentiment_mood=sentiment_mood,
            upcoming_events=upcoming_events,
            next_event=next_event,
            volatility_level=risk_level
        )
    
    def get_trade_status_json(self, ml_signal: str = None) -> Dict:
        """Get trade status as JSON for API endpoint"""
        status = self.get_trade_decision(ml_signal)
        
        return {
            "can_trade": status.can_trade,
            "decision": status.decision,
            "reason": status.reason,
            "confidence": status.confidence,
            "market_session": status.market_session,
            "in_overlap": self.is_in_session_overlap(),
            "sentiment": {
                "score": status.sentiment_score,
                "mood": status.sentiment_mood
            },
            "events": {
                "upcoming_24h": status.upcoming_events,
                "next_event": status.next_event
            },
            "volatility_level": status.volatility_level,
            "timestamp": datetime.now().isoformat()
        }
    
    def should_close_positions(self) -> Dict:
        """Determine if existing positions should be closed due to risk"""
        status = self.get_trade_decision()
        
        # If risk is high, recommend closing positions
        if status.decision == TradeDecision.BLOCK.value:
            return {
                "should_close": True,
                "reason": f"High risk: {status.reason}",
                "volatility": status.volatility_level
            }
        
        return {
            "should_close": False,
            "reason": "Risk levels acceptable",
            "volatility": status.volatility_level
        }
    
    def get_session_times(self) -> Dict:
        """Get formatted session times for display"""
        sessions = {}
        for session, (start, end) in self.session_times.items():
            current = self.get_current_session()
            is_active = session == current
            
            sessions[session.value] = {
                "start": start.strftime("%H:%M UTC"),
                "end": end.strftime("%H:%M UTC"),
                "is_active": is_active,
                "is_overlap": self.is_in_session_overlap() and is_active
            }
        
        return sessions
    
    def get_status(self) -> Dict:
        """Get gatekeeper status"""
        status = self.get_trade_decision()
        
        return {
            "decision": status.decision,
            "can_trade": status.can_trade,
            "current_session": status.market_session,
            "in_overlap": self.is_in_session_overlap(),
            "risk_level": status.volatility_level,
            "sentiment": {
                "score": status.sentiment_score,
                "mood": status.sentiment_mood
            },
            "upcoming_events": status.upcoming_events,
            "event_filter_enabled": self.enable_event_filter,
            "session_filter_enabled": self.enable_session_filter,
            "sentiment_filter_enabled": self.enable_sentiment_filter
        }


def main():
    """Test the risk gatekeeper"""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    print("=" * 60)
    print("RISK GATEKEEPER TEST")
    print("=" * 60)
    
    # Initialize
    config = {
        'event_block_minutes_before': 30,
        'event_block_minutes_after': 15,
        'enable_session_filter': True,
        'enable_event_filter': True,
        'enable_sentiment_filter': False
    }
    
    gatekeeper = RiskGatekeeper(config=config, logger=logger)
    
    # Test session detection
    print("\n🕐 Current Market Session:")
    current = gatekeeper.get_current_session()
    print(f"  Session: {current.value}")
    
    is_overlap = gatekeeper.is_in_session_overlap()
    print(f"  In Overlap: {is_overlap}")
    
    # Test event risk (without watchdog - will return safe)
    print("\n📅 Event Risk Check:")
    event_check = gatekeeper.check_event_risk()
    print(f"  Has Risk: {event_check['has_risk']}")
    print(f"  Reason: {event_check['reason']}")
    
    # Test session risk
    print("\n⏰ Session Risk Check:")
    session_check = gatekeeper.check_session_risk()
    print(f"  Has Risk: {session_check['has_risk']}")
    print(f"  Reason: {session_check['reason']}")
    
    # Test overall decision
    print("\n🎯 Trade Decision:")
    decision = gatekeeper.get_trade_decision()
    print(f"  Decision: {decision.decision}")
    print(f"  Can Trade: {decision.can_trade}")
    print(f"  Reason: {decision.reason}")
    print(f"  Confidence: {decision.confidence}")
    print(f"  Volatility: {decision.volatility_level}")
    
    # Test JSON output
    print("\n📊 JSON Status:")
    json_status = gatekeeper.get_trade_status_json()
    for key, value in json_status.items():
        if key != 'events':
            print(f"  {key}: {value}")
    
    # Test session times
    print("\n🕐 Session Times:")
    sessions = gatekeeper.get_session_times()
    for name, info in sessions.items():
        active = " ✅ ACTIVE" if info['is_active'] else ""
        print(f"  {name:12s}: {info['start']} - {info['end']}{active}")
    
    # Test position closure
    print("\n🛡️ Position Closure Check:")
    close_check = gatekeeper.should_close_positions()
    print(f"  Should Close: {close_check['should_close']}")
    print(f"  Reason: {close_check['reason']}")
    
    # Status
    print("\n📊 Gatekeeper Status:")
    status = gatekeeper.get_status()
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    print("\n✅ Risk Gatekeeper test complete!")


if __name__ == "__main__":
    main()
