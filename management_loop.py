"""
IWM-5-VWAP Management Loop
Live position management with scaling and exits.
"""
import time
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from logger import setup_logger
from config import Config
from utils import get_et_time

logger = setup_logger("ManagementLoop")


class PositionManager:
    """
    Manages live positions with scaling and exit logic.
    Implements Strat-0DTE management rules.
    """
    
    def __init__(self):
        self.current_position = None
        self.entry_time = None
        self.entry_price = None
        self.peak_price = None
        self.scale1_hit = False
        self.scale2_hit = False
        self.vwap_exit_blocks = 0
        self.max_vwap_blocks = 2
        
    def open_position(self, option_data: Dict, signal: Dict):
        """Open new position."""
        self.current_position = {
            'contract': option_data['contract'],
            'strike': option_data['strike'],
            'delta': option_data['delta'],
            'entry_price': option_data['ask'],
            'bias': signal['bias'],
            'trigger': signal['trigger'],
            'vwap': signal['vwap']
        }
        
        self.entry_time = time.time()
        self.entry_price = option_data['ask']
        self.peak_price = option_data['ask']
        self.scale1_hit = False
        self.scale2_hit = False
        self.vwap_exit_blocks = 0
        
        logger.info(f"📈 POSITION OPENED: {option_data['contract']} @ ${option_data['ask']:.2f}")
    
    def update_position(self, current_price: float, current_vwap: float) -> Optional[Dict]:
        """
        Update position and check for exits/scaling.
        Returns exit signal if position should be closed.
        """
        if not self.current_position:
            return None
        
        # Update peak price
        if current_price > self.peak_price:
            self.peak_price = current_price
        
        # Calculate P&L
        pnl_pct = ((current_price - self.entry_price) / self.entry_price) * 100
        
        # Check scaling levels
        if not self.scale1_hit and pnl_pct >= 30:
            self.scale1_hit = True
            logger.info(f"📊 SCALE 1: +{pnl_pct:.1f}% profit")
            return {'action': 'SCALE1', 'pnl_pct': pnl_pct}
        
        if not self.scale2_hit and pnl_pct >= 70:
            self.scale2_hit = True
            logger.info(f"📊 SCALE 2: +{pnl_pct:.1f}% profit")
            return {'action': 'SCALE2', 'pnl_pct': pnl_pct}
        
        # Check exit conditions
        exit_signal = self._check_exit_conditions(current_price, current_vwap)
        
        if exit_signal:
            logger.warning(f"📤 EXIT SIGNAL: {exit_signal['reason']}")
            return exit_signal
        
        return None
    
    def _check_exit_conditions(self, current_price: float, current_vwap: float) -> Optional[Dict]:
        """Check all exit conditions."""
        if not self.current_position:
            return None
        
        bias = self.current_position['bias']
        trigger = self.current_position['trigger']
        
        # Check VWAP exit blocks
        if self._check_vwap_exit_blocks(current_price, current_vwap, bias):
            return {
                'action': 'EXIT',
                'reason': 'VWAP exit blocks exceeded',
                'vwap_blocks': self.vwap_exit_blocks
            }
        
        # Check trigger re-entry
        if self._check_trigger_re_entry(current_price, trigger, bias):
            return {
                'action': 'EXIT',
                'reason': 'Back inside trigger levels',
                'trigger': trigger
            }
        
        # Check time exit (45 minutes)
        if self._check_time_exit():
            return {
                'action': 'EXIT',
                'reason': 'Time exit (45 minutes)',
                'duration_minutes': (time.time() - self.entry_time) / 60
            }
        
        # Check end of day (14:30 ET)
        if self._check_end_of_day():
            return {
                'action': 'EXIT',
                'reason': 'End of day (14:30 ET)'
            }
        
        return None
    
    def _check_vwap_exit_blocks(self, current_price: float, current_vwap: float, bias: str) -> bool:
        """Check VWAP exit blocks."""
        # Determine if price is on wrong side of VWAP
        if bias == 'Long' and current_price < current_vwap:
            self.vwap_exit_blocks += 1
        elif bias == 'Short' and current_price > current_vwap:
            self.vwap_exit_blocks += 1
        else:
            self.vwap_exit_blocks = 0  # Reset if on correct side
        
        return self.vwap_exit_blocks >= self.max_vwap_blocks
    
    def _check_trigger_re_entry(self, current_price: float, trigger: float, bias: str) -> bool:
        """Check if price has re-entered trigger levels."""
        if bias == 'Long':
            return current_price < trigger
        elif bias == 'Short':
            return current_price > trigger
        
        return False
    
    def _check_time_exit(self) -> bool:
        """Check if 45 minutes have passed."""
        if not self.entry_time:
            return False
        
        duration_minutes = (time.time() - self.entry_time) / 60
        return duration_minutes >= 45
    
    def _check_end_of_day(self) -> bool:
        """Check if it's after 14:30 ET."""
        current_time = get_et_time()
        return current_time.hour >= 14 and current_time.minute >= 30
    
    def close_position(self, exit_reason: str) -> Dict:
        """Close current position."""
        if not self.current_position:
            return None
        
        position_data = self.current_position.copy()
        position_data['exit_reason'] = exit_reason
        position_data['exit_time'] = time.time()
        
        # Calculate final P&L
        if self.entry_price:
            final_pnl = ((self.peak_price - self.entry_price) / self.entry_price) * 100
            position_data['final_pnl_pct'] = final_pnl
        
        logger.info(f"📤 POSITION CLOSED: {exit_reason}")
        
        # Reset position
        self.current_position = None
        self.entry_time = None
        self.entry_price = None
        self.peak_price = None
        self.scale1_hit = False
        self.scale2_hit = False
        self.vwap_exit_blocks = 0
        
        return position_data
    
    def get_position_status(self) -> Optional[Dict]:
        """Get current position status."""
        if not self.current_position:
            return None
        
        return {
            'contract': self.current_position['contract'],
            'strike': self.current_position['strike'],
            'entry_price': self.entry_price,
            'peak_price': self.peak_price,
            'bias': self.current_position['bias'],
            'duration_minutes': (time.time() - self.entry_time) / 60 if self.entry_time else 0,
            'scale1_hit': self.scale1_hit,
            'scale2_hit': self.scale2_hit,
            'vwap_blocks': self.vwap_exit_blocks
        }
