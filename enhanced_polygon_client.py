"""
Enhanced Polygon.io WebSocket Client
Leverages multiple Polygon services for comprehensive market data.
Based on Polygon.io documentation: https://polygon.io/docs/websocket/quickstart#next-steps
"""

import json
import time
import threading
import websocket
from typing import List, Dict, Optional, Callable
from config import Config
from logger import logger


class EnhancedPolygonClient:
    """
    Enhanced Polygon.io client that uses multiple WebSocket connections
    efficiently based on Polygon.io documentation recommendations.
    """
    
    def __init__(self):
        """Initialize enhanced client with multiple service support."""
        self.clients = {}
        self.data_handlers = {}
        self.connected_services = set()
        
        # Initialize different service clients
        self._init_service_clients()
    
    def _init_service_clients(self):
        """Initialize clients for different Polygon services."""
        services = {
            "stocks": "wss://socket.polygon.io/stocks",
            "options": "wss://socket.polygon.io/options", 
            "indices": "wss://socket.polygon.io/indices",
            "forex": "wss://socket.polygon.io/forex"
        }
        
        for service, url in services.items():
            self.clients[service] = {
                "url": url,
                "ws": None,
                "thread": None,
                "authenticated": False,
                "subscriptions": set()
            }
    
    def connect_service(self, service: str, max_retries: int = 3):
        """
        Connect to a specific Polygon service.
        
        Args:
            service: "stocks", "options", "indices", "forex"
            max_retries: Maximum connection attempts
        """
        if service not in self.clients:
            raise ValueError(f"Unknown service: {service}")
        
        client = self.clients[service]
        
        # Add random delay to prevent simultaneous connections
        import random
        delay = random.uniform(1, 5)
        logger.info(f"Connecting to {service} service in {delay:.1f} seconds...")
        time.sleep(delay)
        
        for attempt in range(max_retries):
            try:
                self._connect_websocket(service)
                return True
            except Exception as e:
                logger.warning(f"{service} connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    wait_time = 5 * (2 ** attempt)
                    logger.info(f"Retrying {service} in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to connect to {service} after {max_retries} attempts")
                    return False
    
    def _connect_websocket(self, service: str):
        """Establish WebSocket connection for a service."""
        client = self.clients[service]
        
        def on_open(ws):
            logger.info(f"WebSocket opened [{service}], authenticating...")
            # Authenticate
            auth_msg = {"action": "auth", "params": Config.POLYGON_API_KEY}
            ws.send(json.dumps(auth_msg))
        
        def on_message(ws, message):
            try:
                data = json.loads(message)
                self._handle_message(service, data)
            except Exception as e:
                logger.error(f"Error processing {service} message: {e}")
        
        def on_error(ws, error):
            logger.error(f"WebSocket error [{service}]: {error}")
            if "max_connections" in str(error):
                logger.error(f"Connection limit exceeded for {service} - waiting before retry")
                time.sleep(60)
        
        def on_close(ws, close_status_code, close_msg):
            logger.warning(f"WebSocket closed [{service}]: {close_status_code} - {close_msg}")
            client["authenticated"] = False
            self.connected_services.discard(service)
        
        # Create WebSocket connection
        client["ws"] = websocket.WebSocketApp(
            client["url"],
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        
        # Start connection in separate thread
        client["thread"] = threading.Thread(
            target=client["ws"].run_forever,
            daemon=True
        )
        client["thread"].start()
        
        # Wait for authentication
        timeout = 10
        start = time.time()
        while not client["authenticated"] and (time.time() - start) < timeout:
            time.sleep(0.1)
        
        if not client["authenticated"]:
            raise ConnectionError(f"Failed to authenticate {service} WebSocket")
        
        self.connected_services.add(service)
        logger.info(f"WebSocket connected and authenticated [{service}]")
    
    def _handle_message(self, service: str, data: Dict):
        """Handle incoming messages from different services."""
        if isinstance(data, list):
            # Multiple events bundled together
            for event in data:
                self._process_event(service, event)
        else:
            self._process_event(service, data)
    
    def _process_event(self, service: str, event: Dict):
        """Process individual events from services."""
        event_type = event.get("ev", "")
        
        # Route to appropriate handler
        if service == "stocks" and event_type in ["T", "A"]:
            # Trade or Aggregate data
            if "T.IWM" in str(event) or "A.IWM" in str(event):
                self._handle_iwm_data(event)
        elif service == "options" and event_type == "T":
            # Options trade data
            if "IWM" in str(event):
                self._handle_iwm_options_data(event)
        elif service == "indices":
            # Index data (SPY, QQQ correlation)
            self._handle_index_data(event)
        elif service == "forex":
            # Forex data for market sentiment
            self._handle_forex_data(event)
    
    def _handle_iwm_data(self, data: Dict):
        """Handle IWM stock data."""
        logger.debug(f"IWM Stock Data: {data}")
        # Route to your existing IWM strategy logic
    
    def _handle_iwm_options_data(self, data: Dict):
        """Handle IWM options data."""
        logger.debug(f"IWM Options Data: {data}")
        # Route to your options strategy logic
    
    def _handle_index_data(self, data: Dict):
        """Handle index data for market correlation."""
        logger.debug(f"Index Data: {data}")
        # Use for market correlation analysis
    
    def _handle_forex_data(self, data: Dict):
        """Handle forex data for market sentiment."""
        logger.debug(f"Forex Data: {data}")
        # Use for market sentiment analysis
    
    def subscribe_to_iwm_comprehensive(self):
        """
        Subscribe to comprehensive IWM data across multiple services.
        Based on Polygon.io documentation best practices.
        """
        # Stocks service - IWM trades and aggregates
        if "stocks" in self.connected_services:
            stocks_client = self.clients["stocks"]
            sub_msg = {
                "action": "subscribe",
                "params": "T.IWM,A.IWM"  # Trades and Aggregates
            }
            stocks_client["ws"].send(json.dumps(sub_msg))
            logger.info("Subscribed to IWM stock data (trades + aggregates)")
        
        # Options service - IWM options
        if "options" in self.connected_services:
            options_client = self.clients["options"]
            sub_msg = {
                "action": "subscribe", 
                "params": "T.O:IWM*"  # All IWM options
            }
            options_client["ws"].send(json.dumps(sub_msg))
            logger.info("Subscribed to IWM options data")
        
        # Indices service - Market correlation
        if "indices" in self.connected_services:
            indices_client = self.clients["indices"]
            sub_msg = {
                "action": "subscribe",
                "params": "T.SPY,T.QQQ"  # SPY and QQQ for correlation
            }
            indices_client["ws"].send(json.dumps(sub_msg))
            logger.info("Subscribed to market index data (SPY, QQQ)")
    
    def connect_all_services(self):
        """Connect to all available Polygon services."""
        services = ["stocks", "options", "indices", "forex"]
        
        for service in services:
            try:
                if self.connect_service(service):
                    logger.info(f"Successfully connected to {service}")
                else:
                    logger.warning(f"Failed to connect to {service}")
            except Exception as e:
                logger.error(f"Error connecting to {service}: {e}")
        
        # Subscribe to comprehensive IWM data
        if self.connected_services:
            self.subscribe_to_iwm_comprehensive()
            logger.info(f"Connected to {len(self.connected_services)} Polygon services")
        else:
            logger.error("No Polygon services connected")
    
    def disconnect_all(self):
        """Disconnect from all services."""
        for service, client in self.clients.items():
            if client["ws"]:
                client["ws"].close()
                logger.info(f"Disconnected from {service}")
        
        self.connected_services.clear()
        logger.info("Disconnected from all Polygon services")
