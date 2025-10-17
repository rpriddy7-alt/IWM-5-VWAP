"""
Overnight Bias / 0DTE Execution Strategy for Miyagi
Implements the complete overnight bias strategy with 12h candle analysis,
5-minute confirmation, and VWAP/EMA20 filters.
"""
import time
import numpy as np
from typing import Dict, Optional, Tuple, List
from collections import deque
from datetime import datetime, timedelta
from logger import setup_logger
from config import Config
from utils import get_et_time

logger = setup_logger("OvernightBiasStrategy")


class OvernightBiasStrategy:
    """
    Overnight Bias / 0DTE Execution Strategy for Miyagi.
    
    Core Concept:
    - Use 12-hour overnight candle (3 AM ET close) to set day's directional bias
    - Trade 0DTE options intraday based on 5-minute confirmation
    - Use VWAP + EMA20 as structural filters
    """
    
    def __init__(self):
        # 12-hour overnight bar data (15:00-03:00 ET)
        self.overnight_bars: deque = deque(maxlen=10)
        self.current_overnight_bar: Optional[Dict] = None
        
        # 5-minute candle data for confirmation
        self.five_min_candles: deque = deque(maxlen=100)
        self.current_five_min_candle: Optional[Dict] = None
        
        # EMA20 calculation
        self.ema20_data: deque = deque(maxlen=20)
        self.current_ema20: float = 0.0
        
        # Strategy state
        self.current_bias: Optional[str] = None  # 'calls', 'puts', or None
        self.bias_confidence: float = 0.0
        self.overnight_high: Optional[float] = None
        self.overnight_low: Optional[float] = None
        
        # Entry window tracking
        self.entry_windows = {
            'primary': {'start': '09:45', 'end': '11:00'},
            'secondary': {'start': '13:30', 'end': '14:15'}
        }
        
        # Position tracking
        self.active_positions: Dict = {}
        self.daily_pnl: float = 0.0
        self.max_daily_loss: float = -700.0  # $700 max daily loss
        
        # Risk management
        self.position_sizes = {
            'initial': 0.33,  # 1/3 of capital
            'add': 0.33,      # 1/3 for retest
            'reserve': 0.34   # 1/3 reserve
        }
        
        # Time filters
        self.last_analysis_time: Optional[datetime] = None
        self.overnight_processed_today: bool = False
        
        # Symbol tier configuration (will be set by orchestrator)
        self.symbol_tier: str = 'tier1'
        self.tier_controls: Dict = {
            'max_positions': 2,
            'position_size_multiplier': 1.0,
            'time_stop_minutes': 45
        }
        
    def update_overnight_bar(self, bar_data: Dict) -> Dict:
        """
        Process 12-hour overnight bar for bias determination.
        
        Args:
            bar_data: {
                'timestamp': float,
                'open': float,
                'high': float,
                'low': float,
                'close': float,
                'volume': int
            }
            
        Returns:
            Dict with bias analysis
        """
        current_time = get_et_time()
        
        # Check if this is 3:00 AM ET (overnight bar close)
        if not self._is_overnight_bar_complete(current_time):
            return {'status': 'pending', 'bias': self.current_bias}
        
        # Store overnight bar
        overnight_bar = {
            'timestamp': bar_data['timestamp'],
            'open': bar_data['open'],
            'high': bar_data['high'],
            'low': bar_data['low'],
            'close': bar_data['close'],
            'volume': bar_data['volume'],
            'analysis_time': current_time
        }
        
        self.overnight_bars.append(overnight_bar)
        self.overnight_high = bar_data['high']
        self.overnight_low = bar_data['low']
        
        # Determine bias based on overnight bar
        bias_result = self._determine_overnight_bias(bar_data)
        
        if bias_result['bias']:
            self.current_bias = bias_result['bias']
            self.bias_confidence = bias_result['confidence']
            self.overnight_processed_today = True
            
            logger.info(f"Overnight Bias Set: {self.current_bias.upper()}")
            logger.info(f"  Confidence: {self.bias_confidence:.2f}")
            logger.info(f"  Overnight High: {self.overnight_high:.2f}")
            logger.info(f"  Overnight Low: {self.overnight_low:.2f}")
        
        return {
            'status': 'complete',
            'bias': self.current_bias,
            'confidence': self.bias_confidence,
            'overnight_high': self.overnight_high,
            'overnight_low': self.overnight_low,
            'bar_type': bias_result['bar_type']
        }
    
    def update_five_minute_data(self, tick_data: Dict, vwap_data: Dict) -> Dict:
        """
        Update 5-minute confirmation system with tick data and VWAP.
        
        Args:
            tick_data: Current tick data
            vwap_data: VWAP analysis data
            
        Returns:
            Dict with confirmation status
        """
        current_time = get_et_time()
        
        # Update 5-minute candle
        self._update_five_minute_candle(tick_data)
        
        # Update EMA20
        self._update_ema20(tick_data['price'])
        
        # Check if we're in entry window
        if not self._is_in_entry_window(current_time):
            return {'status': 'outside_window', 'bias': self.current_bias}
        
        # Check for 5-minute close
        if self._is_five_minute_close(current_time):
            return self._process_five_minute_close(vwap_data)
        
        return {'status': 'waiting', 'bias': self.current_bias}
    
    def _is_overnight_bar_complete(self, current_time: datetime) -> bool:
        """Check if overnight bar is complete (3:00 AM ET)."""
        return (current_time.hour == 3 and 
                current_time.minute == 0 and 
                current_time.second < 30)
    
    def _determine_overnight_bias(self, bar_data: Dict) -> Dict:
        """
        Determine bias based on overnight bar analysis.
        
        Rules:
        - 2-up: Closed above previous inside-bar high → Bullish (Calls)
        - 2-down: Closed below previous inside-bar low → Bearish (Puts)  
        - 1: Still inside bar → Neutral (Wait for breakout)
        """
        if len(self.overnight_bars) < 2:
            return {'bias': None, 'confidence': 0.0, 'bar_type': 'first'}
        
        current_bar = bar_data
        previous_bar = self.overnight_bars[-2]
        
        current_high = current_bar['high']
        current_low = current_bar['low']
        current_close = current_bar['close']
        
        prev_high = previous_bar['high']
        prev_low = previous_bar['low']
        
        # Check if inside bar (1)
        if current_high <= prev_high and current_low >= prev_low:
            return {'bias': None, 'confidence': 0.0, 'bar_type': '1'}
        
        # Check 2-up break (bullish)
        if current_close > prev_high:
            confidence = min(0.7 + (abs(current_close - prev_high) / prev_high) * 10, 1.0)
            return {'bias': 'calls', 'confidence': confidence, 'bar_type': '2-up'}
        
        # Check 2-down break (bearish)
        if current_close < prev_low:
            confidence = min(0.7 + (abs(prev_low - current_close) / prev_low) * 10, 1.0)
            return {'bias': 'puts', 'confidence': confidence, 'bar_type': '2-down'}
        
        # Default to inside bar
        return {'bias': None, 'confidence': 0.0, 'bar_type': '1'}
    
    def _update_five_minute_candle(self, tick_data: Dict):
        """Update current 5-minute candle."""
        current_time = get_et_time()
        
        # Check if new 5-minute candle
        if (self.current_five_min_candle is None or 
            self._is_new_five_minute_candle(current_time)):
            
            # Store previous candle if exists
            if self.current_five_min_candle:
                self.five_min_candles.append(self.current_five_min_candle.copy())
            
            # Start new candle
            self.current_five_min_candle = {
                'timestamp': tick_data['timestamp'],
                'open': tick_data['price'],
                'high': tick_data['price'],
                'low': tick_data['price'],
                'close': tick_data['price'],
                'volume': tick_data.get('volume', 0)
            }
        else:
            # Update current candle
            self.current_five_min_candle['high'] = max(
                self.current_five_min_candle['high'], tick_data['price']
            )
            self.current_five_min_candle['low'] = min(
                self.current_five_min_candle['low'], tick_data['price']
            )
            self.current_five_min_candle['close'] = tick_data['price']
            self.current_five_min_candle['volume'] += tick_data.get('volume', 0)
    
    def _is_new_five_minute_candle(self, current_time: datetime) -> bool:
        """Check if this is a new 5-minute candle."""
        if not self.current_five_min_candle:
            return True
        
        # 5-minute candles start at :00, :05, :10, :15, etc.
        current_minute = current_time.minute
        candle_start_minute = current_minute - (current_minute % 5)
        
        last_candle_time = datetime.fromtimestamp(
            self.current_five_min_candle['timestamp']
        )
        last_candle_minute = last_candle_time.minute
        last_candle_start_minute = last_candle_minute - (last_candle_minute % 5)
        
        return candle_start_minute != last_candle_start_minute
    
    def _update_ema20(self, price: float):
        """Update EMA20 calculation."""
        self.ema20_data.append(price)
        
        if len(self.ema20_data) == 1:
            self.current_ema20 = price
        else:
            # Calculate EMA20
            alpha = 2.0 / (20 + 1)
            self.current_ema20 = alpha * price + (1 - alpha) * self.current_ema20
    
    def _is_in_entry_window(self, current_time: datetime) -> bool:
        """Check if current time is in entry window."""
        current_time_str = current_time.strftime('%H:%M')
        
        # Primary window: 09:45-11:00
        if '09:45' <= current_time_str <= '11:00':
            return True
        
        # Secondary window: 13:30-14:15
        if '13:30' <= current_time_str <= '14:15':
            return True
        
        return False
    
    def _is_five_minute_close(self, current_time: datetime) -> bool:
        """Check if this is a 5-minute candle close."""
        minute = current_time.minute
        return minute % 5 == 0 and current_time.second < 30
    
    def _process_five_minute_close(self, vwap_data: Dict) -> Dict:
        """
        Process 5-minute candle close for entry confirmation.
        
        Entry Logic:
        1. Day's bias is defined
        2. Price is on your side of VWAP and EMA20
        3. 5-minute candle closes beyond overnight high/low in bias direction
        """
        if not self.current_five_min_candle or not self.current_bias:
            return {'status': 'no_signal', 'bias': self.current_bias}
        
        candle = self.current_five_min_candle.copy()
        current_price = candle['close']
        current_vwap = vwap_data.get('current_vwap', 0)
        
        # Check VWAP and EMA20 alignment
        vwap_aligned = self._check_vwap_alignment(current_price, current_vwap)
        ema20_aligned = self._check_ema20_alignment(current_price)
        
        if not (vwap_aligned and ema20_aligned):
            return {'status': 'not_aligned', 'bias': self.current_bias}
        
        # Check overnight level break
        level_break = self._check_overnight_level_break(candle)
        
        if level_break['broken']:
            logger.info(f"Overnight Level Break: {self.current_bias} at {current_price:.2f}")
            
            return {
                'status': 'entry_signal',
                'bias': self.current_bias,
                'entry_price': current_price,
                'trigger_level': level_break['trigger_level'],
                'vwap': current_vwap,
                'ema20': self.current_ema20,
                'confidence': self.bias_confidence
            }
        
        return {'status': 'no_break', 'bias': self.current_bias}
    
    def _check_vwap_alignment(self, price: float, vwap: float) -> bool:
        """Check if price is aligned with VWAP for current bias."""
        if vwap == 0:
            return False
        
        if self.current_bias == 'calls':
            return price > vwap
        elif self.current_bias == 'puts':
            return price < vwap
        
        return False
    
    def _check_ema20_alignment(self, price: float) -> bool:
        """Check if price is aligned with EMA20 for current bias."""
        if self.current_ema20 == 0:
            return False
        
        if self.current_bias == 'calls':
            return price > self.current_ema20
        elif self.current_bias == 'puts':
            return price < self.current_ema20
        
        return False
    
    def _check_overnight_level_break(self, candle: Dict) -> Dict:
        """Check if candle breaks overnight levels in bias direction."""
        close_price = candle['close']
        
        if self.current_bias == 'calls' and self.overnight_high:
            if close_price > self.overnight_high:
                return {'broken': True, 'trigger_level': self.overnight_high}
        
        elif self.current_bias == 'puts' and self.overnight_low:
            if close_price < self.overnight_low:
                return {'broken': True, 'trigger_level': self.overnight_low}
        
        return {'broken': False, 'trigger_level': None}
    
    def calculate_position_size(self, option_price: float, account_balance: float) -> Dict:
        """
        Calculate position size based on strategy rules.
        
        Position Sizing:
        - 1st entry: 1/3 capital
        - Add 1/3 on clean retest + VWAP hold
        - Keep 1/3 reserve
        - Per-trade risk: 1.5-3% of account
        """
        if self.daily_pnl <= self.max_daily_loss:
            return {'status': 'rejected', 'reason': 'Daily loss limit reached'}
        
        # Calculate available capital (excluding daily losses)
        available_capital = account_balance + self.daily_pnl
        
        # Initial position size (1/3 of available capital)
        position_value = available_capital * self.position_sizes['initial']
        
        # Calculate number of contracts
        num_contracts = int(position_value / option_price)
        
        if num_contracts < 1:
            return {'status': 'rejected', 'reason': 'Insufficient capital for position'}
        
        # Calculate risk per trade (1.5-3% of account)
        risk_per_trade = min(account_balance * 0.03, account_balance * 0.015)
        max_contracts_by_risk = int(risk_per_trade / option_price)
        
        # Use the smaller of the two
        final_contracts = min(num_contracts, max_contracts_by_risk)
        
        return {
            'status': 'approved',
            'num_contracts': final_contracts,
            'position_value': final_contracts * option_price,
            'risk_amount': final_contracts * option_price,
            'available_capital': available_capital
        }
    
    def check_exit_conditions(self, position_data: Dict, current_price: float, 
                            vwap_data: Dict) -> Dict:
        """
        Check exit conditions for active positions.
        
        Exit Rules:
        - Hard exit: Two consecutive 5-minute closes back inside trigger range or across VWAP
        - Profit scales: +30-50% → partial, +70-100% → second scale
        - Time stop: No new high/low within 45 minutes
        """
        position_id = position_data['position_id']
        entry_price = position_data['entry_price']
        entry_time = position_data['entry_time']
        bias = position_data['bias']
        
        current_time = get_et_time()
        time_in_position = (current_time - entry_time).total_seconds() / 60  # minutes
        
        # Time stop (tier-specific)
        time_stop_minutes = self.tier_controls.get('time_stop_minutes', 45)
        if time_in_position > time_stop_minutes:
            return {
                'action': 'close',
                'reason': f'time_stop_{time_stop_minutes}min',
                'position_id': position_id
            }
        
        # Calculate current P&L
        if bias == 'calls':
            pnl_pct = (current_price - entry_price) / entry_price * 100
        else:
            pnl_pct = (entry_price - current_price) / entry_price * 100
        
        # Profit scaling
        if pnl_pct >= 70:  # 70-100% profit
            return {
                'action': 'scale_out',
                'scale': 0.5,  # Scale out 50%
                'reason': 'profit_scale_70',
                'position_id': position_id
            }
        elif pnl_pct >= 30:  # 30-50% profit
            return {
                'action': 'scale_out',
                'scale': 0.25,  # Scale out 25%
                'reason': 'profit_scale_30',
                'position_id': position_id
            }
        
        # Hard exit conditions
        hard_exit = self._check_hard_exit_conditions(
            position_data, current_price, vwap_data
        )
        
        if hard_exit['should_exit']:
            return {
                'action': 'close',
                'reason': hard_exit['reason'],
                'position_id': position_id
            }
        
        return {'action': 'hold', 'position_id': position_id}
    
    def _check_hard_exit_conditions(self, position_data: Dict, current_price: float,
                                   vwap_data: Dict) -> Dict:
        """Check hard exit conditions."""
        bias = position_data['bias']
        trigger_level = position_data.get('trigger_level')
        current_vwap = vwap_data.get('current_vwap', 0)
        
        # Check if price is back inside trigger range
        if bias == 'calls' and trigger_level:
            if current_price < trigger_level:
                return {'should_exit': True, 'reason': 'back_inside_trigger_range'}
        
        elif bias == 'puts' and trigger_level:
            if current_price > trigger_level:
                return {'should_exit': True, 'reason': 'back_inside_trigger_range'}
        
        # Check VWAP cross
        if current_vwap > 0:
            if bias == 'calls' and current_price < current_vwap:
                return {'should_exit': True, 'reason': 'vwap_cross'}
            elif bias == 'puts' and current_price > current_vwap:
                return {'should_exit': True, 'reason': 'vwap_cross'}
        
        return {'should_exit': False, 'reason': None}
    
    def get_strategy_status(self) -> Dict:
        """Get current strategy status."""
        return {
            'strategy_name': 'Overnight Bias / 0DTE Execution',
            'current_bias': self.current_bias,
            'bias_confidence': self.bias_confidence,
            'overnight_high': self.overnight_high,
            'overnight_low': self.overnight_low,
            'current_ema20': self.current_ema20,
            'active_positions': len(self.active_positions),
            'daily_pnl': self.daily_pnl,
            'overnight_processed': self.overnight_processed_today
        }
    
    def reset_daily(self):
        """Reset strategy for new trading day."""
        self.current_bias = None
        self.bias_confidence = 0.0
        self.overnight_high = None
        self.overnight_low = None
        self.overnight_processed_today = False
        self.daily_pnl = 0.0
        
        logger.info("Overnight Bias Strategy reset for new day")
    
    def set_tier_controls(self, symbol_tier: str, tier_controls: Dict):
        """Set tier-specific controls for this strategy instance."""
        self.symbol_tier = symbol_tier
        self.tier_controls = tier_controls
        logger.info(f"Set tier controls for {symbol_tier}: {tier_controls}")
