"""
Tradier Trading Client for IWM 0DTE System
Handles live trading execution alongside alert notifications.
"""
import time
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timezone
import requests
from logger import setup_logger
from config import Config

logger = setup_logger("TradierClient")


class TradierTradingClient:
    """Tradier trading client for executing trades based on signals."""
    
    def __init__(self):
        self.api_key = Config.TRADIER_TOKEN
        self.account_id = Config.TRADIER_ACCOUNT_ID
        self.base_url = Config.TRADIER_BASE_URL
        self.enabled = Config.TRADIER_ENABLED
        
        # Trading parameters
        self.position_size = Config.TRADIER_POSITION_SIZE
        self.max_positions = Config.TRADIER_MAX_POSITIONS
        self.stop_loss_pct = Config.TRADIER_STOP_LOSS_PCT
        self.take_profit_pct = Config.TRADIER_TAKE_PROFIT_PCT
        
        # Track active positions
        self.active_positions: Dict[str, Dict] = {}
        
        # Check if Tradier is properly configured
        self.is_configured = bool(self.api_key and self.account_id and self.enabled)
        
        if not self.is_configured:
            logger.info("Tradier trading disabled - alerts only mode")
        else:
            logger.info(f"Tradier trading enabled - {self.base_url}")
            logger.info(f"Position size: ${self.position_size}, Max positions: {self.max_positions}")
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict]:
        """Make authenticated request to Tradier API."""
        if not self.is_configured:
            return None
            
        url = f"{self.base_url}{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Accept': 'application/json'
        }
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=data, timeout=10)
            elif method.upper() == 'POST':
                headers['Content-Type'] = 'application/x-www-form-urlencoded'
                response = requests.post(url, headers=headers, data=data, timeout=10)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                return None
            
            response.raise_for_status()
            return response.json() if response.content else {}
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"Tradier API error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Tradier request error: {e}")
            return None
    
    def get_account_info(self) -> Optional[Dict]:
        """Get account information."""
        return self._make_request('GET', f'/v1/accounts/{self.account_id}')
    
    def get_cash_balance(self) -> float:
        """Get available cash balance for trading."""
        try:
            account_info = self.get_account_info()
            if account_info and 'account' in account_info:
                account = account_info['account']
                # Get settled cash (available for trading)
                cash = float(account.get('cash', {}).get('cash_available', 0))
                logger.info(f"Available cash balance: ${cash:.2f}")
                return cash
        except Exception as e:
            logger.error(f"Error getting cash balance: {e}")
        return 0.0
    
    def get_positions(self) -> List[Dict]:
        """Get current positions."""
        response = self._make_request('GET', f'/v1/accounts/{self.account_id}/positions')
        if response and 'positions' in response:
            return response['positions'] if response['positions'] else []
        return []
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """Get specific position for symbol."""
        positions = self.get_positions()
        for position in positions:
            if position.get('symbol') == symbol:
                return position
        return None
    
    def place_order(self, symbol: str, qty: int, side: str, order_type: str = 'market',
                   time_in_force: str = 'day', stop_price: Optional[float] = None,
                   limit_price: Optional[float] = None) -> Optional[Dict]:
        """
        Place a stock order.
        
        Args:
            symbol: Stock symbol (e.g., 'IWM')
            qty: Number of shares
            side: 'buy' or 'sell'
            order_type: 'market', 'limit', 'stop', 'stop_limit'
            time_in_force: 'day', 'gtc', 'ioc', 'fok'
            stop_price: Stop price for stop orders
            limit_price: Limit price for limit orders
        """
        if not self.is_configured:
            logger.warning("Tradier not configured - order not placed")
            return None
        
        # Check if we already have a position
        existing_position = self.get_position(symbol)
        if existing_position and side == 'buy':
            logger.warning(f"Already have position in {symbol} - skipping buy order")
            return None
        
        order_data = {
            'class': 'equity',
            'symbol': symbol,
            'quantity': str(qty),
            'side': side,
            'type': order_type,
            'duration': time_in_force
        }
        
        if stop_price:
            order_data['stop'] = str(stop_price)
        if limit_price:
            order_data['price'] = str(limit_price)
        
        logger.info(f"Placing {side} order: {qty} shares of {symbol}")
        response = self._make_request('POST', f'/v1/accounts/{self.account_id}/orders', order_data)
        
        if response and 'order' in response:
            order = response['order']
            logger.info(f"Order placed successfully: {order.get('id', 'Unknown ID')}")
            return order
        else:
            logger.error(f"Failed to place order for {symbol}")
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        response = self._make_request('DELETE', f'/v1/accounts/{self.account_id}/orders/{order_id}')
        if response is not None:
            logger.info(f"Order {order_id} cancelled")
            return True
        else:
            logger.error(f"Failed to cancel order {order_id}")
            return False
    
    def close_position(self, symbol: str) -> Optional[Dict]:
        """Close all shares of a position."""
        if not self.is_configured:
            return None
            
        position = self.get_position(symbol)
        if not position:
            logger.warning(f"No position found for {symbol}")
            return None
        
        qty = abs(int(float(position.get('quantity', 0))))
        side = 'sell' if float(position.get('quantity', 0)) > 0 else 'buy'
        
        logger.info(f"Closing position: {qty} shares of {symbol}")
        return self.place_order(symbol, qty, side)
    
    def execute_signal_trade(self, signal_data: Dict, strategy: str = 'momentum') -> Optional[Dict]:
        """
        Execute a trade based on signal data.
        
        Args:
            signal_data: Signal information from the strategy
            strategy: Strategy name for logging
        """
        if not self.is_configured:
            logger.info("Tradier not configured - signal trade not executed")
            return None
        
        # Check if we're at max positions
        positions = self.get_positions()
        if len(positions) >= self.max_positions:
            logger.warning(f"At max positions ({self.max_positions}) - skipping trade")
            return None
        
        # Check available cash balance
        available_cash = self.get_cash_balance()
        if available_cash < self.position_size:
            logger.warning(f"Insufficient cash: ${available_cash:.2f} < ${self.position_size:.2f} - skipping trade")
            return None
        
        # Get current IWM price for position sizing
        symbol = Config.UNDERLYING_SYMBOL
        current_price = signal_data.get('current_price', 0)
        
        if current_price <= 0:
            logger.error("No current price available for trade execution")
            return None
        
        # Calculate position size (don't exceed available cash)
        max_shares_by_cash = int(available_cash / current_price)
        shares_by_position_size = int(self.position_size / current_price)
        shares = min(shares_by_position_size, max_shares_by_cash)
        
        if shares < 1:
            logger.warning(f"Position size too small: ${self.position_size} / ${current_price} = {shares} shares")
            return None
        
        # Place buy order
        order = self.place_order(
            symbol=symbol,
            qty=shares,
            side='buy',
            order_type='market'
        )
        
        if order:
            # Track the position
            self.active_positions[symbol] = {
                'order_id': order.get('id'),
                'symbol': symbol,
                'qty': shares,
                'entry_price': current_price,
                'strategy': strategy,
                'entry_time': time.time(),
                'stop_loss': current_price * (1 - self.stop_loss_pct / 100),
                'take_profit': current_price * (1 + self.take_profit_pct / 100)
            }
            
            logger.info(f"Trade executed: {shares} shares of {symbol} at ${current_price:.2f}")
            logger.info(f"Stop loss: ${self.active_positions[symbol]['stop_loss']:.2f}")
            logger.info(f"Take profit: ${self.active_positions[symbol]['take_profit']:.2f}")
        
        return order
    
    def check_exit_conditions(self, current_price: float) -> List[Dict]:
        """
        Check if any positions should be closed based on exit conditions.
        
        Returns:
            List of closed positions
        """
        if not self.is_configured:
            return []
        
        closed_positions = []
        
        for symbol, position in list(self.active_positions.items()):
            should_exit = False
            exit_reason = ""
            
            # Check stop loss
            if current_price <= position['stop_loss']:
                should_exit = True
                exit_reason = f"Stop loss hit: ${current_price:.2f} <= ${position['stop_loss']:.2f}"
            
            # Check take profit
            elif current_price >= position['take_profit']:
                should_exit = True
                exit_reason = f"Take profit hit: ${current_price:.2f} >= ${position['take_profit']:.2f}"
            
            # Check time-based exit (end of day)
            elif self._should_exit_time_based(position):
                should_exit = True
                exit_reason = "End of trading day"
            
            if should_exit:
                logger.info(f"Exit condition met for {symbol}: {exit_reason}")
                
                # Close the position
                close_order = self.close_position(symbol)
                if close_order:
                    position['exit_price'] = current_price
                    position['exit_reason'] = exit_reason
                    position['exit_time'] = time.time()
                    
                    # Calculate P&L
                    pnl = (current_price - position['entry_price']) * position['qty']
                    position['pnl'] = pnl
                    
                    closed_positions.append(position)
                    del self.active_positions[symbol]
                    
                    logger.info(f"Position closed: P&L = ${pnl:.2f}")
        
        return closed_positions
    
    def _should_exit_time_based(self, position: Dict) -> bool:
        """Check if position should be closed based on time."""
        from utils import is_market_hours, get_et_time
        
        # Exit 5 minutes before market close
        current_time = get_et_time()
        if current_time.hour == 15 and current_time.minute >= 55:
            return True
        
        return False
    
    def get_trading_summary(self) -> Dict:
        """Get summary of trading activity."""
        if not self.is_configured:
            return {'enabled': False, 'message': 'Tradier trading disabled'}
        
        positions = self.get_positions()
        account = self.get_account_info()
        
        return {
            'enabled': True,
            'active_positions': len(positions),
            'max_positions': self.max_positions,
            'position_size': self.position_size,
            'account_equity': account.get('account', {}).get('total_equity', 'Unknown') if account else 'Unknown',
            'buying_power': account.get('account', {}).get('buying_power', 'Unknown') if account else 'Unknown',
            'sandbox_mode': getattr(Config, 'TRADIER_SANDBOX_MODE', False),
            'positions': [
                {
                    'symbol': pos.get('symbol'),
                    'quantity': pos.get('quantity'),
                    'market_value': pos.get('market_value'),
                    'cost_basis': pos.get('cost_basis')
                }
                for pos in positions
            ]
        }


if __name__ == "__main__":
    # Test the Tradier client
    client = TradierTradingClient()
    
    if client.is_configured:
        print("✅ Tradier client configured")
        summary = client.get_trading_summary()
        print(f"Account status: {summary}")
    else:
        print("❌ Tradier client not configured")
        print("Set TRADIER_ENABLED=true and provide API credentials")