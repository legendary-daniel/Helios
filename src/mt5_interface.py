"""
Helios ML Trading System - MetaTrader 5 Integration
Bridge between Python ML system and MetaTrader 5 Expert Advisor
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Union
import logging
import json
import asyncio
import websockets
import threading
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import hashlib
import hmac
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

@dataclass
class MT5Connection:
    """MT5 connection status"""
    connected: bool = False
    login: int = 0
    server: str = ""
    balance: float = 0.0
    equity: float = 0.0
    margin: float = 0.0
    free_margin: float = 0.0
    currency: str = "USD"
    last_update: Optional[datetime] = None

@dataclass
class TradeRequest:
    """Trade request from Python to MT5"""
    action: str  # BUY, SELL, CLOSE, MODIFY, DELETE
    symbol: str
    volume: float = 0.0
    price: float = 0.0
    sl: float = 0.0
    tp: float = 0.0
    deviation: int = 20
    magic: int = 123456
    comment: str = "Helios ML EA"
    type: int = 0  # ORDER_TYPE_BUY=0, ORDER_TYPE_SELL=1
    type_filling: int = 2  # ORDER_FILLING_FOK
    type_time: int = 1  # ORDER_TIME_GTC
    expiration: int = 0
    request_id: str = ""
    timestamp: float = 0.0

@dataclass
class TradeResult:
    """Trade execution result from MT5"""
    retcode: int = 0
    deal: int = 0
    order: int = 0
    volume: float = 0.0
    price: float = 0.0
    bid: float = 0.0
    ask: float = 0.0
    comment: str = ""
    request_id: str = ""
    retcode_external: int = 0

class MT5Interface:
    """MetaTrader 5 interface for trading operations"""
    
    def __init__(self, config, logger=None):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.connection = MT5Connection()
        self.market_data_cache = {}
        self.is_initialized = False
        
        # WebSocket server for communication with EA
        self.ws_server = None
        self.ws_clients = set()
        self.ws_running = False
        
        # Signal processing
        self.pending_signals = []
        self.signal_lock = threading.Lock()
        
    def initialize(self) -> bool:
        """Initialize MT5 connection"""
        try:
            # Initialize MT5
            if not mt5.initialize():
                self.logger.error(f"MT5 initialization failed: {mt5.last_error()}")
                return False
            
            # Get account info
            account_info = mt5.account_info()
            if account_info is None:
                self.logger.error("Failed to get account info")
                return False
            
            # Update connection info
            self.connection.connected = True
            self.connection.login = account_info.login
            self.connection.server = account_info.server
            self.connection.balance = account_info.balance
            self.connection.equity = account_info.equity
            self.connection.margin = account_info.margin
            self.connection.free_margin = account_info.margin_free
            self.connection.currency = account_info.currency
            self.connection.last_update = datetime.now()
            
            self.is_initialized = True
            self.logger.info(f"MT5 connected: Account {self.connection.login} on {self.connection.server}")
            
            # Start WebSocket server for EA communication
            self.start_websocket_server()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize MT5: {e}")
            return False
    
    def shutdown(self):
        """Shutdown MT5 connection"""
        try:
            if self.ws_running:
                self.stop_websocket_server()
            
            if self.is_initialized:
                mt5.shutdown()
                self.is_initialized = False
                self.connection.connected = False
                
            self.logger.info("MT5 connection closed")
            
        except Exception as e:
            self.logger.error(f"Error during MT5 shutdown: {e}")
    
    def get_market_data(self, symbol: str, timeframe: str = "M1", count: int = 500) -> Optional[pd.DataFrame]:
        """Get market data from MT5"""
        if not self.is_initialized:
            return None
        
        try:
            # Convert timeframe string to MT5 enum
            timeframe_map = {
                "M1": mt5.TIMEFRAME_M1,
                "M5": mt5.TIMEFRAME_M5,
                "M15": mt5.TIMEFRAME_M15,
                "M30": mt5.TIMEFRAME_M30,
                "H1": mt5.TIMEFRAME_H1,
                "H4": mt5.TIMEFRAME_H4,
                "D1": mt5.TIMEFRAME_D1,
                "W1": mt5.TIMEFRAME_W1,
                "MN1": mt5.TIMEFRAME_MN1
            }
            
            mt5_timeframe = timeframe_map.get(timeframe, mt5.TIMEFRAME_M1)
            
            # Get rates
            rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, count)
            if rates is None or len(rates) == 0:
                self.logger.warning(f"No data received for {symbol} {timeframe}")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('time', inplace=True)
            df.rename(columns={
                'open': 'open',
                'high': 'high', 
                'low': 'low',
                'close': 'close',
                'tick_volume': 'tick_volume',
                'spread': 'spread',
                'real_volume': 'real_volume'
            }, inplace=True)
            
            # Cache the data
            cache_key = f"{symbol}_{timeframe}"
            self.market_data_cache[cache_key] = {
                'data': df,
                'timestamp': time.time()
            }
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error getting market data for {symbol}: {e}")
            return None
    
    def get_current_prices(self, symbols: List[str]) -> Dict[str, Dict[str, float]]:
        """Get current prices for multiple symbols"""
        if not self.is_initialized:
            return {}
        
        prices = {}
        
        for symbol in symbols:
            try:
                tick = mt5.symbol_info_tick(symbol)
                if tick is not None:
                    prices[symbol] = {
                        'bid': tick.bid,
                        'ask': tick.ask,
                        'spread': tick.ask - tick.bid,
                        'time': datetime.fromtimestamp(tick.time)
                    }
                else:
                    self.logger.warning(f"No tick data for {symbol}")
                    
            except Exception as e:
                self.logger.error(f"Error getting tick for {symbol}: {e}")
        
        return prices
    
    def place_order(self, order: TradeRequest) -> Optional[TradeResult]:
        """Place an order in MT5"""
        if not self.is_initialized:
            self.logger.error("MT5 not initialized")
            return None
        
        try:
            # Generate unique request ID
            order.request_id = self._generate_request_id()
            order.timestamp = time.time()
            
            # Prepare the request structure
            request = {
                "action": self._get_action_code(order.action),
                "symbol": order.symbol,
                "volume": order.volume,
                "price": order.price,
                "sl": order.sl,
                "tp": order.tp,
                "deviation": order.deviation,
                "magic": order.magic,
                "comment": order.comment,
                "type": order.type,
                "type_filling": order.type_filling,
                "type_time": order.type_time,
                "expiration": order.expiration
            }
            
            # Send order
            result = mt5.order_send(request)
            
            if result is None:
                self.logger.error("Order send returned None")
                return None
            
            # Convert result to TradeResult
            trade_result = TradeResult(
                retcode=result.retcode,
                deal=result.deal,
                order=result.order,
                volume=result.volume,
                price=result.price,
                bid=result.bid,
                ask=result.ask,
                comment=result.comment,
                retcode_external=result.retcode_external
            )
            
            # Log result
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                self.logger.info(f"Order executed successfully: {order.action} {order.volume} {order.symbol} at {result.price}")
            else:
                self.logger.warning(f"Order failed: {result.retcode} - {result.comment}")
            
            return trade_result
            
        except Exception as e:
            self.logger.error(f"Error placing order: {e}")
            return None
    
    def close_position(self, ticket: int, deviation: int = 20) -> Optional[TradeResult]:
        """Close a position by ticket"""
        if not self.is_initialized:
            return None
        
        try:
            # Get position info
            positions = mt5.positions_get(ticket=ticket)
            if positions is None or len(positions) == 0:
                self.logger.error(f"Position {ticket} not found")
                return None
            
            position = positions[0]
            
            # Prepare close request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": position.volume,
                "type": mt5.ORDER_TYPE_SELL if position.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY,
                "position": ticket,
                "deviation": deviation,
                "magic": position.magic,
                "comment": "Helios ML EA Close"
            }
            
            # Get current price
            tick = mt5.symbol_info_tick(position.symbol)
            if tick is None:
                return None
            
            request["price"] = tick.bid if position.type == mt5.POSITION_TYPE_BUY else tick.ask
            
            # Send close request
            result = mt5.order_send(request)
            
            if result is not None and result.retcode == mt5.TRADE_RETCODE_DONE:
                self.logger.info(f"Position {ticket} closed successfully")
            
            return TradeResult(
                retcode=result.retcode if result else 0,
                deal=result.deal if result else 0,
                volume=result.volume if result else 0,
                price=result.price if result else 0,
                comment=result.comment if result else ""
            )
            
        except Exception as e:
            self.logger.error(f"Error closing position {ticket}: {e}")
            return None
    
    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Get all open positions"""
        if not self.is_initialized:
            return []
        
        try:
            positions = mt5.positions_get()
            if positions is None:
                return []
            
            open_positions = []
            for pos in positions:
                open_positions.append({
                    'ticket': pos.ticket,
                    'symbol': pos.symbol,
                    'type': pos.type,
                    'volume': pos.volume,
                    'price_open': pos.price_open,
                    'sl': pos.sl,
                    'tp': pos.tp,
                    'profit': pos.profit,
                    'swap': pos.swap,
                    'price_current': pos.price_current,
                    'comment': pos.comment,
                    'magic': pos.magic,
                    'swap': pos.swap,
                    'time': datetime.fromtimestamp(pos.time)
                })
            
            return open_positions
            
        except Exception as e:
            self.logger.error(f"Error getting open positions: {e}")
            return []
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get current account information"""
        if not self.is_initialized:
            return {}
        
        try:
            account_info = mt5.account_info()
            if account_info is None:
                return {}
            
            self.connection.balance = account_info.balance
            self.connection.equity = account_info.equity
            self.connection.margin = account_info.margin
            self.connection.free_margin = account_info.margin_free
            self.connection.last_update = datetime.now()
            
            return {
                'login': account_info.login,
                'server': account_info.server,
                'balance': account_info.balance,
                'equity': account_info.equity,
                'margin': account_info.margin,
                'free_margin': account_info.margin_free,
                'currency': account_info.currency,
                'leverage': account_info.leverage,
                'name': account_info.name,
                'company': account_info.company
            }
            
        except Exception as e:
            self.logger.error(f"Error getting account info: {e}")
            return {}
    
    def _get_action_code(self, action: str) -> int:
        """Convert action string to MT5 action code"""
        action_map = {
            "BUY": mt5.TRADE_ACTION_DEAL,
            "SELL": mt5.TRADE_ACTION_DEAL,
            "CLOSE": mt5.TRADE_ACTION_DEAL,
            "MODIFY": mt5.TRADE_ACTION_SLTP,
            "DELETE": mt5.TRADE_ACTION_REMOVE,
            "PENDING": mt5.TRADE_ACTION_PENDING
        }
        return action_map.get(action, mt5.TRADE_ACTION_DEAL)
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID"""
        timestamp = str(time.time())
        random_bytes = np.random.bytes(16)
        data = f"{timestamp}_{random_bytes.hex()}".encode()
        return hashlib.sha256(data).hexdigest()[:16]
    
    def start_websocket_server(self):
        """Start WebSocket server for EA communication"""
        try:
            self.ws_server = WebSocketServer(self.config, self.logger)
            self.ws_running = True
            self.logger.info("WebSocket server started for EA communication")
        except Exception as e:
            self.logger.error(f"Failed to start WebSocket server: {e}")
    
    def stop_websocket_server(self):
        """Stop WebSocket server"""
        if self.ws_server:
            self.ws_server.stop()
            self.ws_running = False
            self.logger.info("WebSocket server stopped")

