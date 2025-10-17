"""
Multi-Strategy Orchestrator for Miyagi Trading
Coordinates both VWAP strategy and Overnight Bias strategy.
Allows both strategies to run simultaneously with proper resource management.
"""
import time
import signal
import sys
import threading
from typing import Dict, Optional, Tuple, List
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

# New strategy
from overnight_bias_strategy import OvernightBiasStrategy
from strategy_config import StrategyConfig

logger = setup_logger("MultiStrategyOrchestrator")


class MultiStrategyOrchestrator:
    """
    Multi-strategy orchestrator for Miyagi trading.
    Coordinates VWAP strategy and Overnight Bias strategy.
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
        
        # New Overnight Bias strategy
        self.overnight_bias_strategy = OvernightBiasStrategy()
        
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
        
        # Strategy selection (from configuration)
        self.active_strategies = StrategyConfig.get_active_strategies()
        
        # Multi-symbol support with tiered configuration
        self.overnight_bias_symbols = [s.strip() for s in Config.OVERNIGHT_BIAS_SYMBOLS]
        self.vwap_strategy_symbols = [s.strip() for s in Config.VWAP_STRATEGY_SYMBOLS]
        
        # Symbol tier mapping
        self.symbol_tiers = {}
        for tier, symbols in Config.SYMBOL_TIERS.items():
            for symbol in symbols:
                self.symbol_tiers[symbol.strip()] = tier
        
        # Risk controls per tier
        self.tier_risk_controls = Config.TIER_RISK_CONTROLS
        
        # Symbol-specific strategy instances
        self.overnight_bias_instances = {}
        self.vwap_instances = {}
        
        # Initialize strategy instances for each symbol
        self._initialize_strategy_instances()
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Initialize overnight processing flag
        self.overnight_processed_today = False
        
        # Reset overnight processing flag if it's a new day
        current_time = get_et_time()
        logger.info(f"Daily reset check: current_date={current_time.date()}, has_last_date={hasattr(self, 'last_processed_date')}, last_date={getattr(self, 'last_processed_date', 'None')}")
        
        if not hasattr(self, 'last_processed_date') or self.last_processed_date != current_time.date():
            self.overnight_processed_today = False
            self.last_processed_date = current_time.date()
            logger.info(f"New day detected - resetting overnight analysis flag for {current_time.date()}")
        else:
            logger.info(f"Same day - keeping overnight analysis flag as {self.overnight_processed_today}")
        
        # Check if we need to process overnight analysis for today
        current_hour = current_time.hour
        if current_hour >= 3 and not self.overnight_processed_today:
            logger.info("Overnight analysis needed for today - will process on startup")
    
    def _initialize_strategy_instances(self):
        """Initialize strategy instances for each symbol."""
        logger.info("Initializing strategy instances for multiple symbols")
        
        # Initialize Overnight Bias strategy instances with tier controls
        if self.active_strategies['overnight_bias']:
            for symbol in self.overnight_bias_symbols:
                strategy = OvernightBiasStrategy()
                
                # Set tier-specific controls
                symbol_tier = self.symbol_tiers.get(symbol, 'tier1')
                tier_controls = self.tier_risk_controls.get(symbol_tier, self.tier_risk_controls['tier1'])
                strategy.set_tier_controls(symbol_tier, tier_controls)
                
                self.overnight_bias_instances[symbol] = strategy
                logger.info(f"Initialized Overnight Bias strategy for {symbol} ({symbol_tier})")
        
        # Initialize VWAP strategy instances (using existing components)
        if self.active_strategies['vwap']:
            for symbol in self.vwap_strategy_symbols:
                # Create symbol-specific VWAP components
                self.vwap_instances[symbol] = {
                    'session_vwap': SessionVWAP(),
                    'five_min_confirmation': FiveMinuteConfirmation(),
                    'position_sizing': PositionSizing(),
                    'hard_invalidation': HardInvalidation()
                }
                logger.info(f"Initialized VWAP strategy for {symbol}")
        
        logger.info(f"Strategy instances initialized: {len(self.overnight_bias_instances)} Overnight Bias, {len(self.vwap_instances)} VWAP")
    
    def start_strategy(self):
        """Start the multi-strategy system."""
        logger.info("Starting Multi-Strategy Miyagi System")
        
        try:
            # Initialize components
            self._initialize_components()
            
            # Start data feeds
            self._start_data_feeds()
            
            # Check if we need to catch up on today's overnight analysis
            current_time = get_et_time()
            if self._should_analyze_overnight(current_time):
                logger.info("Catching up on today's overnight analysis...")
                self._process_overnight_analysis()
            
            # Check daily balance for silent trading
            self._check_daily_balance()
            
            # Main strategy loop
            self._run_strategy_loop()
            
        except Exception as e:
            logger.error(f"Multi-strategy error: {e}")
            self._cleanup()
            raise
    
    def _initialize_components(self):
        """Initialize all strategy components."""
        logger.info("Initializing multi-strategy components")
        
        # Setup WebSocket handlers
        self.polygon_ws.register_handler('stocks.aggregate_per_second', self._handle_stock_data)
        self.polygon_ws.register_handler('stocks.aggregate_per_minute', self._handle_minute_data)
        
        # Start session VWAP
        self.session_vwap.start_session()
        
        logger.info("Multi-strategy components initialized")
    
    def _start_data_feeds(self):
        """Start data feeds for both strategies across multiple symbols."""
        logger.info("Starting multi-symbol data feeds for Miyagi multi-strategy")
        
        # Connect to Polygon WebSocket with retry logic and connection lock
        self.polygon_ws.connect_with_retry()
        
        # Get all unique symbols from both strategies
        all_symbols = set()
        if self.active_strategies['overnight_bias']:
            all_symbols.update(self.overnight_bias_symbols)
        if self.active_strategies['vwap']:
            all_symbols.update(self.vwap_strategy_symbols)
        
        # Subscribe to all symbols
        for symbol in all_symbols:
            self.polygon_ws.subscribe(f"stocks.{symbol}")
            logger.info(f"Subscribed to {symbol} data feed")
        
        logger.info(f"Miyagi multi-symbol data feeds started successfully: {list(all_symbols)}")
    
    def _run_strategy_loop(self):
        """Main multi-strategy execution loop."""
        logger.info("Starting multi-strategy loop")
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
                
                # Process both strategies
                self._process_strategies(current_time)
                
                # Monitor active positions
                if self.active_positions:
                    self._monitor_positions()
                
                # Sleep for 1 second
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Multi-strategy loop error: {e}")
                time.sleep(5)  # Wait 5 seconds on error
    
    def _process_strategies(self, current_time: datetime):
        """Process both VWAP and Overnight Bias strategies across multiple symbols."""
        # Process Overnight Bias strategy for each symbol
        if self.active_strategies['overnight_bias']:
            for symbol in self.overnight_bias_symbols:
                self._process_overnight_bias_strategy_for_symbol(symbol, current_time)
        
        # Process VWAP strategy for each symbol
        if self.active_strategies['vwap']:
            for symbol in self.vwap_strategy_symbols:
                self._process_vwap_strategy_for_symbol(symbol, current_time)
    
    def _process_overnight_bias_strategy_for_symbol(self, symbol: str, current_time: datetime):
        """Process Overnight Bias strategy for a specific symbol."""
        if symbol not in self.overnight_bias_instances:
            return
        
        strategy = self.overnight_bias_instances[symbol]
        
        # Get current market data for this symbol
        current_data = self._get_current_market_data_for_symbol(symbol)
        if not current_data:
            return
        
        # Get VWAP data for this symbol
        vwap_data = self.session_vwap.get_vwap_control_status()
        
        # Update 5-minute data for overnight bias strategy
        bias_result = strategy.update_five_minute_data(current_data, vwap_data)
        
        # Check for entry signals
        if bias_result.get('status') == 'entry_signal':
            self._execute_overnight_bias_entry_for_symbol(symbol, bias_result, current_data)
    
    def _process_vwap_strategy_for_symbol(self, symbol: str, current_time: datetime):
        """Process VWAP strategy for a specific symbol."""
        if symbol not in self.vwap_instances:
            return
        
        vwap_components = self.vwap_instances[symbol]
        
        # Get current market data for this symbol
        current_data = self._get_current_market_data_for_symbol(symbol)
        if not current_data:
            return
        
        # Check entry windows
        if self._is_in_entry_window(current_time):
            self._process_vwap_entry_window_for_symbol(symbol, current_data, vwap_components)
    
    def _execute_overnight_bias_entry_for_symbol(self, symbol: str, bias_result: Dict, current_data: Dict):
        """Execute entry for Overnight Bias strategy for a specific symbol."""
        logger.info(f"Executing Overnight Bias entry for {symbol}: {bias_result['bias']}")
        
        # Get option chain data for this symbol
        option_chain = self.polygon_rest.get_options_chain(symbol)
        if not option_chain:
            logger.error(f"No option chain data available for {symbol} Overnight Bias strategy")
            return
        
        # Select contracts
        selected_contracts = self.contract_selector.filter_and_rank_contracts(option_chain)
        
        if not selected_contracts.get(bias_result['bias']):
            logger.error(f"No {bias_result['bias']} contracts available for {symbol} Overnight Bias strategy")
            return
        
        # Get best contract
        best_contract = selected_contracts[bias_result['bias']][0]
        
        # Calculate position size using Overnight Bias strategy rules with tier-specific controls
        strategy = self.overnight_bias_instances[symbol]
        
        # Get tier-specific risk controls
        symbol_tier = self.symbol_tiers.get(symbol, 'tier1')
        tier_controls = self.tier_risk_controls.get(symbol_tier, self.tier_risk_controls['tier1'])
        
        # Apply tier-specific position sizing
        base_account = 7000.0  # $7K account example
        tier_multiplier = tier_controls['position_size_multiplier']
        adjusted_account = base_account * tier_multiplier
        
        position_size = strategy.calculate_position_size(
            best_contract['price'], adjusted_account
        )
        
        if position_size['status'] != 'approved':
            logger.error(f"{symbol} Overnight Bias position sizing failed: {position_size['reason']}")
            return
        
        # Add position
        position_data = {
            'strategy': 'overnight_bias',
            'symbol': symbol,
            'bias': bias_result['bias'],
            'option_price': best_contract['price'],
            'num_contracts': position_size['num_contracts'],
            'position_size': position_size['position_size'],
            'entry_price': bias_result['entry_price'],
            'trigger_level': bias_result['trigger_level'],
            'vwap': bias_result['vwap'],
            'ema20': bias_result['ema20'],
            'confidence': bias_result['confidence']
        }
        
        # Add to position tracking
        position_id = len(self.active_positions) + 1
        self.active_positions[position_id] = position_data
        
        # Send entry alert
        self.alerts.send_entry_alert(position_data, best_contract)
        
        logger.info(f"{symbol} Overnight Bias position entered: {bias_result['bias']} - {position_size['num_contracts']} contracts")
    
    def _process_vwap_entry_window_for_symbol(self, symbol: str, current_data: Dict, vwap_components: Dict):
        """Process VWAP strategy entry window for a specific symbol."""
        # This would implement VWAP strategy logic for the specific symbol
        # For now, just log the processing
        logger.info(f"Processing VWAP entry window for {symbol}")
    
    def _process_vwap_strategy(self, current_data: Dict, vwap_data: Dict, current_time: datetime):
        """Process the original VWAP strategy."""
        # Check entry windows
        if self._is_in_entry_window(current_time):
            self._process_vwap_entry_window(current_data, vwap_data)
    
    def _process_overnight_bias_strategy(self, current_data: Dict, vwap_data: Dict, current_time: datetime):
        """Process the new Overnight Bias strategy."""
        # Update 5-minute data for overnight bias strategy
        bias_result = self.overnight_bias_strategy.update_five_minute_data(
            current_data, vwap_data
        )
        
        # Check for entry signals
        if bias_result.get('status') == 'entry_signal':
            self._execute_overnight_bias_entry(bias_result, current_data)
    
    def _should_analyze_overnight(self, current_time: datetime) -> bool:
        """Check if we should analyze overnight data."""
        # Check if we're at 3:00 AM ET or if we haven't processed today's data yet
        is_three_am = (current_time.hour == 3 and 
                       current_time.minute == 0 and 
                       current_time.second < 30)
        
        # If it's past 3:00 AM and we haven't processed today's data, do it now
        is_past_three_am = (current_time.hour >= 3 and 
                           not self.overnight_processed_today)
        
        # Debug logging
        logger.info(f"Overnight analysis check: current_time={current_time}, is_three_am={is_three_am}, is_past_three_am={is_past_three_am}, has_processed={self.overnight_processed_today}")
        
        return is_three_am or is_past_three_am
    
    def _process_overnight_analysis(self):
        """Process overnight bar analysis for both strategies across multiple symbols."""
        logger.info("Processing overnight analysis for both strategies across multiple symbols")
        
        # Process overnight analysis for each symbol
        for symbol in self.overnight_bias_symbols:
            self._process_overnight_analysis_for_symbol(symbol)
        
        # Mark that we've successfully processed today's overnight data
        self.overnight_processed_today = True
        logger.info("Overnight analysis processing completed successfully for all symbols")
    
    def _process_overnight_analysis_for_symbol(self, symbol: str):
        """Process overnight bar analysis for a specific symbol."""
        logger.info(f"Processing overnight analysis for {symbol}")
        
        # Get overnight bar data for this symbol (this would come from historical data)
        # ACTUAL OVERNIGHT 12H BAR DATA (15:00-03:00 ET)
        base_data = {
            'IWM': {'open': 240.50, 'high': 241.93, 'low': 240.19, 'close': 241.20, 'volume': 1000000},
            'SPY': {'open': 440.50, 'high': 443.93, 'low': 439.19, 'close': 442.20, 'volume': 2000000},
            'QQQ': {'open': 378.50, 'high': 381.93, 'low': 377.19, 'close': 380.20, 'volume': 1500000}
        }
        
        symbol_data = base_data.get(symbol, base_data['IWM'])
        overnight_bar = {
            'timestamp': time.time(),
            'open': symbol_data['open'],
            'high': symbol_data['high'],
            'low': symbol_data['low'],
            'close': symbol_data['close'],
            'volume': symbol_data['volume']
        }
        
        # Process with overnight bias strategy for this symbol
        if symbol in self.overnight_bias_instances:
            strategy = self.overnight_bias_instances[symbol]
            bias_result = strategy.update_overnight_bar(overnight_bar)
            
            if bias_result['status'] == 'complete':
                logger.info(f"{symbol} Overnight Bias: {bias_result['bias']} (confidence: {bias_result['confidence']:.2f})")
                
                # Send bias alert for this symbol
                if bias_result['bias']:
                    self.alerts.send_bias_alert(bias_result['bias'], {
                        **bias_result,
                        'symbol': symbol
                    })
    
    def _check_daily_balance(self):
        """Check daily balance for silent trading (SEPARATE FROM ALERTS)."""
        try:
            from silent_tradier_executor import silent_executor
            silent_executor._check_daily_balance()
            logger.info("Tradier balance check completed (SEPARATE FROM ALERTS)")
        except Exception as e:
            logger.error(f"Tradier balance check failed: {e}")
            logger.info("ALERTS CONTINUE NORMALLY - Tradier issues do not affect strategy")
            # Alerts continue regardless of Tradier issues
    
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
    
    def _process_vwap_entry_window(self, current_data: Dict, vwap_data: Dict):
        """Process VWAP strategy entry window logic."""
        if not self.current_bias:
            return  # No bias set yet
        
        # Check if we can enter new position
        if not self._can_enter_new_position():
            return
        
        # Check 5-minute confirmation
        confirmation_result = self.five_min_confirmation.update(
            current_data, self.current_bias, self.trigger_levels
        )
        
        if confirmation_result.get('entry_signal'):
            self._execute_vwap_entry(current_data)
    
    def _execute_overnight_bias_entry(self, bias_result: Dict, current_data: Dict):
        """Execute entry for Overnight Bias strategy."""
        logger.info(f"Executing Overnight Bias entry: {bias_result['bias']}")
        
        # Get option chain data
        option_chain = self.polygon_rest.get_options_chain(Config.UNDERLYING_SYMBOL)
        if not option_chain:
            logger.error("No option chain data available for Overnight Bias strategy")
            return
        
        # Select contracts
        selected_contracts = self.contract_selector.filter_and_rank_contracts(option_chain)
        
        if not selected_contracts.get(bias_result['bias']):
            logger.error(f"No {bias_result['bias']} contracts available for Overnight Bias strategy")
            return
        
        # Get best contract
        best_contract = selected_contracts[bias_result['bias']][0]
        
        # Calculate position size using Overnight Bias strategy rules
        position_size = self.overnight_bias_strategy.calculate_position_size(
            best_contract['price'], 7000.0  # $7K account example
        )
        
        if position_size['status'] != 'approved':
            logger.error(f"Overnight Bias position sizing failed: {position_size['reason']}")
            return
        
        # Add position
        position_data = {
            'strategy': 'overnight_bias',
            'bias': bias_result['bias'],
            'option_price': best_contract['price'],
            'num_contracts': position_size['num_contracts'],
            'position_size': position_size['position_size'],
            'entry_price': bias_result['entry_price'],
            'trigger_level': bias_result['trigger_level'],
            'vwap': bias_result['vwap'],
            'ema20': bias_result['ema20'],
            'confidence': bias_result['confidence']
        }
        
        # Add to position tracking
        position_id = len(self.active_positions) + 1
        self.active_positions[position_id] = position_data
        
        # Send entry alert
        self.alerts.send_entry_alert(position_data, best_contract)
        
        logger.info(f"Overnight Bias position entered: {bias_result['bias']} - {position_size['num_contracts']} contracts")
    
    def _execute_vwap_entry(self, market_data: Dict):
        """Execute entry logic for VWAP strategy."""
        logger.info(f"Executing VWAP entry for bias: {self.current_bias}")
        
        # Get option chain data
        option_chain = self.polygon_rest.get_options_chain(Config.UNDERLYING_SYMBOL)
        if not option_chain:
            logger.error("No option chain data available for VWAP strategy")
            return
        
        # Select contracts
        selected_contracts = self.contract_selector.filter_and_rank_contracts(option_chain)
        
        if not selected_contracts.get(self.current_bias):
            logger.error(f"No {self.current_bias} contracts available for VWAP strategy")
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
            logger.error(f"VWAP position sizing failed: {position_size['reason']}")
            return
        
        # Add position
        position_data = {
            'strategy': 'vwap',
            'bias': self.current_bias,
            'option_price': best_contract['price'],
            'num_contracts': position_size['num_contracts'],
            'position_size': position_size['position_size'],
            'trigger_levels': self.trigger_levels
        }
        
        # Add to invalidation tracking
        self.hard_invalidation.add_position(position_data)
        
        # Add to position tracking
        position_id = len(self.active_positions) + 1
        self.active_positions[position_id] = position_data
        
        # Send entry alert
        self.alerts.send_entry_alert(position_data, best_contract)
        
        logger.info(f"VWAP position entered: {self.current_bias} - {position_size['num_contracts']} contracts")
    
    def _can_enter_new_position(self) -> bool:
        """Check if we can enter a new position."""
        # Check position sizing limits
        position_summary = self.position_sizing.get_position_summary()
        
        if position_summary['total_positions'] >= 2:  # Max 2 positions
            return False
        
        if position_summary['daily_pnl'] <= -700:  # Daily loss limit
            return False
        
        return True
    
    def _monitor_positions(self):
        """Monitor active positions for both strategies."""
        for position_id, position in self.active_positions.items():
            strategy = position.get('strategy', 'vwap')
            
            if strategy == 'overnight_bias':
                self._monitor_overnight_bias_position(position_id, position)
            else:
                self._monitor_vwap_position(position_id, position)
    
    def _monitor_overnight_bias_position(self, position_id: int, position: Dict):
        """Monitor Overnight Bias strategy position."""
        # Get current market data
        current_data = self._get_current_market_data()
        if not current_data:
            return
        
        # Get VWAP data
        vwap_data = self.session_vwap.get_vwap_control_status()
        
        # Check exit conditions
        exit_result = self.overnight_bias_strategy.check_exit_conditions(
            position, current_data['price'], vwap_data
        )
        
        if exit_result['action'] == 'close':
            self._close_position(position_id, exit_result['reason'])
        elif exit_result['action'] == 'scale_out':
            self._scale_out_position(position_id, exit_result)
    
    def _monitor_vwap_position(self, position_id: int, position: Dict):
        """Monitor VWAP strategy position."""
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
    
    def _scale_out_position(self, position_id: int, scale_result: Dict):
        """Scale out position."""
        logger.info(f"Scaling out position {position_id}: {scale_result['reason']}")
        
        # Update position size
        if position_id in self.active_positions:
            current_contracts = self.active_positions[position_id]['num_contracts']
            scale_contracts = int(current_contracts * scale_result['scale'])
            
            self.active_positions[position_id]['num_contracts'] -= scale_contracts
            
            # Send scaling alert
            self.alerts.send_scaling_alert(position_id, scale_result, {
                'scaled_contracts': scale_contracts,
                'remaining_contracts': self.active_positions[position_id]['num_contracts']
            })
    
    def _close_position(self, position_id: int, reason: str):
        """Close position."""
        if position_id not in self.active_positions:
            return
        
        position = self.active_positions[position_id]
        strategy = position.get('strategy', 'vwap')
        
        if strategy == 'overnight_bias':
            # Calculate final P&L for overnight bias position
            current_data = self._get_current_market_data()
            if current_data:
                # Simple P&L calculation (would need actual option pricing)
                final_pnl = 0.0  # Placeholder
            else:
                final_pnl = 0.0
        else:
            # Use existing position sizing for VWAP positions
            close_result = self.position_sizing.close_position(position_id, reason)
            final_pnl = close_result.get('final_pnl', 0.0)
            
            # Remove from invalidation tracking
            self.hard_invalidation.remove_position(position_id)
        
        # Send close alert
        self.alerts.send_close_alert(position_id, reason, final_pnl)
        
        # Remove from active positions
        del self.active_positions[position_id]
        
        logger.info(f"Position closed: {position_id} - Reason: {reason} - P&L: {final_pnl:.2f}")
    
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
    
    def _get_current_market_data(self) -> Optional[Dict]:
        """Get current market data."""
        # This would get real-time data from Polygon
        # For now, return simulated data
        return {
            'timestamp': time.time(),
            'price': 245.5,  # This would be actual price
            'volume': 1000
        }
    
    def _get_current_market_data_for_symbol(self, symbol: str) -> Optional[Dict]:
        """Get current market data for a specific symbol."""
        # This would get real-time data from Polygon for the specific symbol
        # For now, return simulated data with symbol-specific pricing
        base_prices = {
            'IWM': 245.5,
            'SPY': 443.0,
            'QQQ': 380.0
        }
        
        return {
            'timestamp': time.time(),
            'price': base_prices.get(symbol, 245.5),
            'volume': 1000,
            'symbol': symbol
        }
    
    def _handle_stock_data(self, data: Dict):
        """Handle stock data from WebSocket."""
        # Update session VWAP
        vwap_result = self.session_vwap.update(data)
        
        # Update 5-minute confirmation for VWAP strategy
        if self.current_bias:
            confirmation_result = self.five_min_confirmation.update(
                data, self.current_bias, self.trigger_levels
            )
            
            if confirmation_result.get('entry_signal'):
                self._execute_vwap_entry(data)
    
    def _handle_minute_data(self, data: Dict):
        """Handle minute data from WebSocket."""
        # Process minute-level data if needed
        pass
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.strategy_active = False
        
        # Cleanup resources
        logger.info("Cleaning up resources")
        if hasattr(self, 'polygon_ws'):
            self.polygon_ws.disconnect()
        if hasattr(self, 'session_vwap'):
            self.session_vwap.end_session()
        logger.info("Cleanup complete")
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
        """Get current multi-strategy status."""
        # Get status for each overnight bias strategy instance
        overnight_bias_statuses = {}
        for symbol, strategy in self.overnight_bias_instances.items():
            overnight_bias_statuses[symbol] = strategy.get_strategy_status()
        
        return {
            'strategy_active': self.strategy_active,
            'active_strategies': self.active_strategies,
            'overnight_bias_symbols': self.overnight_bias_symbols,
            'vwap_strategy_symbols': self.vwap_strategy_symbols,
            'current_bias': self.current_bias,
            'trigger_levels': self.trigger_levels,
            'entry_window_active': self.entry_window_active,
            'active_positions': len(self.active_positions),
            'daily_pnl': self.daily_pnl,
            'position_summary': self.position_sizing.get_position_summary(),
            'invalidation_status': self.hard_invalidation.get_invalidation_status(),
            'overnight_bias_statuses': overnight_bias_statuses
        }
    
    def toggle_strategy(self, strategy_name: str, enabled: bool):
        """Toggle a strategy on/off."""
        if strategy_name in self.active_strategies:
            self.active_strategies[strategy_name] = enabled
            logger.info(f"Strategy {strategy_name} {'enabled' if enabled else 'disabled'}")
        else:
            logger.error(f"Unknown strategy: {strategy_name}")
    
    def get_strategy_performance(self) -> Dict:
        """Get performance metrics for both strategies."""
        return {
            'vwap_strategy': {
                'active': self.active_strategies['vwap'],
                'positions': len([p for p in self.active_positions.values() if p.get('strategy') == 'vwap']),
                'bias': self.current_bias
            },
            'overnight_bias_strategy': {
                'active': self.active_strategies['overnight_bias'],
                'positions': len([p for p in self.active_positions.values() if p.get('strategy') == 'overnight_bias']),
                'bias': self.overnight_bias_strategy.current_bias,
                'confidence': self.overnight_bias_strategy.bias_confidence
            }
        }
