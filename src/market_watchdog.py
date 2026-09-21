"""
Helios ML Trading System - Market Watchdog
Economic Calendar & News Data Ingestion Module
Fetches free calendar events and news from web sources
"""

import requests
import feedparser
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import time
import json

class MarketWatchdog:
    """Fetches economic calendar and news from free sources"""
    
    def __init__(self, config: dict = None, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.config = config or {}
        
        # Economic calendar URL (ForexFactory free calendar)
        self.calendar_url = "https://www.forexfactory.com/calendar.php"
        
        # News RSS feeds (free)
        self.rss_feeds = [
            "https://feeds.reuters.com/reuters/businessNews",
            "https://feeds.reuters.com/reuters/marketsNews",
            "https://feeds.bbci.co.uk/news/business/rss.xml"
        ]
        
        # Cache for events
        self.events_cache = []
        self.news_cache = []
        self.last_fetch_time = None
        self.cache_duration = 300  # 5 minutes
        
        # High impact event keywords
        self.high_impact_keywords = [
            "nonfarm payrolls", "nfp", "fomc", "federal reserve",
            "interest rate", "inflation", "cpi", "gdp", "unemployment",
            "ecb", "boe", "bank of england", "rate decision",
            "consumer price index", "retail sales", "trade balance"
        ]
        
    def fetch_economic_calendar(self, days_ahead: int = 3) -> List[Dict]:
        """Fetch upcoming economic events"""
        try:
            # Use a simpler approach - parse from ForexFactory RSS
            events = []
            
            # Fetch from multiple sources
            for days in range(days_ahead):
                target_date = datetime.now() + timedelta(days=days)
                date_str = target_date.strftime("%Y-%m-%d")
                
                # Try ForexFactory RSS feed
                rss_url = f"https://www.forexfactory.com/calendar.atom?date={date_str}"
                response = requests.get(rss_url, timeout=10, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                
                if response.status_code == 200:
                    feed = feedparser.parse(response.text)
                    for entry in feed.entries[:20]:  # Limit to 20 events per day
                        event = self._parse_calendar_entry(entry, target_date)
                        if event:
                            events.append(event)
            
            self.events_cache = events
            self.last_fetch_time = datetime.now()
            
            self.logger.info(f"Fetched {len(events)} economic events")
            return events
            
        except Exception as e:
            self.logger.error(f"Error fetching calendar: {e}")
            return self.events_cache  # Return cached if available
    
    def _parse_calendar_entry(self, entry, target_date: datetime) -> Optional[Dict]:
        """Parse a calendar entry into structured format"""
        try:
            title = entry.get('title', '').lower()
            
            # Determine impact level
            impact = "low"
            for keyword in self.high_impact_keywords:
                if keyword in title:
                    impact = "high"
                    break
            
            # Parse time if available
            event_time = target_date.replace(hour=12, minute=0, second=0)  # Default to noon
            
            return {
                "id": entry.get('id', ''),
                "title": entry.get('title', 'Unknown Event'),
                "time": event_time.isoformat(),
                "impact": impact,
                "currency": self._extract_currency(title),
                "source": "forexfactory"
            }
            
        except Exception as e:
            self.logger.warning(f"Error parsing event: {e}")
            return None
    
    def _extract_currency(self, title: str) -> str:
        """Extract currency from event title"""
        currencies = ["USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "CNY", "NZD"]
        title_upper = title.upper()
        
        for curr in currencies:
            if curr in title_upper:
                return curr
        
        return "USD"  # Default
    
    def fetch_news(self, keywords: List[str] = None, max_items: int = 10) -> List[Dict]:
        """Fetch latest news headlines"""
        if keywords is None:
            keywords = ["USD", "EUR", "GBP", "Fed", "ECB", "market", "trade"]
        
        try:
            all_news = []
            
            for feed_url in self.rss_feeds:
                try:
                    response = requests.get(feed_url, timeout=10, headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    })
                    
                    if response.status_code == 200:
                        feed = feedparser.parse(response.text)
                        
                        for entry in feed.entries[:max_items]:
                            # Filter by keywords
                            title = entry.get('title', '').lower()
                            summary = entry.get('summary', '').lower()
                            
                            if any(kw.lower() in title or kw.lower() in summary for kw in keywords):
                                news_item = {
                                    "title": entry.get('title', ''),
                                    "summary": entry.get('summary', '')[:200],
                                    "published": entry.get('published', ''),
                                    "source": feed.feed.get('title', 'Unknown'),
                                    "url": entry.get('link', '')
                                }
                                all_news.append(news_item)
                                
                except Exception as e:
                    self.logger.warning(f"Error fetching {feed_url}: {e}")
                    continue
            
            # Sort by published time and limit
            all_news = sorted(all_news, key=lambda x: x.get('published', ''), reverse=True)
            self.news_cache = all_news[:max_items]
            
            self.logger.info(f"Fetched {len(self.news_cache)} news items")
            return self.news_cache
            
        except Exception as e:
            self.logger.error(f"Error fetching news: {e}")
            return self.news_cache
    
    def get_upcoming_high_impact_events(self, hours_ahead: int = 24) -> List[Dict]:
        """Get high impact events in the next N hours"""
        if not self.events_cache or not self.last_fetch_time:
            self.fetch_economic_calendar()
        
        now = datetime.now()
        cutoff = now + timedelta(hours=hours_ahead)
        
        high_impact = []
        for event in self.events_cache:
            try:
                event_time = datetime.fromisoformat(event['time'])
                if event['impact'] == 'high' and now <= event_time <= cutoff:
                    high_impact.append(event)
            except:
                continue
        
        return high_impact
    
    def is_high_impact_event_imminent(self, minutes: int = 30) -> bool:
        """Check if a high impact event is happening soon"""
        upcoming = self.get_upcoming_high_impact_events(hours_ahead=1)
        
        for event in upcoming:
            try:
                event_time = datetime.fromisoformat(event['time'])
                time_until = (event_time - datetime.now()).total_seconds() / 60
                
                if -15 <= time_until <= minutes:  # During event or shortly before
                    return True
            except:
                continue
        
        return False
    
    def get_status(self) -> Dict:
        """Get current watchdog status"""
        upcoming_events = self.get_upcoming_high_impact_events(hours_ahead=24)
        
        return {
            "status": "active",
            "events_cached": len(self.events_cache),
            "news_cached": len(self.news_cache),
            "last_fetch": self.last_fetch_time.isoformat() if self.last_fetch_time else None,
            "upcoming_high_impact": len(upcoming_events),
            "next_event": upcoming_events[0] if upcoming_events else None
        }


def main():
    """Test the market watchdog"""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    watchdog = MarketWatchdog(logger=logger)
    
    print("=" * 60)
    print("MARKET WATCHDOG TEST")
    print("=" * 60)
    
    # Test calendar fetch
    print("\n📅 Fetching economic calendar...")
    events = watchdog.fetch_economic_calendar(days_ahead=3)
    print(f"✅ Found {len(events)} events")
    
    # Show high impact events
    high_impact = [e for e in events if e['impact'] == 'high']
    print(f"⚡ {len(high_impact)} high impact events found")
    
    for event in high_impact[:5]:
        print(f"  - {event['time'][:10]} | {event['currency']} | {event['title'][:50]}")
    
    # Test news fetch
    print("\n📰 Fetching news...")
    news = watchdog.fetch_news()
    print(f"✅ Found {len(news)} news items")
    
    for item in news[:3]:
        print(f"  - {item['title'][:60]}...")
    
    # Test status
    print("\n📊 Watchdog Status:")
    status = watchdog.get_status()
    print(f"  Events cached: {status['events_cached']}")
    print(f"  News cached: {status['news_cached']}")
    print(f"  High impact upcoming: {status['upcoming_high_impact']}")
    
    print("\n✅ Market Watchdog test complete!")


if __name__ == "__main__":
    main()
