"""
5-Minute Confirmation System for IWM Strategy
Implements 5-minute candle confirmation with VWAP alignment.
Handles entry triggers and retest logic.
"""
import time
from typing import Dict, Optional, Tuple, List
from collections import deque
from datetime import datetime, timedelta
import pytz
from logger import setup_logger
from config import Config
from utils import get_et_time

logger = setup_logger("FiveMinuteConfirmation")


class FiveMinuteConfirmation:
    """
    5-minute confirmation system for entry triggers.
    Handles 5-minute candle confirmation with VWAP alignment.
    """
    
    def __init__(self):
        # 5-minute candle data
        self.five_min_candles: deque = deque(maxlen=100)  # Last 100 candles
        self.current_candle: Optional[Dict] = None
        
        # Entry window tracking
        self.entry_windows = {
            'primary': {'start': '09:45', 'end': '11:00'},
            'secondary': {'start': '13:30', 'end': '14:15'}
        }
        
        # Trigger level tracking
        self.trigger_high: Optional[float] = None
        self.trigger_low: Optional[float] = None
        
        # Confirmation state
        self.confirmation_pending: bool = False
        self.confirmation_bias: Optional[str] = None
        self.confirmation_trigger: Optional[float] = None
        
        # Retest tracking
        self.retest_count: int = 0
        self.max_retests: int = 2
        
        # Entry cooldown
        self.last_entry_time: Optional[datetime] = None
        self.entry_cooldown: int = 300  # 5 minutes between entries
        
    def update(self, tick_data: Dict, bias: str, trigger_levels: Tuple[float, float]) -> Dict:
        """
        Update 5-minute confirmation system.
        
        Args:
            tick_data: Current tick data
            bias: Current bias ('calls' or 'puts')
            trigger_levels: (trigger_high, trigger_low)
            
        Returns:
            Dict with confirmation status
        """
        current_time = get_et_time()
        
        # Update trigger levels
        self.trigger_high, self.trigger_low = trigger_levels
        
        # Check if in entry window
        if not self._is_in_entry_window(current_time):
            return {'status': 'outside_window', 'bias': bias}
        
        # Update current candle
        self._update_current_candle(tick_data)
        
        # Check for 5-minute close
        if self._is_five_minute_close(current_time):
            return self._process_five_minute_close(bias)
        
        # Check for retest opportunities
        if self.confirmation_pending:
            return self._check_retest_opportunity(tick_data, bias)
        
        return {'status': 'waiting', 'bias': bias}
    
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
    
    def _update_current_candle(self, tick_data: Dict):
        """Update current 5-minute candle data."""
        if self.current_candle is None:
            self.current_candle = {
                'timestamp': tick_data['timestamp'],
                'open': tick_data['price'],
                'high': tick_data['price'],
                'low': tick_data['price'],
                'close': tick_data['price'],
                'volume': tick_data.get('volume', 0)
            }
        else:
            # Update candle data
            self.current_candle['high'] = max(self.current_candle['high'], tick_data['price'])
            self.current_candle['low'] = min(self.current_candle['low'], tick_data['price'])
            self.current_candle['close'] = tick_data['price']
            self.current_candle['volume'] += tick_data.get('volume', 0)
    
    def _is_five_minute_close(self, current_time: datetime) -> bool:
        """Check if this is a 5-minute candle close."""
        # 5-minute candles close at :00, :05, :10, :15, etc.
        minute = current_time.minute
        return minute % 5 == 0 and current_time.second < 30
    
    def _process_five_minute_close(self, bias: str) -> Dict:
        """
        Process 5-minute candle close for confirmation.
        
        Args:
            bias: Current bias ('calls' or 'puts')
            
        Returns:
            Dict with confirmation result
        """
        if not self.current_candle:
            return {'status': 'no_candle', 'bias': bias}
        
        candle = self.current_candle.copy()
        candle['timestamp'] = time.time()
        
        # Store completed candle
        self.five_min_candles.append(candle)
        
        # Check for trigger break
        trigger_break = self._check_trigger_break(candle, bias)
        
        if trigger_break['broken']:
            # Set confirmation pending
            self.confirmation_pending = True
            self.confirmation_bias = bias
            self.confirmation_trigger = trigger_break['trigger_level']
            
            logger.info(f"5-Minute Trigger Break: {bias} at {candle['close']:.2f}")
            
            return {
                'status': 'trigger_break',
                'bias': bias,
                'trigger_level': trigger_break['trigger_level'],
                'candle_close': candle['close'],
                'confirmation_pending': True
            }
        
        # Check for confirmation if pending
        if self.confirmation_pending and self.confirmation_bias == bias:
            confirmation = self._check_confirmation(candle, bias)
            
            if confirmation['confirmed']:
                # Reset confirmation state
                self.confirmation_pending = False
                self.confirmation_bias = None
                self.confirmation_trigger = None
                self.retest_count = 0
                
                logger.info(f"5-Minute Confirmation: {bias} confirmed at {candle['close']:.2f}")
                
                return {
                    'status': 'confirmed',
                    'bias': bias,
                    'candle_close': candle['close'],
                    'entry_signal': True
                }
        
        # Reset current candle
        self.current_candle = None
        
        return {'status': 'no_trigger', 'bias': bias}
    
    def _check_trigger_break(self, candle: Dict, bias: str) -> Dict:
        """
        Check if candle breaks trigger level.
        
        Args:
            candle: 5-minute candle data
            bias: Current bias
            
        Returns:
            Dict with break status
        """
        if bias == 'calls' and self.trigger_high is not None:
            if candle['close'] > self.trigger_high:
                return {'broken': True, 'trigger_level': self.trigger_high}
        
        elif bias == 'puts' and self.trigger_low is not None:
            if candle['close'] < self.trigger_low:
                return {'broken': True, 'trigger_level': self.trigger_low}
        
        return {'broken': False, 'trigger_level': None}
    
    def _check_confirmation(self, candle: Dict, bias: str) -> Dict:
        """
        Check if candle confirms the trigger break.
        
        Args:
            candle: 5-minute candle data
            bias: Current bias
            
        Returns:
            Dict with confirmation status
        """
        if bias == 'calls':
            # For calls, need close above trigger and VWAP
            if (candle['close'] > self.confirmation_trigger and 
                candle['close'] > self.current_candle.get('vwap', 0)):
                return {'confirmed': True}
        
        elif bias == 'puts':
            # For puts, need close below trigger and VWAP
            if (candle['close'] < self.confirmation_trigger and 
                candle['close'] < self.current_candle.get('vwap', 0)):
                return {'confirmed': True}
        
        return {'confirmed': False}
    
    def _check_retest_opportunity(self, tick_data: Dict, bias: str) -> Dict:
        """
        Check for retest opportunities.
        
        Args:
            tick_data: Current tick data
            bias: Current bias
            
        Returns:
            Dict with retest status
        """
        if self.retest_count >= self.max_retests:
            # Max retests reached, cancel confirmation
            self.confirmation_pending = False
            self.confirmation_bias = None
            self.confirmation_trigger = None
            self.retest_count = 0
            
            return {'status': 'max_retests', 'bias': bias}
        
        current_price = tick_data['price']
        
        # Check for retest
        if bias == 'calls' and self.confirmation_trigger is not None:
            if (current_price <= self.confirmation_trigger * 1.001 and  # Within 0.1%
                current_price >= self.confirmation_trigger * 0.999):
                self.retest_count += 1
                
                logger.info(f"Retest opportunity: {bias} at {current_price:.2f}")
                
                return {
                    'status': 'retest_opportunity',
                    'bias': bias,
                    'retest_count': self.retest_count,
                    'price': current_price
                }
        
        elif bias == 'puts' and self.confirmation_trigger is not None:
            if (current_price >= self.confirmation_trigger * 0.999 and  # Within 0.1%
                current_price <= self.confirmation_trigger * 1.001):
                self.retest_count += 1
                
                logger.info(f"Retest opportunity: {bias} at {current_price:.2f}")
                
                return {
                    'status': 'retest_opportunity',
                    'bias': bias,
                    'retest_count': self.retest_count,
                    'price': current_price
                }
        
        return {'status': 'waiting_retest', 'bias': bias}
    
    def can_enter_trade(self, bias: str) -> bool:
        """
        Check if we can enter a trade for the given bias.
        
        Args:
            bias: Current bias
            
        Returns:
            True if can enter, False otherwise
        """
        if self.confirmation_pending and self.confirmation_bias == bias:
            return True
        
        return False
    
    def get_entry_signal(self, bias: str) -> Optional[Dict]:
        """
        Get entry signal for the given bias.
        
        Args:
            bias: Current bias
            
        Returns:
            Entry signal dict or None
        """
        if not self.can_enter_trade(bias):
            return None
        
        return {
            'bias': bias,
            'trigger_level': self.confirmation_trigger,
            'retest_count': self.retest_count,
            'timestamp': time.time()
        }
    
    def reset_confirmation(self):
        """Reset confirmation state."""
        self.confirmation_pending = False
        self.confirmation_bias = None
        self.confirmation_trigger = None
        self.retest_count = 0
        
        logger.info("5-Minute confirmation reset")
