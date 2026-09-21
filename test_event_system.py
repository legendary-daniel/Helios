#!/usr/bin/env python3
"""
Test script for Event-Based Trading System
Tests all new components: MarketWatchdog, NeuralSentiment, RiskGatekeeper
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(Path(__file__).parent))

def test_market_watchdog():
    """Test MarketWatchdog component"""
    print("\n" + "="*60)
    print("TESTING: Market Watchdog")
    print("="*60)
    
    try:
        from market_watchdog import MarketWatchdog
        
        watchdog = MarketWatchdog()
        
        # Test fetching calendar
        print("\n📅 Fetching economic calendar...")
        events = watchdog.fetch_economic_calendar(days_ahead=3)
        print(f"✅ Found {len(events)} events")
        
        # Show high impact events
        high_impact = [e for e in events if e['impact'] == 'high']
        print(f"⚡ {len(high_impact)} high impact events")
        
        for event in high_impact[:3]:
            print(f"  - {event['time'][:10]} | {event['currency']} | {event['title'][:40]}")
        
        # Test fetching news
        print("\n📰 Fetching market news...")
        news = watchdog.fetch_news(max_items=5)
        print(f"✅ Found {len(news)} news items")
        
        # Test status
        status = watchdog.get_status()
        print(f"\n📊 Status: {status['events_cached']} events, {status['news_cached']} news")
        
        print("\n✅ Market Watchdog: PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Market Watchdog: FAILED - {e}")
        return False

def test_sentiment_engine():
    """Test NeuralSentiment component"""
    print("\n" + "="*60)
    print("TESTING: Neural Sentiment Engine")
    print("="*60)
    
    try:
        from neural_sentiment import NeuralSentiment
        
        sentiment = NeuralSentiment()
        
        # Try to load model
        print("\n🤖 Loading sentiment model...")
        loaded = sentiment.load_model()
        if loaded:
            print("✅ Model loaded successfully")
        else:
            print("⚠️  Using keyword fallback")
        
        # Test with sample headlines
        test_headlines = [
            "Fed signals interest rate hike amid inflation concerns",
            "Stock market rallies to new all-time high",
            "Economic data shows unexpected decline",
            "Tech companies report record profits"
        ]
        
        print("\n📰 Analyzing headlines...")
        result = sentiment.analyze_headlines(test_headlines)
        
        print(f"  Overall: {result['overall_sentiment']}")
        print(f"  Score: {result['sentiment_score']:.3f}")
        
        # Test market mood
        mood = sentiment.get_market_mood()
        print(f"\n🎯 Market Mood: {mood['mood']}")
        print(f"  Score: {mood['score']:.3f}")
        print(f"  Trend: {mood['trend']}")
        
        # Test trade filter
        filter_result = sentiment.should_filter_trade("BUY")
        print(f"\n🛡️  Trade Filter Test (BUY signal):")
        print(f"  Filter: {filter_result['filter_trade']}")
        print(f"  Reason: {filter_result['reason']}")
        
        print("\n✅ Neural Sentiment: PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Neural Sentiment: FAILED - {e}")
        return False

def test_risk_gatekeeper():
    """Test RiskGatekeeper component"""
    print("\n" + "="*60)
    print("TESTING: Risk Gatekeeper")
    print("="*60)
    
    try:
        from risk_gatekeeper import RiskGatekeeper
        
        # Initialize (without dependencies for basic test)
        gatekeeper = RiskGatekeeper()
        
        # Test session detection
        print("\n🕐 Current Market Session:")
        current = gatekeeper.get_current_session()
        print(f"  Session: {current.value}")
        
        is_overlap = gatekeeper.is_in_session_overlap()
        print(f"  In Overlap: {is_overlap}")
        
        # Test session times
        print("\n⏰ Trading Sessions:")
        sessions = gatekeeper.get_session_times()
        for name, info in sessions.items():
            active = " ✅" if info['is_active'] else ""
            print(f"  {name:12s}: {info['start']} - {info['end']}{active}")
        
        # Test risk checks (without dependencies)
        print("\n📊 Risk Checks:")
        session_check = gatekeeper.check_session_risk()
        print(f"  Session Risk: {session_check['has_risk']} - {session_check['reason']}")
        
        event_check = gatekeeper.check_event_risk()
        print(f"  Event Risk: {event_check['has_risk']} - {event_check['reason']}")
        
        # Test overall decision
        print("\n🎯 Trade Decision:")
        decision = gatekeeper.get_trade_decision()
        print(f"  Decision: {decision.decision}")
        print(f"  Can Trade: {decision.can_trade}")
        print(f"  Reason: {decision.reason}")
        print(f"  Volatility: {decision.volatility_level}")
        
        print("\n✅ Risk Gatekeeper: PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Risk Gatekeeper: FAILED - {e}")
        return False

def test_integration():
    """Test full integration"""
    print("\n" + "="*60)
    print("TESTING: Full Integration")
    print("="*60)
    
    try:
        from market_watchdog import MarketWatchdog
        from neural_sentiment import NeuralSentiment
        from risk_gatekeeper import RiskGatekeeper
        
        # Initialize components
        print("\n🔧 Initializing components...")
        watchdog = MarketWatchdog()
        sentiment = NeuralSentiment()
        gatekeeper = RiskGatekeeper()
        
        # Integrate
        print("🔗 Integrating components...")
        gatekeeper.integrate_with_system(watchdog, sentiment)
        
        # Get full status
        print("\n📊 Full System Status:")
        status = gatekeeper.get_trade_decision()
        
        print(f"  Can Trade: {status.can_trade}")
        print(f"  Decision: {status.decision}")
        print(f"  Session: {status.market_session}")
        print(f"  Sentiment: {status.sentiment_mood} ({status.sentiment_score:.2f})")
        print(f"  Volatility: {status.volatility_level}")
        
        # Test JSON output
        print("\n📋 JSON Status:")
        json_status = gatekeeper.get_trade_status_json()
        print(f"  can_trade: {json_status['can_trade']}")
        print(f"  decision: {json_status['decision']}")
        print(f"  volatility_level: {json_status['volatility_level']}")
        
        print("\n✅ Integration Test: PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Integration Test: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("="*60)
    print("HELIOS EVENT-BASED TRADING SYSTEM - TEST SUITE")
    print("="*60)
    
    results = []
    
    # Run tests
    results.append(("Market Watchdog", test_market_watchdog()))
    results.append(("Neural Sentiment", test_sentiment_engine()))
    results.append(("Risk Gatekeeper", test_risk_gatekeeper()))
    results.append(("Integration", test_integration()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST RESULTS SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {name:20s}: {status}")
    
    print(f"\n📊 Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Event-based trading system is ready.")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please check errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
