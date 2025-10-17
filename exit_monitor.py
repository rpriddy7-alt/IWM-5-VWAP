"""
IWM-5-VWAP Exit Monitor
Advanced VWAP-based exit strategy for IWM options trading.
"""
import time
from typing import Dict, Tuple
from logger import setup_logger
from config import Config

logger = setup_logger("VWAPExitMonitor")


class IWM5VWAPExitMonitor:
    """
    IWM-5-VWAP Exit Monitor for advanced VWAP-based exits.
    """
    
    def __init__(self):
        self.max_giveback_pct = Config.MAX_GIVEBACK_PERCENT
        self.tighten_giveback_pct = Config.TIGHTEN_GIVEBACK_PERCENT
        self.vwap_exit_blocks = Config.VWAP_EXIT_BLOCKS
        
    def should_exit(self, position_data: Dict, market_data: Dict, strategy: str = 'vwap') -> Tuple[bool, str]:
        """
        Check if position should exit based on VWAP strategy rules.
        
        Args:
            position_data: Position information from risk manager
            market_data: Current market data
            strategy: Strategy name (always 'vwap' for this system)
            
        Returns:
            Tuple of (should_exit, exit_reason)
        """
        if not position_data:
            return False, ""
        
        current_price = market_data.get('current_price', 0)
        vwap = market_data.get('vwap_1min', 0)
        entry_price = position_data.get('entry_price', 0)
        peak_price = position_data.get('peak_price', entry_price)
        
        if entry_price == 0 or current_price == 0:
            return False, ""
        
        # Calculate P&L
        pnl_pct = ((current_price - entry_price) / entry_price) * 100
        
        # VWAP-based exit conditions
        exit_conditions = {
            'max_giveback': pnl_pct <= -self.max_giveback_pct,
            'tighten_giveback': pnl_pct <= -self.tighten_giveback_pct and current_price < vwap,
            'vwap_exit': self._check_vwap_exit_blocks(market_data),
            'time_stop': self._check_time_stop()
        }
        
        # Check exit conditions
        for condition, should_exit in exit_conditions.items():
            if should_exit:
                reason = self._get_exit_reason(condition, pnl_pct, current_price, vwap)
                logger.warning(f"📤 VWAP EXIT: {reason}")
                return True, reason
        
        return False, ""
    
    def _check_vwap_exit_blocks(self, market_data: Dict) -> bool:
        """Check if price has been below VWAP for too many blocks."""
        # This would need to track VWAP blocks over time
        # For now, return False as this requires more complex tracking
        return False
    
    def _check_time_stop(self) -> bool:
        """Check if time stop has been reached."""
        from utils import should_force_exit
        return should_force_exit()
    
    def _get_exit_reason(self, condition: str, pnl_pct: float, current_price: float, vwap: float) -> str:
        """Get human-readable exit reason."""
        reasons = {
            'max_giveback': f"Max giveback hit ({pnl_pct:.1f}%)",
            'tighten_giveback': f"Tighten giveback hit ({pnl_pct:.1f}%) below VWAP",
            'vwap_exit': f"Below VWAP too long (${current_price:.2f} vs ${vwap:.2f})",
            'time_stop': "Time stop reached (15:55 ET)"
        }
        return reasons.get(condition, "Unknown exit condition")
