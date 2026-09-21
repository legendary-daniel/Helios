# Helios ML Trading System - Event-Based Trading Enhancement

## Overview

The Helios ML Trading System has been enhanced with **event-based trading capabilities** using FREE data sources. The system now monitors global economic events, analyzes market sentiment, and makes intelligent trading decisions based on market conditions.

## New Components

### 1. Market Watchdog (`src/market_watchdog.py`)
**Purpose:** Fetches economic calendar and news from free sources

**Features:**
- Economic calendar from ForexFactory (free RSS feed)
- News aggregation from Reuters, BBC (free RSS feeds)
- High-impact event detection (NFP, FOMC, interest rates, etc.)
- Automatic caching with 5-minute refresh
- Currency extraction from event titles

**Cost:** $0 (completely free)

### 2. Neural Sentiment (`src/neural_sentiment.py`)
**Purpose:** AI-powered sentiment analysis using local models

**Features:**
- Uses Hugging Face transformers (local, no API costs)
- Falls back to keyword-based analysis if model unavailable
- Tracks sentiment history (last 100 readings)
- Market mood calculation (Bullish/Bearish/Neutral)
- Trade filtering based on sentiment

**Cost:** $0 (local compute, free models)

**Model Options:**
- Primary: ProsusAI/finbert (financial sentiment)
- Fallback: distilbert-base-uncased-finetuned-sst-2-english

### 3. Risk Gatekeeper (`src/risk_gatekeeper.py`)
**Purpose:** Central decision engine integrating all risk factors

**Features:**
- Market session detection (Sydney, Tokyo, London, NY)
- High-liquidity overlap detection
- Event risk assessment (blocks trading during high-impact events)
- Sentiment-based trade filtering
- Comprehensive trade decision logic

**Risk Levels:**
- HIGH: Block all trading
- MEDIUM: Allow with caution
- LOW: Normal trading

## New API Endpoints

| Endpoint | Description |
|----------|-------------|
| `/api/v1/trade_status` | Get current trade decision (can_trade, reason, confidence) |
| `/api/v1/events` | Get upcoming high-impact economic events |
| `/api/v1/news` | Get latest market news with sentiment |
| `/api/v1/sentiment` | Get current market sentiment score |
| `/api/v1/sessions` | Get current market session status |
| `/api/v1/risk_analysis` | Comprehensive risk analysis |
| `/api/v1/event_status` | Event system status |

## How It Works

### Trading Decision Flow

```
1. ML Signal Generated (BUY/SELL)
   ↓
2. Check Market Session
   - Is it in allowed session? (London, NY, Tokyo)
   - Is it in high-liquidity overlap?
   ↓
3. Check Economic Events
   - Any high-impact events in next 30 minutes?
   - During event or 15 minutes after?
   ↓
4. Check Market Sentiment
   - Does sentiment contradict signal?
   - Is sentiment extreme?
   ↓
5. Final Decision
   - HIGH RISK → Block trading
   - MEDIUM RISK → Allow with caution
   - LOW RISK → Allow trading
```

### Example Trade Decision

```json
{
  "can_trade": false,
  "decision": "block",
  "reason": "Event: High-impact event: Non-Farm Payrolls",
  "confidence": 0.9,
  "market_session": "new_york",
  "in_overlap": false,
  "sentiment": {
    "score": -0.45,
    "mood": "BEARISH"
  },
  "events": {
    "upcoming_24h": 3,
    "next_event": {
      "title": "Non-Farm Payrolls",
      "time": "2026-02-17T13:30:00",
      "impact": "high"
    }
  },
  "volatility_level": "high"
}
```

## Market Sessions (UTC)

| Session | Start | End | Overlap |
|---------|-------|-----|---------|
| Sydney | 22:00 | 07:00 | No |
| Tokyo | 00:00 | 06:00 | With London (08:00-09:00) |
| London | 07:00 | 16:00 | With NY (13:00-16:00) |
| New York | 13:00 | 21:00 | With London (13:00-16:00) |

**Best Trading Times:**
- London-NY Overlap: 13:00-16:00 UTC (highest liquidity)
- Tokyo-London Overlap: 08:00-09:00 UTC

## Risk Rules

### Event-Based Risk
- Block new trades 30 minutes BEFORE high-impact events
- Block new trades 15 minutes AFTER high-impact events
- High-impact events: NFP, FOMC, interest rate decisions, CPI, GDP

### Session-Based Risk
- Only trade during active sessions (Tokyo, London, NY)
- Prefer overlap periods for higher liquidity

### Sentiment-Based Risk (Optional)
- Filter trades that contradict extreme sentiment
- Example: Market strongly Bearish + ML signal BUY → Block

## Installation

### Install Dependencies

```bash
# Install required packages
uv pip install beautifulsoup4 feedparser transformers torch

# For macOS - install libomp for LightGBM (if needed)
brew install libomp
```

### Test the System

```bash
# Test event-based trading components
python test_event_system.py

# Start the server
python src/helios_server.py
```

### Test the API

```bash
# Get trade status
curl http://localhost:8765/api/v1/trade_status

# Get upcoming events
curl "http://localhost:8765/api/v1/events?hours=24"

# Get market sentiment
curl http://localhost:8765/api/v1/sentiment

# Get session status
curl http://localhost:8765/api/v1/sessions
```

## Configuration

### Risk Gatekeeper Options

Edit in `helios_server.py`:

```python
risk_gatekeeper = RiskGatekeeper(
    config={
        'event_block_minutes_before': 30,    # Block 30 min before events
        'event_block_minutes_after': 15,      # Block 15 min after events
        'enable_session_filter': True,        # Enable session filtering
        'enable_event_filter': True,           # Enable event filtering
        'enable_sentiment_filter': False       # Enable sentiment filtering
    },
    logger=logger
)
```

## MT5 EA Integration

The EA can query the trade status endpoint to determine if trading is allowed:

```mql5
// In EA - check before trading
string status = SendHTTPRequest("http://localhost:8765/api/v1/trade_status");
// Parse JSON and check can_trade field
```

## Dashboard

The new event-based features will appear in the dashboard under the "Macro" section showing:
- Current market session
- Upcoming high-impact events
- Market sentiment gauge
- Trade decision status

## Cost Summary

| Component | Cost |
|-----------|------|
| Economic Calendar | $0 (ForexFactory RSS) |
| News Feeds | $0 (Reuters, BBC RSS) |
| Sentiment Analysis | $0 (Local Hugging Face) |
| Server Hosting | $0 (Your computer) |
| **Total** | **$0** |

## Limitations

1. **Data Delay:** RSS feeds may have 5-15 minute delays
2. **No Real-Time:** Not suitable for high-frequency trading
3. **Basic Sentiment:** Keyword fallback is simple (not AI-powered)
4. **Internet Required:** Needs internet for calendar/news

## Future Enhancements (Paid)

- Real-time data feeds ($20-100/month)
- Professional sentiment API ($50/month)
- Bloomberg/Reuters terminals ($15,000+/year)

## Support

For issues or questions:
1. Check logs in `logs/helios_server.log`
2. Run `python test_event_system.py` for diagnostics
3. Test individual endpoints with curl

---

**Status:** ✅ Event-Based Trading System Ready
**Cost:** $0 (Free)
**Complexity:** Medium
**Risk Protection:** High
