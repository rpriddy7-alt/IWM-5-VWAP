"""
Risk management for simplified IWM 0DTE momentum system.
Tracks a single position, keeps peak/mark values, and provides summaries.
Momentum exits handled by `SimpleExitMonitor` in `signals.py`.
"""
import time
from typing import Dict, Optional
from logger import setup_logger
from config import Config

logger = setup_logger("RiskManager")


class Position:
    """Represents an active 0DTE call position."""
    
    def __init__(self, contract_symbol: str, entry_data: Dict):
        self.contract_symbol = contract_symbol
        self.entry_time = time.time()
        self.entry_price = entry_data.get('entry_price', 0)
        self.entry_data = entry_data
        
        # Peak tracking for giveback management
        self.peak_mark = self.entry_price
        self.current_mark = self.entry_price
        
        # Exit state
        self.exit_triggered = False
        self.exit_reason = None
        self.exit_time = None
        
        logger.info(f"Position opened: {contract_symbol} @ ${self.entry_price:.2f}")
    
    def update_mark(self, current_price: float):
        """Update current mark and track peak."""
        self.current_mark = current_price
        if current_price > self.peak_mark:
            self.peak_mark = current_price
            logger.debug(f"New peak for {self.contract_symbol}: ${self.peak_mark:.2f}")
    
    def get_pnl_percent(self) -> float:
        """Calculate current P&L percentage."""
        if self.entry_price == 0:
            return 0.0
        return ((self.current_mark - self.entry_price) / self.entry_price) * 100.0
    
    def get_giveback_from_peak(self) -> float:
        """Calculate giveback from peak as percentage."""
        if self.peak_mark == 0:
            return 0.0
        return ((self.peak_mark - self.current_mark) / self.peak_mark) * 100.0
    
    def trigger_exit(self, reason: str):
        """Mark position for exit."""
        if not self.exit_triggered:
            self.exit_triggered = True
            self.exit_reason = reason
            self.exit_time = time.time()
            logger.warning(f"Exit triggered for {self.contract_symbol}: {reason}")


class RiskManager:
    """Manage single-position state for the simplified system."""
    
    def __init__(self):
        self.position: Optional[Position] = None
        
    def has_position(self) -> bool:
        """Check if we have an active position."""
        return self.position is not None and not self.position.exit_triggered
    
    def open_position(self, contract_symbol: str, entry_data: Dict):
        """
        Open a new position.
        
        Args:
            contract_symbol: Contract ticker
            entry_data: Entry details (price, delta, IV, etc.)
        """
        if self.has_position():
            logger.error("Attempted to open position while one already exists")
            return
        
        self.position = Position(contract_symbol, entry_data)
    
    def update_position(self, current_mark: float):
        """
        Update position with current market price.
        
        Args:
            current_mark: Current option mid price
        """
        if not self.has_position():
            return
        
        self.position.update_mark(current_mark)
    
    def get_position_summary(self) -> Optional[Dict]:
        """Get current position summary for logging/alerts."""
        if not self.position:
            return None
        
        pos = self.position
        duration_minutes = (time.time() - pos.entry_time) / 60.0
        
        return {
            'contract': pos.contract_symbol,
            'entry_price': pos.entry_price,
            'current_mark': pos.current_mark,
            'peak_mark': pos.peak_mark,
            'pnl_percent': pos.get_pnl_percent(),
            'giveback_percent': pos.get_giveback_from_peak(),
            'duration_minutes': duration_minutes,
            'exit_triggered': pos.exit_triggered,
            'exit_reason': pos.exit_reason,
            'strategy': pos.entry_data.get('strategy', 'momentum'),
            'is_call': pos.entry_data.get('is_call', True)
        }
    
    def close_position(self) -> Optional[Dict]:
        """
        Close the position and return summary.
        
        Returns:
            Position summary dict or None
        """
        if not self.position:
            return None
        
        summary = self.get_position_summary()
        logger.info(
            f"Position closed: {self.position.contract_symbol} | "
            f"P&L: {summary['pnl_percent']:.1f}%"
        )
        
        self.position = None
        return summary

