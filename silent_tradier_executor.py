"""
Silent Tradier Executor for IWM Strategy
Completely separate trading execution that runs quietly in background.
No interference with alerts - just silent buy/sell automation.
"""
import time
import threading
from typing import Dict, Optional, List
from datetime import datetime
from logger import setup_logger
from config import Config
from tradier_client import TradierTradingClient
from utils import get_et_time, is_market_hours

logger = setup_logger("SilentTradier")


class SilentTradierExecutor:
    """
    Silent Tradier executor that runs completely separate from alerts.
    Handles automatic buying/selling based on strategy signals.
    """
    
    def __init__(self):
        # Initialize Tradier client
        self.tradier = TradierTradingClient()
        
        # Silent execution state (COMPLETELY SEPARATE FROM ALERTS)
        self.silent_enabled = Config.TRADIER_ENABLED
        self.daily_balance = 1000.0  # Tradier starting balance (SEPARATE)
        self.available_balance = 1000.0  # Tradier available balance (SEPARATE)
        self.daily_trades = 0
        self.max_daily_trades = 3  # Maximum trades per day
        
        # Position tracking
        self.active_positions: Dict[str, Dict] = {}
        self.daily_pnl = 0.0
        
        # Tradier trading fees (per trade)
        self.tradier_commission = 0.0  # Tradier commission (varies by plan)
        self.tradier_sec_fee = 0.00051  # SEC fee (per $1000 of sales)
        self.tradier_finra_fee = 0.000119  # FINRA fee (per share sold)
        self.tradier_regulatory_fee = 0.000119  # Regulatory fee (per share)
        
        # Balance management
        self.balance_check_time = None
        self.last_balance_check = None
        
        if self.silent_enabled:
            logger.info("Silent Tradier executor enabled - running quietly in background (SEPARATE FROM ALERTS)")
            self._check_daily_balance()
        else:
            logger.info("Silent Tradier executor disabled - alerts only mode")
    
    def _check_daily_balance(self):
        """Check available balance at start of each day."""
        try:
            if self.tradier.is_configured:
                # Get actual Tradier account balance (SEPARATE FROM ALERTS)
                balance = self.tradier.get_cash_balance()
                if balance > 0:
                    self.available_balance = balance
                    self.daily_balance = balance
                    logger.info(f"Tradier balance check: ${balance:.2f} available (SEPARATE FROM ALERTS)")
                else:
                    logger.warning("No Tradier balance - silent trading disabled (ALERTS UNAFFECTED)")
                    self.silent_enabled = False
            else:
                logger.warning("Tradier not configured - using simulation mode")
                self.available_balance = 1000.0
        except Exception as e:
            logger.error(f"Balance check failed: {e}")
            self.silent_enabled = False
    
    def execute_silent_buy(self, alert_data: Dict) -> bool:
        """
        Execute silent buy order based on alert data.
        
        Args:
            alert_data: Alert data from strategy
            
        Returns:
            True if order placed successfully
        """
        if not self.silent_enabled:
            return False
        
        try:
            # Extract trade information from alert
            symbol = alert_data.get('symbol', 'IWM')
            current_price = alert_data.get('current_price', 0)
            strategy = alert_data.get('strategy', 'IWM-5-VWAP')
            confidence = alert_data.get('confidence', 0.0)
            
            if current_price <= 0:
                logger.error("No valid price for silent buy")
                return False
            
            # Check if we have available balance
            if self.available_balance < 100:  # Minimum trade size
                logger.warning("Insufficient balance for silent buy")
                return False
            
            # Check daily trade limit
            if self.daily_trades >= self.max_daily_trades:
                logger.warning("Daily trade limit reached")
                return False
            
            # Calculate position size based on available balance
            # Use full balance for high confidence, split for lower confidence
            if confidence >= 0.8:
                # High confidence - use full available balance
                trade_amount = self.available_balance
            elif confidence >= 0.6:
                # Medium confidence - use 70% of available balance
                trade_amount = self.available_balance * 0.7
            else:
                # Lower confidence - use 50% of available balance
                trade_amount = self.available_balance * 0.5
            
            # Calculate shares
            shares = int(trade_amount / current_price)
            if shares < 1:
                logger.warning("Position size too small for silent buy")
                return False
            
            # Calculate fees for this trade
            total_fees = self._calculate_tradier_fees(trade_amount, shares, is_sell=False)
            
            # Check if we have enough for trade + fees
            if self.available_balance < (trade_amount + total_fees):
                logger.warning(f"Insufficient Tradier balance for trade + fees: ${self.available_balance:.2f} < ${trade_amount + total_fees:.2f}")
                return False
            
            # Execute silent buy order
            order_result = self.tradier.place_order(
                symbol=symbol,
                qty=shares,
                side='buy',
                order_type='market'
            )
            
            if order_result:
                # Track the position silently
                self.active_positions[symbol] = {
                    'order_id': order_result.get('id'),
                    'symbol': symbol,
                    'qty': shares,
                    'entry_price': current_price,
                    'strategy': strategy,
                    'entry_time': time.time(),
                    'trade_amount': trade_amount,
                    'confidence': confidence
                }
                
                # Update available balance with fees
                self.available_balance -= (trade_amount + total_fees)
                self.daily_trades += 1
                
                logger.info(f"Silent buy executed: {shares} shares of {symbol} at ${current_price:.2f}")
                logger.info(f"Trade amount: ${trade_amount:.2f}, Fees: ${total_fees:.4f}, Remaining balance: ${self.available_balance:.2f}")
                
                return True
            else:
                logger.error("Silent buy order failed")
                return False
                
        except Exception as e:
            logger.error(f"Silent buy execution error: {e}")
            return False
    
    def execute_silent_sell(self, alert_data: Dict) -> bool:
        """
        Execute silent sell order based on alert data.
        
        Args:
            alert_data: Alert data from strategy
            
        Returns:
            True if order placed successfully
        """
        if not self.silent_enabled:
            return False
        
        try:
            symbol = alert_data.get('symbol', 'IWM')
            
            # Check if we have an active position
            if symbol not in self.active_positions:
                logger.warning(f"No active position for {symbol} to sell")
                return False
            
            position = self.active_positions[symbol]
            qty = position['qty']
            entry_price = position['entry_price']
            
            # Get current price for P&L calculation
            current_price = alert_data.get('current_price', entry_price)
            
            # Execute silent sell order
            order_result = self.tradier.place_order(
                symbol=symbol,
                qty=qty,
                side='sell',
                order_type='market'
            )
            
            if order_result:
                # Calculate P&L
                pnl = (current_price - entry_price) * qty
                self.daily_pnl += pnl
                
                # Calculate fees for sell
                trade_amount = current_price * qty
                sell_fees = self._calculate_tradier_fees(trade_amount, qty, is_sell=True)
                
                # Update available balance (proceeds minus fees)
                self.available_balance += (trade_amount - sell_fees)
                
                # Remove position
                del self.active_positions[symbol]
                
                logger.info(f"Silent sell executed: {qty} shares of {symbol} at ${current_price:.2f}")
                logger.info(f"P&L: ${pnl:.2f}, Fees: ${sell_fees:.4f}, Total P&L: ${self.daily_pnl:.2f}")
                logger.info(f"Updated balance: ${self.available_balance:.2f}")
                
                return True
            else:
                logger.error("Silent sell order failed")
                return False
                
        except Exception as e:
            logger.error(f"Silent sell execution error: {e}")
            return False
    
    def check_exit_conditions(self, current_price: float) -> List[Dict]:
        """
        Check exit conditions for active positions.
        
        Args:
            current_price: Current market price
            
        Returns:
            List of positions that should be exited
        """
        if not self.silent_enabled:
            return []
        
        exit_positions = []
        
        for symbol, position in self.active_positions.items():
            entry_price = position['entry_price']
            qty = position['qty']
            entry_time = position['entry_time']
            
            # Calculate current P&L
            pnl = (current_price - entry_price) * qty
            pnl_pct = (current_price - entry_price) / entry_price * 100
            
            # Check exit conditions
            should_exit = False
            exit_reason = ""
            
            # Stop loss check (2% loss)
            if pnl_pct <= -2.0:
                should_exit = True
                exit_reason = "Stop loss triggered"
            
            # Take profit check (3% gain)
            elif pnl_pct >= 3.0:
                should_exit = True
                exit_reason = "Take profit triggered"
            
            # Time-based exit (end of day)
            elif self._should_exit_for_time():
                should_exit = True
                exit_reason = "End of day exit"
            
            if should_exit:
                exit_positions.append({
                    'symbol': symbol,
                    'position': position,
                    'current_price': current_price,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'exit_reason': exit_reason
                })
        
        return exit_positions
    
    def _calculate_tradier_fees(self, trade_amount: float, shares: int, is_sell: bool) -> float:
        """
        Calculate Tradier trading fees.
        
        Args:
            trade_amount: Dollar amount of trade
            shares: Number of shares
            is_sell: Whether this is a sell trade
            
        Returns:
            Total fees for the trade
        """
        total_fees = 0.0
        
        # Commission (if applicable)
        total_fees += self.tradier_commission
        
        # SEC fee (on sales only)
        if is_sell:
            sec_fee = trade_amount * self.tradier_sec_fee
            total_fees += sec_fee
        
        # FINRA fee (on sales only, per share)
        if is_sell and shares > 0:
            finra_fee = shares * self.tradier_finra_fee
            total_fees += finra_fee
        
        # Regulatory fee (per share)
        if shares > 0:
            regulatory_fee = shares * self.tradier_regulatory_fee
            total_fees += regulatory_fee
        
        return total_fees
    
    def _should_exit_for_time(self) -> bool:
        """Check if we should exit positions due to time."""
        current_time = get_et_time()
        
        # Exit 5 minutes before market close
        if current_time.hour == 15 and current_time.minute >= 55:
            return True
        
        return False
    
    def get_daily_summary(self) -> Dict:
        """Get daily trading summary."""
        return {
            'daily_balance': self.daily_balance,
            'available_balance': self.available_balance,
            'daily_pnl': self.daily_pnl,
            'daily_trades': self.daily_trades,
            'active_positions': len(self.active_positions),
            'silent_enabled': self.silent_enabled
        }
    
    def reset_daily_state(self):
        """Reset daily state for new trading day."""
        self.daily_balance = 1000.0
        self.available_balance = 1000.0
        self.daily_trades = 0
        self.daily_pnl = 0.0
        self.active_positions.clear()
        
        # Check balance for new day
        self._check_daily_balance()
        
        logger.info("Daily state reset - ready for new trading day")


# Global silent executor instance
silent_executor = SilentTradierExecutor()
