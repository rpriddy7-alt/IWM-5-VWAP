"""
Lifetime P&L Tracker for IWM 0DTE momentum system.
Tracks cumulative profit/loss across all trades with persistent storage.
Balance starts at $0 and updates after every sell alert.

NOTE: On Render, data persists during the same deployment but may reset
on redeploys. To add true persistence across restarts, manually add a 
persistent disk in Render dashboard and update PNL_DATA_DIR env var.
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from logger import setup_logger

logger = setup_logger("PnLTracker")


class LifetimePnLTracker:
    """
    Track lifetime P&L with persistent storage that survives deploys.
    Always assumes 1 contract per trade (100 share multiplier).
    """
    
    CONTRACT_MULTIPLIER = 100  # Standard option contract = 100 shares
    
    def __init__(self):
        """Initialize tracker and load existing data."""
        # Use environment variable for data directory (Render-safe path)
        data_dir = os.getenv('PNL_DATA_DIR', 'data')
        self.data_dir = Path(data_dir)
        self.pnl_file = self.data_dir / "lifetime_pnl.json"
        
        # Ensure directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.data = self._load_data()
        logger.info(f"P&L Tracker initialized at {self.data_dir}")
        logger.info(f"Lifetime Balance: ${self.data['lifetime_balance']:.2f}")
    
    def _load_data(self) -> Dict:
        """Load existing P&L data or create new."""
        if self.pnl_file.exists():
            try:
                with open(self.pnl_file, 'r') as f:
                    data = json.load(f)
                logger.info(f"Loaded existing P&L data: {data['total_trades']} trades, "
                           f"${data['lifetime_balance']:.2f} balance")
                return data
            except Exception as e:
                logger.error(f"Error loading P&L data: {e}, creating new")
                return self._create_new_data()
        else:
            logger.info("No existing P&L data found, starting fresh at $0.00")
            return self._create_new_data()
    
    def _create_new_data(self) -> Dict:
        """Create fresh P&L data structure."""
        return {
            'lifetime_balance': 0.0,
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'last_trade_pnl': 0.0,
            'last_trade_timestamp': None,
            'first_trade_timestamp': None,
            'best_trade': 0.0,
            'worst_trade': 0.0
        }
    
    def _save_data(self):
        """Persist P&L data to disk."""
        try:
            # Ensure directory exists
            self.pnl_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write atomically (temp file + rename)
            temp_file = self.pnl_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(self.data, f, indent=2)
            
            temp_file.replace(self.pnl_file)
            logger.debug(f"P&L data saved to {self.pnl_file}")
            
        except Exception as e:
            logger.error(f"Failed to save P&L data: {e}")
    
    def record_trade(self, entry_price: float, exit_price: float, 
                     contract_symbol: str, exit_reason: str, 
                     blackout_mode: bool = False) -> Dict:
        """
        Record a completed trade and update lifetime balance.
        
        Args:
            entry_price: Entry price per share
            exit_price: Exit price per share
            contract_symbol: Contract ticker
            exit_reason: Why position was closed
            blackout_mode: Was this a blackout mode trade
            
        Returns:
            Dict with trade summary and updated totals
        """
        # Calculate P&L (1 contract = 100 shares)
        price_diff = exit_price - entry_price
        pnl_dollars = price_diff * self.CONTRACT_MULTIPLIER
        pnl_percent = (price_diff / entry_price * 100) if entry_price > 0 else 0
        
        # Update totals
        self.data['lifetime_balance'] += pnl_dollars
        self.data['total_trades'] += 1
        self.data['last_trade_pnl'] = pnl_dollars
        self.data['last_trade_timestamp'] = datetime.now().isoformat()
        
        # Track wins/losses
        if pnl_dollars > 0:
            self.data['wins'] += 1
        else:
            self.data['losses'] += 1
        
        # Track best/worst
        if self.data['total_trades'] == 1:
            self.data['first_trade_timestamp'] = datetime.now().isoformat()
            self.data['best_trade'] = pnl_dollars
            self.data['worst_trade'] = pnl_dollars
        else:
            if pnl_dollars > self.data['best_trade']:
                self.data['best_trade'] = pnl_dollars
            if pnl_dollars < self.data['worst_trade']:
                self.data['worst_trade'] = pnl_dollars
        
        # Save to disk
        self._save_data()
        
        # Log the trade
        mode_tag = "[BLACKOUT]" if blackout_mode else "[NORMAL]"
        logger.warning(f"Trade #{self.data['total_trades']} {mode_tag}: "
                      f"{contract_symbol} ${entry_price:.2f}→${exit_price:.2f} "
                      f"= {pnl_dollars:+.2f} ({pnl_percent:+.1f}%) | "
                      f"Lifetime: ${self.data['lifetime_balance']:.2f}")
        
        # Return summary
        return {
            'trade_number': self.data['total_trades'],
            'pnl_dollars': pnl_dollars,
            'pnl_percent': pnl_percent,
            'lifetime_balance': self.data['lifetime_balance'],
            'wins': self.data['wins'],
            'losses': self.data['losses'],
            'win_rate': (self.data['wins'] / self.data['total_trades'] * 100) 
                        if self.data['total_trades'] > 0 else 0,
            'best_trade': self.data['best_trade'],
            'worst_trade': self.data['worst_trade'],
            'exit_reason': exit_reason,
            'blackout_mode': blackout_mode
        }
    
    def get_current_balance(self) -> float:
        """Get current lifetime balance."""
        return self.data['lifetime_balance']
    
    def get_stats(self) -> Dict:
        """Get full statistics summary."""
        total = self.data['total_trades']
        wins = self.data['wins']
        losses = self.data['losses']
        
        return {
            'lifetime_balance': self.data['lifetime_balance'],
            'total_trades': total,
            'wins': wins,
            'losses': losses,
            'win_rate': (wins / total * 100) if total > 0 else 0,
            'best_trade': self.data['best_trade'],
            'worst_trade': self.data['worst_trade'],
            'avg_trade': (self.data['lifetime_balance'] / total) if total > 0 else 0
        }
    
    def is_critical_loss(self, threshold: float = -500.0) -> bool:
        """
        Check if lifetime balance has hit critical loss threshold.
        
        Args:
            threshold: Loss threshold (default -$500)
            
        Returns:
            True if balance <= threshold
        """
        if self.data['lifetime_balance'] <= threshold:
            logger.critical(f"⚠️ CRITICAL LOSS THRESHOLD HIT: "
                          f"${self.data['lifetime_balance']:.2f} <= ${threshold:.2f}")
            return True
        return False


# Global instance
_tracker = None

def get_tracker() -> LifetimePnLTracker:
    """Get or create global P&L tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = LifetimePnLTracker()
    return _tracker

