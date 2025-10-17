"""
IWM Strategy Orchestrator
Main orchestrator for the complete IWM strategy implementation.
Coordinates all strategy components and manages the trading flow.
"""
import time
import signal
import sys
import threading
from typing import Dict, Optional, Tuple
from datetime import datetime
from logger import setup_logger
from config import Config
from utils import get_et_time, is_market_hours

# Strategy components
from overnight_analysis import OvernightBarAnalysis
from session_vwap import SessionVWAP
from five_minute_confirmation import FiveMinuteConfirmation
from position_sizing import PositionSizing
from hard_invalidation import HardInvalidation
from contract_selector import CorrectedMultiStrategyContractSelector
from alerts_complete import IWM5VWAPCompleteAlertClient
from polygon_client import PolygonWebSocketClient, PolygonRESTClient

logger = setup_logger("StrategyOrchestrator")


class IWMStrategyOrchestrator:
    """
    Main orchestrator for the IWM strategy.
    Coordinates all components and manages the complete trading flow.
    """
    
    def __init__(self):
        # Initialize strategy components
        self.overnight_analysis = OvernightBarAnalysis()
        self.session_vwap = SessionVWAP()
        self.five_min_confirmation = FiveMinuteConfirmation()
        self.position_sizing = PositionSizing()
        self.hard_invalidation = HardInvalidation()
        self.contract_selector = CorrectedMultiStrategyContractSelector()
        self.alerts = IWM5VWAPCompleteAlertClient()
        
        # Data clients
        self.polygon_ws = PolygonWebSocketClient("stocks")
        self.polygon_rest = PolygonRESTClient()
        
        # Strategy state
        self.strategy_active = False
        self.current_bias: Optional[str] = None
        self.trigger_levels: Tuple[float, float] = (0.0, 0.0)
        self.entry_window_active = False
        
        # Position tracking
        self.active_positions: Dict = {}
        self.daily_pnl: float = 0.0
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def start_strategy(self):
        """Start the complete strategy."""
        logger.info("Starting IWM Strategy Orchestrator")
        
        try:
            # Initialize components
            self._initialize_components()
            
            # Start data feeds
            self._start_data_feeds()
            
            # Main strategy loop
            self._run_strategy_loop()
            
        except Exception as e:
            logger.error(f"Strategy error: {e}")
            self._cleanup()
            raise
    
    def _initialize_components(self):
        """Initialize all strategy components."""
        logger.info("Initializing strategy components")
        
        # Setup WebSocket handlers
        self.polygon_ws.register_handler('stocks.aggregate_per_second', self._handle_stock_data)
        self.polygon_ws.register_handler('stocks.aggregate_per_minute', self._handle_minute_data)
        
        # Start session VWAP
        self.session_vwap.start_session()
        
        logger.info("Strategy components initialized")
    
    def _start_data_feeds(self):
        """Start data feeds using enhanced Polygon client."""
        logger.info("Starting enhanced data feeds")
        
        try:
            # Import enhanced client
            from enhanced_polygon_client import EnhancedPolygonClient
            
            # Initialize enhanced client
            self.enhanced_polygon = EnhancedPolygonClient()
            
            # Connect to multiple Polygon services
            self.enhanced_polygon.connect_all_services()
            
            logger.info("Enhanced data feeds started with multiple Polygon services")
            
        except ImportError:
            # Fallback to original client
            logger.warning("Enhanced client not available, using original client")
            self.polygon_ws.connect_with_retry()
            self.polygon_ws.subscribe(f"stocks.{Config.UNDERLYING_SYMBOL}")
            logger.info("Data feeds started with original client")
    
    def _run_strategy_loop(self):
        """Main strategy execution loop."""
        logger.info("Starting strategy loop")
        self.strategy_active = True
        
        while self.strategy_active:
            try:
                current_time = get_et_time()
                
                # Check if market is open
                if not is_market_hours():
                    time.sleep(60)  # Wait 1 minute if market closed
                    continue
                
                # Process overnight analysis (at 03:00 ET)
                if self._should_analyze_overnight(current_time):
                    self._process_overnight_analysis()
                
                # Check entry windows
                if self._is_in_entry_window(current_time):
                    self._process_entry_window()
                
                # Monitor active positions
                if self.active_positions:
                    self._monitor_positions()
                
                # Sleep for 1 second
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Strategy loop error: {e}")
                time.sleep(5)  # Wait 5 seconds on error
    
    def _should_analyze_overnight(self, current_time: datetime) -> bool:
        """Check if we should analyze overnight data."""
        return (current_time.hour == 3 and 
                current_time.minute == 0 and 
                current_time.second < 30)
    
    def _process_overnight_analysis(self):
        """Process overnight bar analysis."""
        logger.info("Processing overnight analysis")
        
        # Get overnight bar data (this would come from historical data)
        # For now, we'll simulate the analysis
        overnight_bar = {
            'timestamp': time.time(),
            'open': 245.0,  # This would be actual data
            'high': 247.0,
            'low': 244.0,
            'close': 246.5,
            'volume': 1000000
        }
        
        # Analyze overnight bar
        analysis_result = self.overnight_analysis.update_overnight_bar(overnight_bar)
        
        if analysis_result['status'] == 'complete':
            self.current_bias = analysis_result['bias']
            self.trigger_levels = (analysis_result['trigger_high'], analysis_result['trigger_low'])
            
            logger.info(f"Overnight analysis complete: {self.current_bias}")
            
            # Send bias alert
            if self.current_bias:
                self.alerts.send_bias_alert(self.current_bias, analysis_result)
    
    def _is_in_entry_window(self, current_time: datetime) -> bool:
        """Check if we're in an entry window."""
        current_time_str = current_time.strftime('%H:%M')
        
        # Primary window: 09:45-11:00
        if '09:45' <= current_time_str <= '11:00':
            return True
        
        # Secondary window: 13:30-14:15
        if '13:30' <= current_time_str <= '14:15':
            return True
        
        return False
    
    def _process_entry_window(self):
        """Process entry window logic."""
        if not self.current_bias:
            return  # No bias set yet
        
        # Check if we can enter new position
        if not self._can_enter_new_position():
            return
        
        # Get current market data
        current_data = self._get_current_market_data()
        if not current_data:
            return
        
        # Check 5-minute confirmation
        confirmation_result = self.five_min_confirmation.update(
            current_data, self.current_bias, self.trigger_levels
        )
        
        if confirmation_result.get('entry_signal'):
            self._execute_entry(current_data)
    
    def _can_enter_new_position(self) -> bool:
        """Check if we can enter a new position."""
        # Check position sizing limits
        position_summary = self.position_sizing.get_position_summary()
        
        if position_summary['total_positions'] >= 2:  # Max 2 positions
            return False
        
        if position_summary['daily_pnl'] <= -700:  # Daily loss limit
            return False
        
        return True
    
    def _execute_entry(self, market_data: Dict):
        """Execute entry logic."""
        logger.info(f"Executing entry for bias: {self.current_bias}")
        
        # Get option chain data
        option_chain = self.polygon_rest.get_options_chain(Config.UNDERLYING_SYMBOL)
        if not option_chain:
            logger.error("No option chain data available")
            return
        
        # Select contracts
        selected_contracts = self.contract_selector.filter_and_rank_contracts(option_chain)
        
        if not selected_contracts.get(self.current_bias):
            logger.error(f"No {self.current_bias} contracts available")
            return
        
        # Get best contract
        best_contract = selected_contracts[self.current_bias][0]
        
        # Calculate position size
        position_size = self.position_sizing.calculate_position_size(
            self.current_bias,
            best_contract['price'],
            self.trigger_levels[0] if self.current_bias == 'calls' else self.trigger_levels[1],
            market_data['price']
        )
        
        if position_size['status'] != 'approved':
            logger.error(f"Position sizing failed: {position_size['reason']}")
            return
        
        # Add position
        position_data = {
            'bias': self.current_bias,
            'option_price': best_contract['price'],
            'num_contracts': position_size['num_contracts'],
            'position_size': position_size['position_size'],
            'trigger_levels': self.trigger_levels
        }
        
        if self.position_sizing.add_position(position_data):
            # Add to invalidation tracking
            self.hard_invalidation.add_position(position_data)
            
            # Send entry alert
            self.alerts.send_entry_alert(position_data, best_contract)
            
            logger.info(f"Position entered: {self.current_bias} - {position_size['num_contracts']} contracts")
    
    def _monitor_positions(self):
        """Monitor active positions."""
        for position_id, position in self.active_positions.items():
            # Update position P&L
            pnl_result = self.position_sizing.update_position_pnl(
                position_id, position['current_price']
            )
            
            # Check for scaling opportunities
            if pnl_result.get('scaling_recommendations'):
                self._process_scaling_opportunities(position_id, pnl_result['scaling_recommendations'])
            
            # Check for invalidation
            invalidation_result = self.hard_invalidation.update(
                position, position['current_price'], self.trigger_levels, 
                self.session_vwap.get_vwap_control_status()
            )
            
            if invalidation_result.get('action') == 'close_position':
                self._close_position(position_id, invalidation_result['reason'])
    
    def _process_scaling_opportunities(self, position_id: int, scaling_recommendations: list):
        """Process scaling opportunities."""
        for recommendation in scaling_recommendations:
            scale_result = self.position_sizing.execute_scale(
                position_id, recommendation['scale']
            )
            
            if scale_result['status'] == 'executed':
                # Send scaling alert
                self.alerts.send_scaling_alert(position_id, recommendation, scale_result)
                
                logger.info(f"Scale executed: {recommendation['scale']} for position {position_id}")
    
    def _close_position(self, position_id: int, reason: str):
        """Close position."""
        close_result = self.position_sizing.close_position(position_id, reason)
        
        if close_result['status'] == 'closed':
            # Remove from invalidation tracking
            self.hard_invalidation.remove_position(position_id)
            
            # Send close alert
            self.alerts.send_close_alert(position_id, reason, close_result['final_pnl'])
            
            # Remove from active positions
            if position_id in self.active_positions:
                del self.active_positions[position_id]
            
            logger.info(f"Position closed: {position_id} - Reason: {reason}")
    
    def _get_current_market_data(self) -> Optional[Dict]:
        """Get current market data."""
        # This would get real-time data from Polygon
        # For now, return simulated data
        return {
            'timestamp': time.time(),
            'price': 245.5,  # This would be actual price
            'volume': 1000
        }
    
    def _handle_stock_data(self, data: Dict):
        """Handle stock data from WebSocket."""
        # Update session VWAP
        vwap_result = self.session_vwap.update(data)
        
        # Update 5-minute confirmation
        if self.current_bias:
            confirmation_result = self.five_min_confirmation.update(
                data, self.current_bias, self.trigger_levels
            )
            
            if confirmation_result.get('entry_signal'):
                self._execute_entry(data)
    
    def _handle_minute_data(self, data: Dict):
        """Handle minute data from WebSocket."""
        # Process minute-level data if needed
        pass
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.strategy_active = False
        self._cleanup()
        sys.exit(0)
    
    def _cleanup(self):
        """Cleanup resources."""
        logger.info("Cleaning up resources")
        
        # Close WebSocket connection
        if self.polygon_ws:
            self.polygon_ws.disconnect()
        
        # End session VWAP
        self.session_vwap.end_session()
        
        logger.info("Cleanup complete")
    
    def get_strategy_status(self) -> Dict:
        """Get current strategy status."""
        return {
            'strategy_active': self.strategy_active,
            'current_bias': self.current_bias,
            'trigger_levels': self.trigger_levels,
            'entry_window_active': self.entry_window_active,
            'active_positions': len(self.active_positions),
            'daily_pnl': self.daily_pnl,
            'position_summary': self.position_sizing.get_position_summary(),
            'invalidation_status': self.hard_invalidation.get_invalidation_status()
        }
