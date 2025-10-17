#!/usr/bin/env python3
"""
Miyagi Strategy System - Complete Implementation
Implements the complete Miyagi strategy with overnight analysis, bias logic, and VWAP control.
"""
import signal
import sys
import time
import threading
import os
from typing import Dict, Optional
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

from config import Config
from logger import setup_logger, log_trade_event
from multi_strategy_orchestrator import MultiStrategyOrchestrator
from utils import (
    is_market_hours, 
    can_enter_trade, 
    should_force_exit,
    get_todays_expiry,
    get_et_time
)

logger = setup_logger("MiyagiStrategyMain")


class HealthCheckHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler for Render health checks."""
    
    def do_GET(self):
        if self.path in ['/health', '/']:
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(b'Miyagi Strategy System Running')
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Suppress HTTP server logs."""
        pass


def start_health_server():
    """Start HTTP health check server for Render."""
    port = int(os.getenv('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    
    def run_server():
        logger.info(f"Health check server started on port {port}")
        try:
            server.serve_forever()
        except Exception as e:
            logger.error(f"Health server error: {e}")
    
    health_thread = threading.Thread(target=run_server, daemon=True)
    health_thread.start()
    return server


def main():
    """Main execution function."""
    logger.info("Starting Miyagi Strategy System")
    
    # Add instance check to prevent multiple instances
    import os
    import time
    import random
    import signal
    import sys
    
    # Add short startup delay to prevent multiple instances from starting simultaneously
    startup_delay = random.uniform(1, 3)
    logger.info(f"Instance startup delay: {startup_delay:.1f} seconds")
    time.sleep(startup_delay)
    
    # Start health check server
    health_server = start_health_server()
    
    # Initialize multi-strategy orchestrator
    strategy = MultiStrategyOrchestrator()
    
    # Start the complete strategy in a separate thread
    strategy_thread = threading.Thread(target=strategy.start_strategy, daemon=True)
    strategy_thread.start()
    
    # Signal handler for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        strategy.strategy_active = False
        if 'health_server' in locals():
            health_server.shutdown()
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Keep the main process alive with a keep-alive mechanism
    logger.info("Strategy started - keeping process alive...")
    try:
        while True:
            time.sleep(30)  # Sleep for 30 seconds
            logger.info("Keep-alive: Process still running...")
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Strategy error: {e}")
        raise
    finally:
        # Cleanup
        logger.info("Shutting down system...")
        strategy.strategy_active = False
        if 'health_server' in locals():
            health_server.shutdown()
        logger.info("System shutdown complete")


if __name__ == "__main__":
    main()
