#!/usr/bin/env python3
"""
IWM Strategy System - Complete Implementation
Implements the complete IWM strategy with overnight analysis, bias logic, and VWAP control.
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
from strategy_orchestrator import IWMStrategyOrchestrator
from utils import (
    is_market_hours, 
    can_enter_trade, 
    should_force_exit,
    get_todays_expiry,
    get_et_time
)

logger = setup_logger("IWMStrategyMain")


class HealthCheckHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler for Render health checks."""
    
    def do_GET(self):
        if self.path in ['/health', '/']:
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(b'IWM Corrected Multi-Strategy System Running')
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_HEAD(self):
        """Handle HEAD requests for health checks."""
        if self.path in ['/health', '/']:
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Log health check requests for debugging
        logger.debug(f"Health check: {format % args}")


def start_health_server():
    """Start HTTP server for health checks."""
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    # Start server in daemon thread for Render compatibility
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    logger.info(f"Health server on port {port}")
    return server


class IWM5VWAPSystem:
    """
    IWM-5-VWAP Advanced VWAP Strategy System.
    Advanced VWAP-based strategy for IWM options trading.
    """
    
    def __init__(self):
        """Initialize IWM-5-VWAP system components."""
        self.running = False
        self.shutdown_event = threading.Event()
        
        # Validate configuration
        validation = Config.validate()
        if not validation['valid']:
            logger.error("Configuration errors:")
            for error in validation['errors']:
                logger.error(f"  - {error}")
            
            # Check if we're in a deployment environment
            if os.getenv('RENDER'):
                logger.critical("FATAL: Missing required environment variables in Render deployment")
                logger.critical("Please check Render dashboard -> Environment tab")
                logger.critical("Required: POLYGON_API_KEY, PUSHOVER_TOKEN, PUSHOVER_USER_KEY")
                logger.critical(f"Current env vars: RENDER={os.getenv('RENDER')}, PORT={os.getenv('PORT')}")
            else:
                logger.critical("FATAL: Missing required environment variables")
                logger.critical("Please set: POLYGON_API_KEY, PUSHOVER_TOKEN, PUSHOVER_USER_KEY")
            
            raise ValueError("Invalid configuration. Check environment variables.")
        
        logger.info("Initializing IWM-5-VWAP Advanced VWAP System...")
        logger.info(Config.get_config_summary())
        
        # Core components
        self.ws_stocks = PolygonWebSocketClient(ws_type="stocks")
        self.rest_client = PolygonRESTClient()
        
        # Strat-0DTE components
        self.bias_engine = StratBiasEngine()
        self.execution_engine = VWAPExecutionEngine(self.bias_engine)
        self.options_mapper = OptionsMapper()
        self.position_manager = PositionManager()
        self.risk_manager = RiskManager()
        self.alert_client = CorrectedMultiStrategyPushoverClient()
        
        # State tracking
        self.current_chain_data: Optional[list] = None
        self.last_chain_update: float = 0
        self.last_entry_time: float = 0
        self.min_time_between_entries = 60  # 1 minute between entries
        
        # Strategy tracking
        self.strategy_stats = {
            'momentum': {'signals': 0, 'wins': 0, 'losses': 0, 'win_rate': 0},
            'gap': {'signals': 0, 'wins': 0, 'losses': 0, 'win_rate': 0},
            'volume': {'signals': 0, 'wins': 0, 'losses': 0, 'win_rate': 0},
            'strength': {'signals': 0, 'wins': 0, 'losses': 0, 'win_rate': 0},
            'combined': {'signals': 0, 'wins': 0, 'losses': 0, 'win_rate': 0}
        }
        
        # Register shutdown handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        # Start health server
        start_health_server()
        
        logger.info("✓ CORRECTED Multi-Strategy System initialized")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.warning(f"Received signal {signum}, shutting down...")
        self.shutdown()
    
    def start(self):
        """Start the corrected multi-strategy trading system."""
        try:
            self.running = True
            
            # Connect to WebSocket
            self._connect_websocket()
            
            # Start background tasks
            self._start_background_tasks()
            
            logger.warning("🚀 CORRECTED Multi-Strategy IWM System ONLINE")
            self.alert_client.send_system_alert(
                f"CORRECTED Multi-Strategy System started at {get_et_time().strftime('%H:%M:%S ET')}",
                priority=0
            )
            
            # Main event loop
            self._main_loop()
            
        except Exception as e:
            logger.critical(f"Fatal error: {e}", exc_info=True)
            self.alert_client.send_system_alert(f"SYSTEM ERROR: {str(e)[:200]}", priority=1)
            raise
        finally:
            self.shutdown()
    
    def _connect_websocket(self):
        """Connect to Polygon stocks WebSocket for IWM price data."""
        logger.info("Connecting to Polygon stocks WebSocket...")
        
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                self.ws_stocks.connect()
                logger.info("WebSocket connection initiated")
                
                # Wait a moment for connection to establish
                time.sleep(2)
                
                self.ws_stocks.register_handler('A', self._handle_stock_aggregate)
                self.ws_stocks.subscribe([f"A.{Config.UNDERLYING_SYMBOL}"])
                
                logger.info(f"✓ WebSocket connected and subscribed to A.{Config.UNDERLYING_SYMBOL}")
                logger.info("Waiting for stock data...")
                return  # Success, exit retry loop
                
            except ConnectionError as e:
                logger.error(f"WebSocket connection failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.critical("Failed to connect to WebSocket after all retries")
                    raise
            except Exception as e:
                logger.error(f"Unexpected error during WebSocket connection: {e}")
                raise
    
    def _start_background_tasks(self):
        """Start background tasks."""
        logger.info("Starting background tasks...")
        
        # Chain update thread
        chain_thread = threading.Thread(
            target=self._chain_update_loop,
            daemon=True,
            name="ChainUpdater"
        )
        chain_thread.start()
        
        # Strategy summary thread (every 30 minutes)
        summary_thread = threading.Thread(
            target=self._strategy_summary_loop,
            daemon=True,
            name="StrategySummary"
        )
        summary_thread.start()
        
        logger.info("✓ Background tasks started (2 threads)")
    
    def _main_loop(self):
        """Main event loop for corrected multi-strategy system."""
        logger.info("Entering CORRECTED multi-strategy main loop...")
        
        while self.running and not self.shutdown_event.is_set():
            try:
                # Market hours check
                if not is_market_hours():
                    time.sleep(60)
                    continue
                
                # Force exit at 15:55
                if should_force_exit() and self.risk_manager.has_position():
                    logger.warning("Time stop reached - forcing exit")
                    self._execute_exit("Time stop 15:55 ET")
                
                # Monitor position if we have one
                if self.risk_manager.has_position():
                    try:
                        self._monitor_position()
                    except Exception as e:
                        logger.error(f"Error in position monitoring: {e}", exc_info=True)
                
                # Check for Strat-0DTE signals if no position
                elif not self.position_manager.current_position:
                    try:
                        self._check_strat_signals()
                    except Exception as e:
                        logger.error(f"Error in Strat signal checking: {e}", exc_info=True)
                
                # Manage active positions
                try:
                    self._manage_positions()
                except Exception as e:
                    logger.error(f"Error in position management: {e}", exc_info=True)
                
                # Check exit conditions for active positions (every loop iteration)
                try:
                    if hasattr(self, 'current_stock_data') and self.current_stock_data:
                        current_price = self.current_stock_data.get('current_price', 0)
                        if current_price > 0:
                            closed_positions = self.alert_client.check_and_close_positions(current_price)
                            if closed_positions:
                                logger.info(f"Closed {len(closed_positions)} positions")
                except Exception as e:
                    logger.error(f"Error checking exit conditions: {e}", exc_info=True)
                
                
                # Check WebSocket health periodically
                try:
                    self._check_websocket_health()
                except Exception as e:
                    logger.error(f"Error in WebSocket health check: {e}", exc_info=True)
                
                # Periodic log for entry cooldown
                if not hasattr(self, '_last_cooldown_log'):
                    self._last_cooldown_log = 0
                
                now = time.time()
                if now - self._last_cooldown_log > 60:
                    remaining = int(self.min_time_between_entries - (time.time() - self.last_entry_time))
                    logger.debug(f"Entry cooldown: {remaining}s remaining before next entry allowed")
                    self._last_cooldown_log = now
                else:
                    # Periodic log for time restrictions
                    if not hasattr(self, '_last_time_restriction_log'):
                        self._last_time_restriction_log = 0
                    
                    now = time.time()
                    if now - self._last_time_restriction_log > 300:  # Every 5 minutes
                        current_et = get_et_time()
                        can_enter = can_enter_trade()
                        logger.info(f"⏰ Time check: {current_et.strftime('%H:%M:%S')} ET, Cutoff: {Config.NO_ENTRY_AFTER} ET, Can enter: {can_enter}")
                        self._last_time_restriction_log = now
                
                # Professional monitoring loop - check every 2 seconds
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                time.sleep(5)
        
        logger.info("Main loop exited")
    
    def _chain_update_loop(self):
        """Poll options chain for contract selection."""
        logger.info("Chain update thread started")
        
        while self.running and not self.shutdown_event.is_set():
            try:
                if not is_market_hours():
                    time.sleep(30)
                    continue
                
                # Get 0DTE chain
                expiry = get_todays_expiry()
                chain_data = self.rest_client.get_options_chain(
                    Config.UNDERLYING_SYMBOL,
                    expiry=expiry
                )
                
                if chain_data:
                    logger.info(f"Chain snapshot: {len(chain_data)} contracts")
                    self.current_chain_data = chain_data
                    self.last_chain_update = time.time()
                    
                    # Update tracked contracts for both calls and puts
                    self.contract_selector.filter_and_rank_contracts(chain_data)
                else:
                    logger.warning("⚠️ Chain snapshot returned empty data - retrying next cycle")
                
                # Poll every 10 seconds
                time.sleep(Config.CHAIN_SNAPSHOT_INTERVAL_SECONDS)
                
            except Exception as e:
                logger.error(f"Error in chain update: {e}", exc_info=True)
                time.sleep(10)
    
    def _strategy_summary_loop(self):
        """Send strategy performance summary once at end of market day."""
        logger.info("Strategy summary thread started")
        
        summary_sent_today = False
        
        while self.running and not self.shutdown_event.is_set():
            try:
                time.sleep(60)  # Check every minute
                
                # Check if market just closed (between 15:55 and 16:00 ET)
                from utils import get_et_time
                current_time = get_et_time()
                current_hour = current_time.hour
                current_minute = current_time.minute
                
                # Market closes at 16:00 ET, send summary between 15:55-16:00
                if current_hour == 15 and current_minute >= 55 and not summary_sent_today:
                    # Only send summary if there are actual trades
                    total_signals = sum(stats.get('signals', 0) for stats in self.strategy_stats.values())
                    if total_signals > 0:
                        self.alert_client.send_strategy_summary_alert(self.strategy_stats)
                        summary_sent_today = True
                        logger.info("End-of-day strategy summary sent")
                    else:
                        logger.debug("No trades today - skipping end-of-day summary")
                        summary_sent_today = True
                
                # Reset flag at start of new trading day (9:30 AM ET)
                if current_hour == 9 and current_minute >= 30:
                    summary_sent_today = False
                
            except Exception as e:
                logger.error(f"Error in strategy summary: {e}", exc_info=True)
                time.sleep(60)
    
    def _handle_stock_aggregate(self, msg: Dict):
        """Handle IWM per-second price updates."""
        # Log data reception periodically (every 60 seconds)
        if not hasattr(self, '_last_data_log'):
            self._last_data_log = 0
        
        now = time.time()
        if now - self._last_data_log > 60:
            price = msg.get('c', 0)
            vwap = msg.get('a', 0)
            volume = msg.get('v', 0)
            logger.info(f"📊 Data feed active: IWM ${price:.2f}, VWAP ${vwap:.2f}, Vol {volume:,}")
            self._last_data_log = now
        
        # Mark that we received WebSocket data
        if hasattr(self, '_websocket_data_received'):
            self._websocket_data_received = True
        
        # Update Strat-0DTE execution engine
        self.execution_engine.update(msg)
        
        # Store current stock data for position checking
        self.current_stock_data = {
            'current_price': msg.get('c', 0),
            'vwap': msg.get('a', 0),
            'volume': msg.get('v', 0),
            'timestamp': time.time()
        }
    
    def _check_websocket_health(self):
        """Check if WebSocket is receiving data."""
        if not hasattr(self, '_last_websocket_check'):
            self._last_websocket_check = time.time()
            self._websocket_data_received = False
        
        now = time.time()
        if now - self._last_websocket_check > 120:  # Check every 2 minutes
            if not self._websocket_data_received:
                logger.warning("⚠️ No WebSocket data received in 2 minutes - checking connection")
                logger.warning("This may indicate WebSocket authentication or subscription issues")
            else:
                logger.info("✓ WebSocket data flow confirmed")
            
            self._last_websocket_check = now
            self._websocket_data_received = False
    
    def _check_all_signals(self):
        """Check all strategies for entry signals based on STOCK TRENDS ONLY."""
        
        # Need fresh chain data
        if not self.current_chain_data:
            if not hasattr(self, '_last_chain_warning'):
                self._last_chain_warning = 0
            
            now = time.time()
            if now - self._last_chain_warning > 60:  # Warn every 60 seconds
                logger.warning("⚠️ No chain data available for signal check - waiting for chain update")
                self._last_chain_warning = now
            return
        
        chain_age = time.time() - self.last_chain_update
        if chain_age > Config.CHAIN_SNAPSHOT_MAX_AGE_SECONDS:
            if not hasattr(self, '_last_chain_age_warning'):
                self._last_chain_age_warning = 0
            
            now = time.time()
            if now - self._last_chain_age_warning > 60:  # Warn every 60 seconds
                logger.warning(f"⚠️ Chain data too old ({chain_age:.0f}s > {Config.CHAIN_SNAPSHOT_MAX_AGE_SECONDS}s) - waiting for fresh data")
                self._last_chain_age_warning = now
            return
        
        # Find the best signal (may be combined) - this calls check_all_signals() internally
        best_strategy, signal_active, signal_data = self.vwap_signals.get_best_signal()
        
        if not signal_active:
            # Get all signals for status logging
            all_signals = self.vwap_signals.check_all_signals()
            # Periodic logging to show we're checking signals
            if not hasattr(self, '_last_signal_check_log'):
                self._last_signal_check_log = 0
            
            now = time.time()
            if now - self._last_signal_check_log > 300:  # Every 5 minutes
                active_signals = sum(1 for active, _ in all_signals.values() if active)
                logger.info(f"🔍 Monitoring {len(all_signals)} strategies ({active_signals} active signals)")
                
                # Log detailed signal status for debugging
                for strategy, (active, data) in all_signals.items():
                    if strategy == 'momentum' and data:
                        logger.info(f"📊 Momentum status: Price>VWAP={data.get('price_above_vwap', False)}, "
                                  f"VWAP rising={data.get('vwap_rising', False)}, "
                                  f"Volume surge={data.get('volume_surge', False)}, "
                                  f"Momentum={data.get('price_momentum', 0):.3f}")
                
                self._last_signal_check_log = now
            return
        
        # Get best contract for the signal (OPTION CONTRACT FOR ALERT PURPOSES ONLY)
        best_contract = self.contract_selector.get_best_entry_contract(signal_data, best_strategy)
        
        if not best_contract:
            logger.warning(f"{best_strategy} signal but no viable contract (direction={signal_data.get('direction')}, "
                           f"confidence={signal_data.get('confidence'):.2f})")
            return
        
        # CORRECTED: Validate contract selection matches signal direction
        direction = signal_data.get('direction', 'call')
        if not self.contract_selector.validate_contract_selection(best_contract, direction):
            logger.error(f"Contract selection validation failed for {best_strategy} {direction}")
            return

        # Log contract selection details for visibility
        logger.info(
            f"{best_strategy} {direction} candidate: {best_contract['symbol']} "
            f"(Δ{best_contract['delta']:.2f}, spread {best_contract['spread_pct']:.2f}%, "
            f"volume {best_contract['volume']})"
        )
        
        # Calculate entry price
        entry_price = self.contract_selector.calculate_entry_price(best_contract, best_strategy)
        
        # Execute entry
        self._execute_entry(best_contract, entry_price, signal_data, best_strategy)
    
    def _execute_entry(self, contract: Dict, entry_price: float, signal_data: Dict, strategy: str):
        """Execute buy alert and open position."""
        
        direction = signal_data.get('direction', 'call')
        is_call = direction == 'call'
        
        logger.warning(f"🔥 {strategy.upper()} {direction.upper()} ENTRY: {contract['symbol']} @ ${entry_price:.2f}")
        
        # Send buy alert with CORRECTED information
        success = self.alert_client.send_buy_alert(
            signal_data, 
            contract, 
            entry_price,
            strategy
        )
        
        if not success:
            logger.error("Failed to send buy alert")
        
        # Open position
        entry_data = {
            'entry_price': entry_price,
            'delta': contract.get('delta', 0),
            'iv': contract.get('iv', 0),
            'spread_pct': contract.get('spread_pct', 0),
            'signal_data': signal_data,
            'strategy': strategy,
            'is_call': is_call
        }
        
        self.risk_manager.open_position(contract['symbol'], entry_data)
        self.last_entry_time = time.time()
        
        # Set exit monitor with strategy-specific timing
        self.exit_monitor.set_position_info(strategy, is_call)
        
        # Update strategy stats
        self.strategy_stats[strategy]['signals'] += 1
        
        # Log trade
        log_trade_event(logger, "BUY", {
            'contract': contract['symbol'],
            'entry_price': entry_price,
            'strategy': strategy,
            'direction': direction,
            'iwm_price': signal_data['current_price'],
            'confidence': signal_data.get('confidence', 0)
        })
    
    def _monitor_position(self):
        """Monitor position for exit conditions with CORRECTED timing."""
        
        if not self.risk_manager.has_position():
            return
        
        pos_summary = self.risk_manager.get_position_summary()
        contract_symbol = pos_summary['contract']
        
        # Get current contract price
        contract_data = self.contract_selector.get_contract_data(contract_symbol)
        
        if not contract_data:
            # Try to get from chain if not in top contracts
            if self.current_chain_data:
                for contract in self.current_chain_data:
                    if contract.get('details', {}).get('ticker') == contract_symbol:
                        last_quote = contract.get('last_quote', {})
                        bid = last_quote.get('bid', 0)
                        ask = last_quote.get('ask', 0)
                        if bid > 0 and ask > 0:
                            contract_data = {'mid': (bid + ask) / 2.0}
                            break
            
            if not contract_data:
                logger.error(f"Cannot get price for {contract_symbol}")
                contract_data = {'mid': pos_summary['current_mark']}
        
        current_mark = contract_data['mid']
        
        # Update position
        self.risk_manager.update_position(current_mark)
        
        # Get current market data (STOCK TRENDS ONLY)
        recent_data = list(self.vwap_signals.per_sec_data)[-60:] if self.vwap_signals.per_sec_data else []
        if recent_data:
            vwap_1min = self.vwap_signals._calculate_vwap(recent_data)
            current_price = recent_data[-1]['price']
        else:
            vwap_1min = 0
            current_price = 0
        
        market_data = {
            'spot_price': current_price,
            'vwap_1min': vwap_1min
        }
        
        # Get strategy from position data
        strategy = pos_summary.get('strategy', 'momentum')
        is_call = pos_summary.get('is_call', True)
        
        # Check exit conditions with CORRECTED timing
        position_data = {
            'giveback_percent': pos_summary['giveback_percent'],
            'pnl_percent': pos_summary['pnl_percent'],
            'duration_minutes': pos_summary['duration_minutes'],
            'is_call': is_call
        }
        
        should_exit, exit_reason = self.exit_monitor.should_exit(position_data, market_data, strategy)
        
        if should_exit:
            self._execute_exit(exit_reason, strategy)
    
    
    def _execute_exit(self, reason: str, strategy: str = 'momentum'):
        """Execute sell alert and close position."""
        
        logger.warning(f"📤 {strategy.upper()} EXIT: {reason}")
        
        # Get position data
        pos_summary = self.risk_manager.get_position_summary()
        if not pos_summary:
            return
        
        # Get market data (STOCK TRENDS ONLY)
        recent_data = list(self.vwap_signals.per_sec_data)[-60:] if self.vwap_signals.per_sec_data else []
        if recent_data:
            vwap_1min = self.vwap_signals._calculate_vwap(recent_data)
            current_price = recent_data[-1]['price']
        else:
            vwap_1min = 0
            current_price = 0
        
        market_data = {
            'spot_price': current_price,
            'vwap_1min': vwap_1min
        }
        
        # Get P&L stats
        from pnl_tracker import get_tracker
        pnl_tracker = get_tracker()
        current_stats = pnl_tracker.get_stats()
        
        # Send sell alert with CORRECTED information
        success = self.alert_client.send_sell_alert(pos_summary, market_data, current_stats, strategy)
        
        if not success:
            logger.error("Failed to send sell alert")
        
        # Update strategy stats
        pnl_pct = pos_summary['pnl_percent']
        if pnl_pct > 0:
            self.strategy_stats[strategy]['wins'] += 1
        else:
            self.strategy_stats[strategy]['losses'] += 1
        
        # Calculate win rate
        total_trades = self.strategy_stats[strategy]['wins'] + self.strategy_stats[strategy]['losses']
        if total_trades > 0:
            self.strategy_stats[strategy]['win_rate'] = (self.strategy_stats[strategy]['wins'] / total_trades) * 100
        
        # Log trade
        log_trade_event(logger, "SELL", {
            'contract': pos_summary['contract'],
            'entry_price': pos_summary['entry_price'],
            'exit_price': pos_summary['current_mark'],
            'pnl_percent': pos_summary['pnl_percent'],
            'duration_min': pos_summary['duration_minutes'],
            'reason': reason,
            'strategy': strategy
        })
        
        # Record P&L
        pnl_tracker.record_trade(
            entry_price=pos_summary['entry_price'],
            exit_price=pos_summary['current_mark'],
            contract_symbol=pos_summary['contract'],
            exit_reason=reason,
            blackout_mode=False
        )
        
        # Close position
        self.risk_manager.close_position()
        
        # Reset exit monitor
        self.exit_monitor = CorrectedExitMonitor()
    
    def shutdown(self):
        """Gracefully shutdown the system."""
        if not self.running:
            return
        
        logger.warning("Shutting down corrected multi-strategy system...")
        self.running = False
        self.shutdown_event.set()
        
        # Close any open position
        if self.risk_manager.has_position():
            self._execute_exit("System shutdown")
        
        # Disconnect WebSocket
        self.ws_stocks.disconnect()
        
        # Send shutdown alert
        self.alert_client.send_system_alert(
            f"CORRECTED Multi-Strategy System stopped at {get_et_time().strftime('%H:%M:%S ET')}",
            priority=0
        )
        
        logger.info("✓ Strat-0DTE shutdown complete")
    
    def _check_strat_signals(self):
        """Check for Strat-0DTE trade signals."""
        # Get current bias
        bias_data = self.bias_engine.get_daily_bias()
        bias = bias_data.get('bias', 'None')
        
        if bias == 'None':
            return
        
        # Check for trade signal from execution engine
        signal = self.execution_engine._check_5min_triggers()
        
        if signal:
            # Map signal to option contract
            option_data = self.options_mapper.map_signal_to_option(signal)
            
            if option_data:
                # Open position
                self.position_manager.open_position(option_data, signal)
                
                # Send entry alert
                self._send_entry_alert(option_data, signal)
                
                # Update entry time
                self.last_entry_time = time.time()
    
    def _manage_positions(self):
        """Manage active positions."""
        if not self.position_manager.current_position:
            return
        
        # Get current market data
        if not hasattr(self, 'current_stock_data') or not self.current_stock_data:
            return
        
        current_price = self.current_stock_data.get('current_price', 0)
        current_vwap = self.execution_engine.get_current_vwap()
        
        if current_price == 0:
            return
        
        # Update position and check for exits/scaling
        exit_signal = self.position_manager.update_position(current_price, current_vwap)
        
        if exit_signal:
            # Handle exit or scaling
            if exit_signal['action'] in ['SCALE1', 'SCALE2']:
                self._handle_scaling(exit_signal)
            elif exit_signal['action'] == 'EXIT':
                self._handle_exit(exit_signal)
    
    def _handle_scaling(self, scale_signal: Dict):
        """Handle position scaling."""
        action = scale_signal['action']
        pnl_pct = scale_signal['pnl_pct']
        
        logger.info(f"📊 {action}: +{pnl_pct:.1f}% profit - Consider scaling position")
        
        # Send scaling alert
        self.alert_client.send_alert(
            title=f"📊 IWM-5-VWAP {action}",
            message=f"Position at +{pnl_pct:.1f}% profit\nConsider scaling position",
            priority=1
        )
    
    def _handle_exit(self, exit_signal: Dict):
        """Handle position exit."""
        reason = exit_signal['reason']
        
        # Close position
        position_data = self.position_manager.close_position(reason)
        
        if position_data:
            # Send exit alert
            self._send_exit_alert(position_data, reason)
            
            # Update risk manager
            self.risk_manager.close_position(reason)
            
            # Update entry time for cooldown
            self.last_entry_time = time.time()
    
    def _send_entry_alert(self, option_data: Dict, signal: Dict):
        """Send entry alert."""
        title = f"🚀 IWM-5-VWAP {signal['bias']} ENTRY"
        
        message = f"""IWM-5-VWAP {signal['bias']} Signal
        
Contract: {option_data['contract']}
Strike: ${option_data['strike']:.2f}
Entry: ${option_data['ask']:.2f}
Spot: ${signal['spot']:.2f}
VWAP: ${signal['vwap']:.2f}
Trigger: ${signal['trigger']:.2f}

STOP: Below VWAP / {signal['trigger']:.2f}
PARTIALS: +30%, +70%"""
        
        self.alert_client.send_alert(title, message, priority=1)
    
    def _send_exit_alert(self, position_data: Dict, reason: str):
        """Send exit alert."""
        title = f"📤 IWM-5-VWAP EXIT"
        
        message = f"""IWM-5-VWAP Position Closed
        
Contract: {position_data['contract']}
Reason: {reason}
Entry: ${position_data['entry_price']:.2f}
Peak: ${position_data.get('peak_price', 0):.2f}
Final P&L: {position_data.get('final_pnl_pct', 0):+.1f}%"""
        
        self.alert_client.send_alert(title, message, priority=1)


def main():
    """Entry point for corrected multi-strategy system."""
    try:
        system = CorrectedMultiStrategySystem()
        system.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()