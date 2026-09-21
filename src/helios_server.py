#!/usr/bin/env python3
"""
Helios ML Trading System - Main Server
FastAPI server with WebSocket support for MT5 integration
"""

import asyncio
import logging
import signal
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
import json
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pandas as pd
from datetime import datetime, timedelta
import time

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))
sys.path.append(str(Path(__file__).parent))

# Import Helios components
try:
    from config.config import config
    from helios_system import HeliosTradingSystem
except ImportError as e:
    print(f"Error importing Helios components: {e}")
    print("Make sure all dependencies are installed and paths are correct")
    sys.exit(1)

# Import Event-Based Trading Components
try:
    from market_watchdog import MarketWatchdog
    from neural_sentiment import NeuralSentiment
    from risk_gatekeeper import RiskGatekeeper
except ImportError as e:
    print(f"Warning: Event-based trading modules not loaded: {e}")
    MarketWatchdog = None
    NeuralSentiment = None
    RiskGatekeeper = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/helios_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# FastAPI app initialization
app = FastAPI(
    title="Helios ML Trading System API",
    description="Professional Machine Learning Trading System",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
trading_system: Optional[HeliosTradingSystem] = None
active_connections: List[WebSocket] = []
connected_mt5_clients: Dict[str, WebSocket] = {}

# Event-Based Trading Components
market_watchdog: Optional[MarketWatchdog] = None
sentiment_engine: Optional[NeuralSentiment] = None
risk_gatekeeper: Optional[RiskGatekeeper] = None

# Startup initialization flag
event_system_initialized = False

# FastAPI WebSocket endpoint
@app.websocket("/ws/mt5")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for MT5 Expert Advisor communication"""
    await websocket.accept()
    client_id = f"mt5_client_{int(time.time())}"
    active_connections.append(websocket)
    connected_mt5_clients[client_id] = websocket
    
    logger.info(f"MT5 client connected: {client_id}")
    
    try:
        while True:
            # Receive message from MT5
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Process message
            await handle_mt5_message(client_id, message, websocket)
            
    except WebSocketDisconnect:
        logger.info(f"MT5 client disconnected: {client_id}")
    except Exception as e:
        logger.error(f"Error handling MT5 message: {e}")
    finally:
        # Cleanup
        if websocket in active_connections:
            active_connections.remove(websocket)
        if client_id in connected_mt5_clients:
            del connected_mt5_clients[client_id]

# REST API Endpoints
@app.get("/")
async def root():
    """Root endpoint with system status"""
    return {
        "service": "Helios ML Trading System",
        "version": "1.0.0",
        "status": "running" if trading_system and trading_system.is_running else "stopped",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "websocket": "/ws/mt5",
            "health": "/health",
            "status": "/api/status",
            "signals": "/api/signals",
            "strategies": "/api/strategies",
            "performance": "/api/performance",
            # Event-Based Trading Endpoints
            "trade_status": "/api/v1/trade_status",
            "events": "/api/v1/events",
            "news": "/api/v1/news",
            "sentiment": "/api/v1/sentiment",
            "sessions": "/api/v1/sessions",
            "risk_analysis": "/api/v1/risk_analysis",
            "event_status": "/api/v1/event_status"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "trading_system_running": trading_system.is_running if trading_system else False,
        "active_connections": len(active_connections),
        "mt5_clients": len(connected_mt5_clients),
        "memory_usage": get_memory_usage(),
        "uptime": get_uptime()
    }
    
    return JSONResponse(status)

@app.get("/api/status")
async def get_system_status():
    """Get comprehensive system status"""
    if not trading_system:
        raise HTTPException(status_code=503, detail="Trading system not initialized")
    
    return trading_system.get_system_status()

@app.get("/api/signals")
async def get_recent_signals():
    """Get recent trading signals"""
    if not trading_system:
        raise HTTPException(status_code=503, detail="Trading system not initialized")
    
    return {
        "signals": trading_system.signals_history[-50:],  # Last 50 signals
        "total": len(trading_system.signals_history)
    }

@app.get("/api/strategies")
async def get_strategies_status():
    """Get trading strategies status"""
    if not trading_system:
        raise HTTPException(status_code=503, detail="Trading system not initialized")
    
    return trading_system.strategy_manager.get_strategy_status()

@app.get("/api/performance")
async def get_performance_metrics():
    """Get performance metrics"""
    if not trading_system:
        raise HTTPException(status_code=503, detail="Trading system not initialized")
    
    metrics = trading_system.get_system_status()
    metrics.update({
        "ml_models_loaded": len(trading_system.ml_models),
        "market_data_symbols": len(trading_system.market_data_cache),
        "processed_data_cache_size": len(trading_system.processed_data_cache),
        "last_training_time": trading_system.last_training_time.isoformat() if trading_system.last_training_time else None
    })
    
    return metrics

@app.post("/api/start-trading")
async def start_trading():
    """Start the trading system"""
    global trading_system
    
    if trading_system and trading_system.is_running:
        return {"status": "already_running", "message": "Trading system is already running"}
    
    try:
        # Initialize trading system if not already initialized
        if not trading_system:
            trading_system = HeliosTradingSystem()
            await trading_system.initialize()
        
        # Start trading in background
        asyncio.create_task(trading_system.start_trading())
        
        return {"status": "started", "message": "Trading system started successfully"}
        
    except Exception as e:
        logger.error(f"Error starting trading system: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/stop-trading")
async def stop_trading():
    """Stop the trading system"""
    if not trading_system or not trading_system.is_running:
        return {"status": "already_stopped", "message": "Trading system is not running"}
    
    try:
        await trading_system.stop_trading()
        return {"status": "stopped", "message": "Trading system stopped successfully"}
        
    except Exception as e:
        logger.error(f"Error stopping trading system: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/signal")
async def manual_signal(signal_data: Dict[str, Any]):
    """Submit manual trading signal"""
    if not trading_system:
        raise HTTPException(status_code=503, detail="Trading system not initialized")
    
    try:
        # Process manual signal
        # This would integrate with the trading system
        logger.info(f"Manual signal received: {signal_data}")
        
        return {
            "status": "received",
            "message": "Signal received and will be processed",
            "signal_id": f"manual_{int(time.time())}"
        }
        
    except Exception as e:
        logger.error(f"Error processing manual signal: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Helper functions
async def handle_mt5_message(client_id: str, message: Dict[str, Any], websocket: WebSocket):
    """Handle incoming messages from MT5"""
    
    message_type = message.get("type", "")
    
    try:
        if message_type == "heartbeat":
            # Respond to heartbeat
            await send_to_client(client_id, {
                "type": "heartbeat_response",
                "timestamp": datetime.now().isoformat(),
                "system_status": "running" if trading_system and trading_system.is_running else "stopped"
            })
            
        elif message_type == "trade_signal":
            # Process trading signal from EA
            await process_trading_signal_from_ea(message.get("data", {}))
            
        elif message_type == "status_request":
            # Send system status
            status = get_system_status_for_mt5()
            await send_to_client(client_id, {
                "type": "status_response",
                "data": status
            })
            
        elif message_type == "position_update":
            # Update position information
            await process_position_update(message.get("data", {}))
            
        elif message_type == "trade_result":
            # Process trade execution result
            await process_trade_result(message.get("data", {}))
            
        else:
            logger.warning(f"Unknown message type from MT5: {message_type}")
            
    except Exception as e:
        logger.error(f"Error handling MT5 message: {e}")
        await send_error_to_client(client_id, f"Error processing message: {str(e)}")

async def process_trading_signal_from_ea(signal_data: Dict[str, Any]):
    """Process trading signal received from MT5 Expert Advisor"""
    
    if not trading_system:
        logger.warning("Trading system not available to process signal")
        return
    
    try:
        # Convert EA signal to internal format
        internal_signal = {
            "symbol": signal_data.get("symbol", ""),
            "signal_type": signal_data.get("signal_type", "hold"),
            "confidence": signal_data.get("confidence", 0.5),
            "price": signal_data.get("price", 0.0),
            "stop_loss": signal_data.get("stop_loss", 0.0),
            "take_profit": signal_data.get("take_profit", 0.0),
            "position_size": signal_data.get("position_size", 0.0),
            "strategy": signal_data.get("strategy", "manual"),
            "timestamp": datetime.now().isoformat()
        }
        
        # Add to signals history
        trading_system.signals_history.append(internal_signal)
        
        # Log signal
        logger.info(f"Trading signal from EA: {internal_signal}")
        
        # If this is a high-confidence signal, could trigger additional processing
        if internal_signal["confidence"] > 0.8:
            logger.info(f"High-confidence signal received: {internal_signal['confidence']}")
        
    except Exception as e:
        logger.error(f"Error processing EA signal: {e}")

async def process_position_update(position_data: Dict[str, Any]):
    """Process position update from MT5"""
    
    if not trading_system:
        return
    
    try:
        # Update internal position tracking
        logger.info(f"Position update from MT5: {position_data}")
        
        # Could integrate with meta-learning system for performance tracking
        
    except Exception as e:
        logger.error(f"Error processing position update: {e}")

async def process_trade_result(trade_data: Dict[str, Any]):
    """Process trade execution result from MT5"""
    
    if not trading_system:
        return
    
    try:
        # Update trading statistics
        if trade_data.get("success", False):
            trading_system.successful_trades += 1
        trading_system.total_trades += 1
        
        # Log trade result
        logger.info(f"Trade result from MT5: {trade_data}")
        
        # Update strategy performance if available
        strategy_name = trade_data.get("strategy", "unknown")
        if strategy_name in trading_system.strategy_manager.strategies:
            # Update strategy performance tracking
            was_correct = trade_data.get("profit", 0) > 0
            trading_system.strategy_manager.update_performance(strategy_name, was_correct)
        
        # Notify all connected clients about the trade result
        await broadcast_to_all_clients({
            "type": "trade_result",
            "data": trade_data
        })
        
    except Exception as e:
        logger.error(f"Error processing trade result: {e}")

async def send_to_client(client_id: str, message: Dict[str, Any]):
    """Send message to specific MT5 client"""
    
    if client_id in connected_mt5_clients:
        websocket = connected_mt5_clients[client_id]
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending message to client {client_id}: {e}")

async def send_error_to_client(client_id: str, error_message: str):
    """Send error message to client"""
    await send_to_client(client_id, {
        "type": "error",
        "message": error_message,
        "timestamp": datetime.now().isoformat()
    })

async def broadcast_to_all_clients(message: Dict[str, Any]):
    """Broadcast message to all connected clients"""
    
    message_text = json.dumps(message)
    disconnected_clients = []
    
    for client_id, websocket in connected_mt5_clients.items():
        try:
            await websocket.send_text(message_text)
        except Exception as e:
            logger.error(f"Error broadcasting to client {client_id}: {e}")
            disconnected_clients.append(client_id)
    
    # Remove disconnected clients
    for client_id in disconnected_clients:
        del connected_mt5_clients[client_id]

def get_system_status_for_mt5() -> Dict[str, Any]:
    """Get system status formatted for MT5 client"""
    
    if not trading_system:
        return {
            "status": "not_initialized",
            "trading_enabled": False,
            "active_strategies": [],
            "total_trades": 0,
            "daily_pnl": 0.0
        }
    
    return {
        "status": "running" if trading_system.is_running else "stopped",
        "trading_enabled": trading_system.is_running,
        "active_strategies": list(trading_system.strategy_manager.strategies.keys()),
        "ml_models_loaded": list(trading_system.ml_models.keys()),
        "total_trades": trading_system.total_trades,
        "successful_trades": trading_system.successful_trades,
        "success_rate": trading_system.successful_trades / max(trading_system.total_trades, 1),
        "daily_pnl": trading_system.daily_pnl,
        "open_positions": len(trading_system.mt5_interface.get_open_positions()),
        "account_balance": trading_system.mt5_interface.get_account_info().get("balance", 0.0),
        "market_regime": trading_system.meta_learning.current_regime.value if trading_system.meta_learning.current_regime else "unknown",
        "last_update": datetime.now().isoformat()
    }

def get_memory_usage() -> Dict[str, float]:
    """Get memory usage statistics"""
    try:
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            "rss_mb": memory_info.rss / 1024 / 1024,  # Resident Set Size in MB
            "vms_mb": memory_info.vms / 1024 / 1024,  # Virtual Memory Size in MB
            "percent": process.memory_percent()
        }
    except ImportError:
        return {"error": "psutil not available"}

def get_uptime() -> Dict[str, float]:
    """Get uptime information"""
    try:
        import psutil
        boot_time = psutil.boot_time()
        current_time = time.time()
        uptime_seconds = current_time - boot_time
        
        return {
            "seconds": uptime_seconds,
            "minutes": uptime_seconds / 60,
            "hours": uptime_seconds / 3600,
            "days": uptime_seconds / 86400
        }
    except ImportError:
        return {"error": "psutil not available"}

# Background tasks
async def periodic_status_update():
    """Periodic status update broadcast"""
    while True:
        try:
            if trading_system:
                status = {
                    "type": "periodic_status",
                    "data": get_system_status_for_mt5()
                }
                await broadcast_to_all_clients(status)
            
            await asyncio.sleep(30)  # Every 30 seconds
            
        except Exception as e:
            logger.error(f"Error in periodic status update: {e}")
            await asyncio.sleep(60)

# Signal handlers for graceful shutdown
def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    
    if trading_system:
        # Create shutdown task
        asyncio.create_task(trading_system.shutdown())
    
    sys.exit(0)

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info("Helios ML Trading System Server starting...")
    
    # Create necessary directories
    directories = ["logs", "models", "data", "config"]
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Initialize Event-Based Trading Components
    await initialize_event_system()
    
    # Start background tasks
    asyncio.create_task(periodic_status_update())
    
    logger.info("Helios ML Trading System Server started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    logger.info("Helios ML Trading System Server shutting down...")
    
    if trading_system:
        await trading_system.shutdown()
    
    logger.info("Server shutdown complete")

# =============================================================================
# EVENT-BASED TRADING FUNCTIONS
# =============================================================================

async def initialize_event_system():
    """Initialize the event-based trading components"""
    global market_watchdog, sentiment_engine, risk_gatekeeper, event_system_initialized
    
    if not all([MarketWatchdog, NeuralSentiment, RiskGatekeeper]):
        logger.warning("Event-based trading modules not available")
        return
    
    try:
        logger.info("Initializing Event-Based Trading System...")
        
        # Initialize Market Watchdog
        market_watchdog = MarketWatchdog(logger=logger)
        market_watchdog.fetch_economic_calendar()
        logger.info("✅ Market Watchdog initialized")
        
        # Initialize Sentiment Engine
        sentiment_engine = NeuralSentiment(logger=logger)
        # Try to load model (non-blocking)
        try:
            sentiment_engine.load_model()
        except Exception as e:
            logger.warning(f"Could not load sentiment model: {e}")
        logger.info("✅ Sentiment Engine initialized")
        
        # Initialize Risk Gatekeeper
        risk_gatekeeper = RiskGatekeeper(
            config={
                'event_block_minutes_before': 30,
                'event_block_minutes_after': 15,
                'enable_session_filter': True,
                'enable_event_filter': True,
                'enable_sentiment_filter': False
            },
            logger=logger
        )
        
        # Integrate components
        risk_gatekeeper.integrate_with_system(market_watchdog, sentiment_engine)
        logger.info("✅ Risk Gatekeeper initialized")
        
        event_system_initialized = True
        logger.info("✅ Event-Based Trading System fully initialized")
        
    except Exception as e:
        logger.error(f"Error initializing event system: {e}")

# =============================================================================
# EVENT-BASED TRADING API ENDPOINTS
# =============================================================================

@app.get("/api/v1/trade_status")
async def get_trade_status(ml_signal: str = None):
    """
    Get current trade decision based on events, sessions, and sentiment
    
    Args:
        ml_signal: Optional ML signal (BUY/SELL) for sentiment filtering
        
    Returns:
        JSON with can_trade decision and detailed reasons
    """
    if not event_system_initialized or not risk_gatekeeper:
        return {
            "can_trade": True,
            "decision": "allow",
            "reason": "Event system not initialized - trading allowed",
            "event_system": "not_initialized"
        }
    
    try:
        # Get trade decision
        status = risk_gatekeeper.get_trade_status_json(ml_signal)
        return status
        
    except Exception as e:
        logger.error(f"Error getting trade status: {e}")
        return {
            "can_trade": True,
            "decision": "error",
            "reason": f"Error: {str(e)}",
            "event_system": "error"
        }

@app.get("/api/v1/events")
async def get_upcoming_events(hours: int = 24):
    """Get upcoming high-impact economic events"""
    if not market_watchdog:
        return {"events": [], "message": "Market watchdog not initialized"}
    
    try:
        events = market_watchdog.get_upcoming_high_impact_events(hours_ahead=hours)
        return {
            "events": events,
            "count": len(events),
            "timeframe_hours": hours
        }
    except Exception as e:
        logger.error(f"Error fetching events: {e}")
        return {"events": [], "error": str(e)}

@app.get("/api/v1/news")
async def get_market_news(max_items: int = 10):
    """Get latest market news with sentiment"""
    if not market_watchdog or not sentiment_engine:
        return {"news": [], "sentiment": {}, "message": "Components not initialized"}
    
    try:
        # Fetch news
        news = market_watchdog.fetch_news(max_items=max_items)
        
        # Analyze sentiment
        headlines = [item['title'] for item in news]
        sentiment_result = sentiment_engine.analyze_headlines(headlines) if headlines else {}
        
        return {
            "news": news,
            "sentiment": {
                "overall": sentiment_result.get('overall_sentiment', 'NEUTRAL'),
                "score": sentiment_result.get('sentiment_score', 0.0)
            }
        }
    except Exception as e:
        logger.error(f"Error fetching news: {e}")
        return {"news": [], "error": str(e)}

@app.get("/api/v1/sentiment")
async def get_sentiment(lookback_minutes: int = 60):
    """Get current market sentiment"""
    if not sentiment_engine:
        return {"mood": "NEUTRAL", "score": 0.0, "message": "Sentiment engine not initialized"}
    
    try:
        mood = sentiment_engine.get_market_mood(lookback_minutes=lookback_minutes)
        return mood
    except Exception as e:
        logger.error(f"Error getting sentiment: {e}")
        return {"mood": "ERROR", "score": 0.0, "error": str(e)}

@app.get("/api/v1/sessions")
async def get_market_sessions():
    """Get current market session status"""
    if not risk_gatekeeper:
        return {"sessions": {}, "message": "Risk gatekeeper not initialized"}
    
    try:
        current_session = risk_gatekeeper.get_current_session()
        in_overlap = risk_gatekeeper.is_in_session_overlap()
        session_times = risk_gatekeeper.get_session_times()
        
        return {
            "current_session": current_session.value,
            "in_overlap": in_overlap,
            "sessions": session_times
        }
    except Exception as e:
        logger.error(f"Error getting sessions: {e}")
        return {"error": str(e)}

@app.get("/api/v1/risk_analysis")
async def get_risk_analysis(ml_signal: str = None):
    """Get comprehensive risk analysis"""
    if not risk_gatekeeper:
        return {"message": "Risk gatekeeper not initialized"}
    
    try:
        # Get all risk checks
        session_check = risk_gatekeeper.check_session_risk()
        event_check = risk_gatekeeper.check_event_risk()
        sentiment_check = risk_gatekeeper.check_sentiment_risk(ml_signal)
        
        # Get overall decision
        decision = risk_gatekeeper.get_trade_decision(ml_signal)
        
        return {
            "session_check": session_check,
            "event_check": event_check,
            "sentiment_check": sentiment_check,
            "decision": {
                "can_trade": decision.can_trade,
                "decision": decision.decision,
                "reason": decision.reason,
                "volatility_level": decision.volatility_level
            }
        }
    except Exception as e:
        logger.error(f"Error in risk analysis: {e}")
        return {"error": str(e)}

@app.get("/api/v1/event_status")
async def get_event_status():
    """Get event system status"""
    if not all([market_watchdog, sentiment_engine, risk_gatekeeper]):
        return {
            "status": "not_initialized",
            "components": {
                "market_watchdog": market_watchdog is not None,
                "sentiment_engine": sentiment_engine is not None,
                "risk_gatekeeper": risk_gatekeeper is not None
            }
        }
    
    try:
        return {
            "status": "active",
            "components": {
                "market_watchdog": market_watchdog.get_status(),
                "sentiment_engine": sentiment_engine.get_status(),
                "risk_gatekeeper": risk_gatekeeper.get_status()
            }
        }
    except Exception as e:
        logger.error(f"Error getting event status: {e}")
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    # Ensure we're in the correct directory
    os.chdir(Path(__file__).parent)
    
    # Configure and start server
    uvicorn.run(
        "helios_server:app",
        host="0.0.0.0",
        port=8765,
        reload=False,  # Disable reload in production
        log_level="info",
        access_log=True,
        ws_ping_interval=20,
        ws_ping_timeout=30,
        close_connections_gracefully=True
    )