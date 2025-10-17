"""
Polygon.io WebSocket and REST API client for real-time market data.
Handles stocks and options feeds with automatic reconnection.
"""
import json
import time
import threading
from typing import Callable, Dict, List, Optional, Set
from collections import deque
import websocket
import requests
from logger import setup_logger
from config import Config

logger = setup_logger("PolygonClient")


class PolygonWebSocketClient:
    """WebSocket client for Polygon real-time feeds."""
    
    def __init__(self, ws_type: str = "stocks"):
        """
        Initialize WebSocket client.
        
        Args:
            ws_type: "stocks" or "options"
        """
        self.ws_type = ws_type
        self.ws_url = Config.POLYGON_WS_STOCKS if ws_type == "stocks" else Config.POLYGON_WS_OPTIONS
        self.api_key = Config.POLYGON_API_KEY
        
        self.ws: Optional[websocket.WebSocketApp] = None
        self.thread: Optional[threading.Thread] = None
        self.subscriptions: Set[str] = set()
        self.connected = False
        self.authenticated = False
        
        # Message handlers
        self.handlers: Dict[str, List[Callable]] = {}
        
        # Last message timestamp for stall detection
        self.last_message_time = time.time()
        
    def on_message(self, ws, message):
        """Handle incoming WebSocket message."""
        self.last_message_time = time.time()
        
        try:
            data = json.loads(message)
            
            # Handle connection messages
            if isinstance(data, list):
                for item in data:
                    self._route_message(item)
            elif isinstance(data, dict):
                self._route_message(data)
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode message: {e}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    def _route_message(self, msg: dict):
        """Route message to appropriate handler."""
        ev_type = msg.get('ev')
        
        if ev_type == 'status':
            status = msg.get('status')
            message = msg.get('message', '')
            logger.info(f"WS Status [{self.ws_type}]: {status} - {message}")
            
            if status == 'connected':
                self.connected = True
            elif status == 'auth_success':
                self.authenticated = True
                self._resubscribe()
                
        elif ev_type in self.handlers:
            for handler in self.handlers[ev_type]:
                try:
                    handler(msg)
                except Exception as e:
                    logger.error(f"Handler error for {ev_type}: {e}")
    
    def on_error(self, ws, error):
        """Handle WebSocket error."""
        logger.error(f"WebSocket error [{self.ws_type}]: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket close."""
        logger.warning(f"WebSocket closed [{self.ws_type}]: {close_status_code} - {close_msg}")
        self.connected = False
        self.authenticated = False
    
    def on_open(self, ws):
        """Handle WebSocket open - authenticate."""
        logger.info(f"WebSocket opened [{self.ws_type}], authenticating...")
        auth_msg = {"action": "auth", "params": self.api_key}
        ws.send(json.dumps(auth_msg))
    
    def connect(self):
        """Establish WebSocket connection."""
        if self.connected:
            logger.warning(f"Already connected [{self.ws_type}]")
            return
        
        logger.info(f"Connecting to Polygon WebSocket [{self.ws_type}]...")
        
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        
        self.thread = threading.Thread(target=self.ws.run_forever, daemon=True)
        self.thread.start()
        
        # Wait for authentication
        timeout = 10
        start = time.time()
        while not self.authenticated and (time.time() - start) < timeout:
            time.sleep(0.1)
        
        if not self.authenticated:
            raise ConnectionError(f"Failed to authenticate WebSocket [{self.ws_type}]")
        
        logger.info(f"WebSocket connected and authenticated [{self.ws_type}]")
    
    def subscribe(self, channels: List[str]):
        """
        Subscribe to channels.
        
        Args:
            channels: List of channel strings (e.g., ["A.IWM", "T.O:IWM*"])
        """
        if not self.authenticated:
            logger.warning("Not authenticated, queueing subscriptions")
            self.subscriptions.update(channels)
            return
        
        sub_msg = {"action": "subscribe", "params": ",".join(channels)}
        self.ws.send(json.dumps(sub_msg))
        self.subscriptions.update(channels)
        logger.info(f"Subscribed to: {channels}")
    
    def unsubscribe(self, channels: List[str]):
        """Unsubscribe from channels."""
        if not self.authenticated:
            return
        
        unsub_msg = {"action": "unsubscribe", "params": ",".join(channels)}
        self.ws.send(json.dumps(unsub_msg))
        self.subscriptions.difference_update(channels)
        logger.info(f"Unsubscribed from: {channels}")
    
    def _resubscribe(self):
        """Resubscribe to all channels after reconnection."""
        if self.subscriptions:
            self.subscribe(list(self.subscriptions))
    
    def register_handler(self, event_type: str, handler: Callable):
        """
        Register a handler for a specific event type.
        
        Args:
            event_type: Event type (e.g., 'A', 'T', 'Q' for agg, trade, quote)
            handler: Callback function that receives message dict
        """
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
        logger.debug(f"Registered handler for {event_type}")
    
    def is_stalled(self) -> bool:
        """Check if data feed has stalled."""
        return (time.time() - self.last_message_time) > Config.WS_SILENCE_ALERT_SECONDS
    
    def disconnect(self):
        """Close WebSocket connection gracefully."""
        if self.ws:
            self.ws.close()
        self.connected = False
        self.authenticated = False
        logger.info(f"WebSocket disconnected [{self.ws_type}]")


class PolygonRESTClient:
    """REST API client for Polygon data."""
    
    def __init__(self):
        self.base_url = Config.POLYGON_REST_BASE
        self.api_key = Config.POLYGON_API_KEY
        self.session = requests.Session()
        
    def _request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make authenticated REST request with retry logic.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            Response JSON or None on error
        """
        url = f"{self.base_url}{endpoint}"
        params = params or {}
        params['apiKey'] = self.api_key
        
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, params=params, timeout=10)
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    logger.warning(f"Rate limited on {endpoint} (attempt {attempt + 1})")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                        continue
                elif e.response.status_code == 401:
                    logger.error(f"Authentication failed on {endpoint}: Invalid API key")
                    return None
                elif e.response.status_code == 403:
                    logger.error(f"Access forbidden on {endpoint}: Check API permissions")
                    return None
                else:
                    logger.error(f"HTTP error on {endpoint}: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                return None
                
            except requests.exceptions.Timeout as e:
                logger.warning(f"Timeout on {endpoint} (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return None
                
            except requests.exceptions.ConnectionError as e:
                logger.error(f"Connection error on {endpoint}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return None
                
            except Exception as e:
                logger.error(f"Unexpected error on {endpoint}: {e}")
                return None
        
        logger.error(f"Failed to complete request to {endpoint} after {max_retries} attempts")
        return None
    
    def get_options_chain(self, underlying: str, expiry: Optional[str] = None) -> Optional[List[Dict]]:
        """
        Get options chain snapshot for an underlying.
        
        Args:
            underlying: Ticker symbol (e.g., 'IWM')
            expiry: Optional expiry filter (YYYY-MM-DD)
            
        Returns:
            List of contract dicts or None
        """
        endpoint = f"/v3/snapshot/options/{underlying}"
        params = {
            'limit': 250  # Get full chain, not just 10 contracts
        }
        
        if expiry:
            params['expiration_date'] = expiry
        
        data = self._request(endpoint, params)
        
        if data and data.get('status') == 'OK':
            results = data.get('results', [])
            logger.info(f"Polygon returned {len(results)} contracts for {underlying}")
            return results
        return None
    
    def get_aggregates(self, ticker: str, multiplier: int = 1, 
                       timespan: str = "minute", from_ts: str = None, 
                       to_ts: str = None, limit: int = 50) -> Optional[List[Dict]]:
        """
        Get historical aggregates (bars).
        
        Args:
            ticker: Symbol
            multiplier: Size of timespan
            timespan: 'second', 'minute', 'hour', 'day'
            from_ts: Start timestamp
            to_ts: End timestamp
            limit: Max results
            
        Returns:
            List of aggregate dicts or None
        """
        endpoint = f"/v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from_ts}/{to_ts}"
        params = {'limit': limit}
        
        data = self._request(endpoint, params)
        
        if data and data.get('status') == 'OK':
            return data.get('results', [])
        return None


class DataBuffer:
    """Ring buffer for time-series data with automatic expiry."""
    
    def __init__(self, max_age_seconds: int = 3600):
        """
        Initialize buffer.
        
        Args:
            max_age_seconds: Maximum age of data to retain
        """
        self.max_age = max_age_seconds
        self.data: deque = deque()
        self.lock = threading.Lock()
    
    def append(self, item: Dict):
        """Add item with timestamp."""
        with self.lock:
            item['_buffer_ts'] = time.time()
            self.data.append(item)
            self._cleanup()
    
    def _cleanup(self):
        """Remove expired items."""
        cutoff = time.time() - self.max_age
        while self.data and self.data[0].get('_buffer_ts', 0) < cutoff:
            self.data.popleft()
    
    def get_recent(self, seconds: int) -> List[Dict]:
        """Get items from last N seconds."""
        with self.lock:
            self._cleanup()
            cutoff = time.time() - seconds
            return [item for item in self.data if item.get('_buffer_ts', 0) >= cutoff]
    
    def get_all(self) -> List[Dict]:
        """Get all items in buffer."""
        with self.lock:
            self._cleanup()
            return list(self.data)
    
    def clear(self):
        """Clear all data."""
        with self.lock:
            self.data.clear()