class WebSocketServer:
    """WebSocket server for communication between Python and MT5 EA"""
    
    def __init__(self, config, logger=None):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.clients = set()
        self.server = None
        self.running = False
        self.port = 8765
        
    async def register_client(self, websocket, path):
        """Register a new client connection"""
        self.clients.add(websocket)
        self.logger.info(f"Client connected. Total clients: {len(self.clients)}")
        
        try:
            await websocket.wait_closed()
        finally:
            self.clients.remove(websocket)
            self.logger.info(f"Client disconnected. Total clients: {len(self.clients)}")
    
    async def broadcast_message(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients"""
        if not self.clients:
            return
        
        message_str = json.dumps(message)
        disconnected_clients = set()
        
        for client in self.clients:
            try:
                await client.send(message_str)
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(client)
            except Exception as e:
                self.logger.error(f"Error sending message to client: {e}")
                disconnected_clients.add(client)
        
        # Remove disconnected clients
        self.clients -= disconnected_clients
    
    def send_signal_to_ea(self, signal_data: Dict[str, Any]):
        """Send trading signal to EA via WebSocket"""
        if not self.running:
            return
        
        # Add signal to message
        message = {
            'type': 'trading_signal',
            'timestamp': time.time(),
            'data': signal_data
        }
        
        # Schedule broadcast in event loop
        if hasattr(self, '_loop') and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self.broadcast_message(message), 
                self._loop
            )
    
    def start(self, port: int = None):
        """Start the WebSocket server"""
        if port:
            self.port = port
        
        self.running = True
        
        # Start server in a separate thread
        def run_server():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop
            
            start_server = websockets.serve(self.register_client, "localhost", self.port)
            self.server = loop.run_until_complete(start_server)
            
            self.logger.info(f"WebSocket server running on port {self.port}")
            loop.run_forever()
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
    
    def stop(self):
        """Stop the WebSocket server"""
        self.running = False
        if self.server:
            self.server.close()
        self.logger.info("WebSocket server stopped")

if __name__ == "__main__":
    # Test MT5 interface
    import logging
    logging.basicConfig(level=logging.INFO)
    
    from config.config import config
    
    mt5_interface = MT5Interface(config)
    
    # Test connection (will fail if MT5 is not running)
    if mt5_interface.initialize():
        print("MT5 connection successful!")
        
        # Test getting market data
        data = mt5_interface.get_market_data("EURUSD", "H1", 10)
        if data is not None:
            print(f"Market data shape: {data.shape}")
            print(data.head())
        
        # Test account info
        account_info = mt5_interface.get_account_info()
        print(f"Account info: {account_info}")
        
        # Test open positions
        positions = mt5_interface.get_open_positions()
        print(f"Open positions: {len(positions)}")
        
        mt5_interface.shutdown()
    else:
        print("MT5 connection failed. Make sure MT5 is running and logged in.")