"""
Hard Invalidation System for IWM Strategy
Implements hard invalidation rules based on trigger levels and VWAP.
"""
import time
from typing import Dict, Optional, List, Tuple
from collections import deque
from datetime import datetime
from logger import setup_logger
from config import Config
from utils import get_et_time

logger = setup_logger("HardInvalidation")


class HardInvalidation:
    """
    Hard invalidation system for position management.
    Implements trigger level and VWAP-based invalidation rules.
    """
    
    def __init__(self):
        # Invalidation tracking
        self.invalidation_triggers: List[Dict] = []
        self.consecutive_closes_inside: int = 0
        self.consecutive_closes_across_vwap: int = 0
        
        # 5-minute close tracking
        self.five_min_closes: deque = deque(maxlen=10)  # Last 10 closes
        self.last_close_time: Optional[datetime] = None
        
        # VWAP tracking
        self.current_vwap: float = 0.0
        self.vwap_side: Optional[str] = None  # 'above' or 'below'
        
        # Position tracking
        self.active_positions: List[Dict] = []
        
        # Invalidation rules
        self.max_consecutive_closes = 2  # Two consecutive closes back inside
        self.vwap_invalidation_closes = 1  # One close across VWAP
        
    def update(self, position_data: Dict, current_price: float, 
               trigger_levels: Tuple[float, float], vwap_data: Dict) -> Dict:
        """
        Update invalidation system with new data.
        
        Args:
            position_data: Current position data
            current_price: Current stock price
            trigger_levels: (trigger_high, trigger_low)
            vwap_data: VWAP analysis data
            
        Returns:
            Dict with invalidation status
        """
        # Update VWAP data
        self.current_vwap = vwap_data.get('current_vwap', 0.0)
        self.vwap_side = vwap_data.get('price_vs_vwap', None)
        
        # Check for 5-minute close
        if self._is_five_minute_close():
            return self._process_five_minute_close(position_data, current_price, trigger_levels)
        
        # Check for real-time invalidation
        return self._check_real_time_invalidation(position_data, current_price, trigger_levels)
    
    def _is_five_minute_close(self) -> bool:
        """Check if this is a 5-minute candle close."""
        current_time = get_et_time()
        
        # 5-minute candles close at :00, :05, :10, :15, etc.
        minute = current_time.minute
        is_close = minute % 5 == 0 and current_time.second < 30
        
        if is_close and (self.last_close_time is None or 
                        (current_time - self.last_close_time).total_seconds() >= 300):
            self.last_close_time = current_time
            return True
        
        return False
    
    def _process_five_minute_close(self, position_data: Dict, current_price: float, 
                                 trigger_levels: Tuple[float, float]) -> Dict:
        """
        Process 5-minute candle close for invalidation check.
        
        Args:
            position_data: Current position data
            current_price: Current stock price
            trigger_levels: (trigger_high, trigger_low)
            
        Returns:
            Dict with invalidation status
        """
        trigger_high, trigger_low = trigger_levels
        bias = position_data.get('bias', '')
        
        # Store 5-minute close
        close_data = {
            'timestamp': time.time(),
            'price': current_price,
            'bias': bias,
            'trigger_high': trigger_high,
            'trigger_low': trigger_low,
            'vwap': self.current_vwap
        }
        self.five_min_closes.append(close_data)
        
        # Check for invalidation
        invalidation_result = self._check_trigger_invalidation(bias, current_price, 
                                                              trigger_high, trigger_low)
        
        if invalidation_result['invalidated']:
            return {
                'status': 'hard_invalidation',
                'reason': invalidation_result['reason'],
                'consecutive_closes': self.consecutive_closes_inside,
                'action': 'close_position'
            }
        
        # Check for VWAP invalidation
        vwap_result = self._check_vwap_invalidation(bias, current_price)
        
        if vwap_result['invalidated']:
            return {
                'status': 'vwap_invalidation',
                'reason': vwap_result['reason'],
                'consecutive_closes': self.consecutive_closes_across_vwap,
                'action': 'close_position'
            }
        
        return {'status': 'valid', 'consecutive_closes': self.consecutive_closes_inside}
    
    def _check_trigger_invalidation(self, bias: str, current_price: float, 
                                   trigger_high: float, trigger_low: float) -> Dict:
        """
        Check for trigger level invalidation.
        
        Args:
            bias: Position bias ('calls' or 'puts')
            current_price: Current stock price
            trigger_high: Trigger high level
            trigger_low: Trigger low level
            
        Returns:
            Dict with invalidation status
        """
        if bias == 'calls':
            # For calls, check if price closes back inside trigger
            if current_price <= trigger_high:
                self.consecutive_closes_inside += 1
                self.consecutive_closes_across_vwap = 0  # Reset VWAP counter
                
                if self.consecutive_closes_inside >= self.max_consecutive_closes:
                    return {
                        'invalidated': True,
                        'reason': f'Two consecutive closes back inside trigger (${trigger_high:.2f})',
                        'consecutive_closes': self.consecutive_closes_inside
                    }
            else:
                # Price still above trigger, reset counter
                self.consecutive_closes_inside = 0
        
        elif bias == 'puts':
            # For puts, check if price closes back inside trigger
            if current_price >= trigger_low:
                self.consecutive_closes_inside += 1
                self.consecutive_closes_across_vwap = 0  # Reset VWAP counter
                
                if self.consecutive_closes_inside >= self.max_consecutive_closes:
                    return {
                        'invalidated': True,
                        'reason': f'Two consecutive closes back inside trigger (${trigger_low:.2f})',
                        'consecutive_closes': self.consecutive_closes_inside
                    }
            else:
                # Price still below trigger, reset counter
                self.consecutive_closes_inside = 0
        
        return {'invalidated': False, 'consecutive_closes': self.consecutive_closes_inside}
    
    def _check_vwap_invalidation(self, bias: str, current_price: float) -> Dict:
        """
        Check for VWAP invalidation.
        
        Args:
            bias: Position bias ('calls' or 'puts')
            current_price: Current stock price
            
        Returns:
            Dict with invalidation status
        """
        if self.current_vwap == 0:
            return {'invalidated': False}
        
        if bias == 'calls':
            # For calls, check if price closes below VWAP
            if current_price < self.current_vwap:
                self.consecutive_closes_across_vwap += 1
                self.consecutive_closes_inside = 0  # Reset trigger counter
                
                if self.consecutive_closes_across_vwap >= self.vwap_invalidation_closes:
                    return {
                        'invalidated': True,
                        'reason': f'Close below VWAP (${self.current_vwap:.2f})',
                        'consecutive_closes': self.consecutive_closes_across_vwap
                    }
            else:
                # Price still above VWAP, reset counter
                self.consecutive_closes_across_vwap = 0
        
        elif bias == 'puts':
            # For puts, check if price closes above VWAP
            if current_price > self.current_vwap:
                self.consecutive_closes_across_vwap += 1
                self.consecutive_closes_inside = 0  # Reset trigger counter
                
                if self.consecutive_closes_across_vwap >= self.vwap_invalidation_closes:
                    return {
                        'invalidated': True,
                        'reason': f'Close above VWAP (${self.current_vwap:.2f})',
                        'consecutive_closes': self.consecutive_closes_across_vwap
                    }
            else:
                # Price still below VWAP, reset counter
                self.consecutive_closes_across_vwap = 0
        
        return {'invalidated': False, 'consecutive_closes': self.consecutive_closes_across_vwap}
    
    def _check_real_time_invalidation(self, position_data: Dict, current_price: float, 
                                     trigger_levels: Tuple[float, float]) -> Dict:
        """
        Check for real-time invalidation (not just 5-minute closes).
        
        Args:
            position_data: Current position data
            current_price: Current stock price
            trigger_levels: (trigger_high, trigger_low)
            
        Returns:
            Dict with invalidation status
        """
        # Real-time invalidation is less strict than 5-minute closes
        # Only check for extreme moves or VWAP violations
        
        bias = position_data.get('bias', '')
        trigger_high, trigger_low = trigger_levels
        
        # Check for extreme moves beyond trigger levels
        if bias == 'calls' and current_price < trigger_low:
            return {
                'status': 'extreme_move',
                'reason': f'Price moved below trigger low (${trigger_low:.2f})',
                'action': 'close_position'
            }
        
        elif bias == 'puts' and current_price > trigger_high:
            return {
                'status': 'extreme_move',
                'reason': f'Price moved above trigger high (${trigger_high:.2f})',
                'action': 'close_position'
            }
        
        return {'status': 'valid'}
    
    def add_position(self, position_data: Dict):
        """Add position to invalidation tracking."""
        position = {
            'id': position_data.get('id', 0),
            'bias': position_data.get('bias', ''),
            'entry_time': time.time(),
            'trigger_levels': position_data.get('trigger_levels', (0, 0)),
            'status': 'active'
        }
        
        self.active_positions.append(position)
        
        # Reset counters for new position
        self.consecutive_closes_inside = 0
        self.consecutive_closes_across_vwap = 0
        
        logger.info(f"Position added to invalidation tracking: {position['bias']}")
    
    def remove_position(self, position_id: int):
        """Remove position from invalidation tracking."""
        self.active_positions = [p for p in self.active_positions if p['id'] != position_id]
        logger.info(f"Position removed from invalidation tracking: {position_id}")
    
    def get_invalidation_status(self) -> Dict:
        """Get current invalidation status."""
        return {
            'consecutive_closes_inside': self.consecutive_closes_inside,
            'consecutive_closes_across_vwap': self.consecutive_closes_across_vwap,
            'current_vwap': self.current_vwap,
            'vwap_side': self.vwap_side,
            'active_positions': len(self.active_positions),
            'max_consecutive_closes': self.max_consecutive_closes
        }
    
    def reset_counters(self):
        """Reset invalidation counters."""
        self.consecutive_closes_inside = 0
        self.consecutive_closes_across_vwap = 0
        self.five_min_closes.clear()
        
        logger.info("Invalidation counters reset")
