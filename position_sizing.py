"""
Position Sizing and Scaling System for IWM Strategy
Implements specific position sizing rules and profit-taking scaling.
"""
import time
from typing import Dict, Optional, Tuple, List
from datetime import datetime
from logger import setup_logger
from config import Config

logger = setup_logger("PositionSizing")


class PositionSizing:
    """
    Position sizing and scaling system for IWM strategy.
    Implements specific sizing rules and profit-taking scaling.
    """
    
    def __init__(self, account_size: float = 7000.0):
        """
        Initialize position sizing system.
        
        Args:
            account_size: Total account size in dollars
        """
        self.account_size = account_size
        self.cash_reserve = account_size / 3  # 1/3 in reserve
        self.available_cash = account_size - self.cash_reserve
        
        # Position sizing rules
        self.first_entry_size = account_size / 3  # ~$2.3k for $7k account
        self.add_on_size = account_size / 3  # Another 1/3 for add-on
        self.max_daily_loss = account_size * 0.10  # 10% max daily loss
        
        # Current positions
        self.current_positions: List[Dict] = []
        self.total_risk: float = 0.0
        self.daily_pnl: float = 0.0
        
        # Scaling rules
        self.scale_1_target = 0.35  # 35% profit for first scale
        self.scale_2_target = 0.85  # 85% profit for second scale
        self.runner_size = 0.20  # 20% of position for runner
        
        # Risk management
        self.max_positions = 2  # Max concurrent positions
        self.position_cooldown = 300  # 5 minutes between positions
        
    def calculate_position_size(self, bias: str, option_price: float, 
                              trigger_level: float, current_price: float) -> Dict:
        """
        Calculate position size for new entry.
        
        Args:
            bias: 'calls' or 'puts'
            option_price: Current option price
            trigger_level: Trigger level for invalidation
            current_price: Current stock price
            
        Returns:
            Dict with position sizing details
        """
        # Check if we can enter new position
        if not self._can_enter_position():
            return {'status': 'blocked', 'reason': 'max_positions_or_cooldown'}
        
        # Calculate risk per trade
        risk_per_trade = self._calculate_risk_per_trade(option_price, trigger_level, current_price)
        
        # Calculate position size
        if len(self.current_positions) == 0:
            # First entry
            position_size = self.first_entry_size
            position_type = 'first_entry'
        else:
            # Add-on entry (only after clean retest)
            position_size = self.add_on_size
            position_type = 'add_on'
        
        # Calculate number of contracts
        num_contracts = int(position_size / option_price)
        actual_size = num_contracts * option_price
        
        # Check if we have enough cash
        if actual_size > self.available_cash:
            return {'status': 'insufficient_cash', 'available': self.available_cash}
        
        # Calculate risk metrics
        max_loss = num_contracts * option_price  # 100% loss scenario
        risk_percent = (max_loss / self.account_size) * 100
        
        return {
            'status': 'approved',
            'position_size': actual_size,
            'num_contracts': num_contracts,
            'option_price': option_price,
            'max_loss': max_loss,
            'risk_percent': risk_percent,
            'position_type': position_type,
            'available_cash': self.available_cash - actual_size
        }
    
    def _can_enter_position(self) -> bool:
        """Check if we can enter a new position."""
        # Check max positions
        if len(self.current_positions) >= self.max_positions:
            return False
        
        # Check cooldown
        if self.current_positions:
            last_position = self.current_positions[-1]
            time_since_last = time.time() - last_position['entry_time']
            if time_since_last < self.position_cooldown:
                return False
        
        # Check daily loss limit
        if self.daily_pnl <= -self.max_daily_loss:
            return False
        
        return True
    
    def _calculate_risk_per_trade(self, option_price: float, trigger_level: float, 
                                 current_price: float) -> float:
        """
        Calculate risk per trade based on invalidation scenario.
        
        Args:
            option_price: Current option price
            trigger_level: Trigger level for invalidation
            current_price: Current stock price
            
        Returns:
            Risk amount in dollars
        """
        # Risk is 100% of option premium if invalidated
        return option_price
    
    def add_position(self, position_data: Dict) -> bool:
        """
        Add new position to tracking.
        
        Args:
            position_data: Position details
            
        Returns:
            True if added successfully, False otherwise
        """
        if not self._can_enter_position():
            return False
        
        position = {
            'id': len(self.current_positions) + 1,
            'bias': position_data['bias'],
            'entry_time': time.time(),
            'option_price': position_data['option_price'],
            'num_contracts': position_data['num_contracts'],
            'position_size': position_data['position_size'],
            'trigger_level': position_data['trigger_level'],
            'scales_taken': [],
            'runner_active': True,
            'status': 'active'
        }
        
        self.current_positions.append(position)
        self.available_cash -= position_data['position_size']
        
        logger.info(f"Position added: {position_data['bias']} - {position_data['num_contracts']} contracts")
        
        return True
    
    def update_position_pnl(self, position_id: int, current_option_price: float) -> Dict:
        """
        Update position P&L and check for scaling opportunities.
        
        Args:
            position_id: Position ID to update
            current_option_price: Current option price
            
        Returns:
            Dict with scaling recommendations
        """
        position = self._get_position(position_id)
        if not position:
            return {'status': 'position_not_found'}
        
        # Calculate P&L
        entry_price = position['option_price']
        pnl_per_contract = current_option_price - entry_price
        pnl_percent = pnl_per_contract / entry_price
        total_pnl = pnl_per_contract * position['num_contracts']
        
        # Update position
        position['current_price'] = current_option_price
        position['pnl_percent'] = pnl_percent
        position['total_pnl'] = total_pnl
        
        # Check for scaling opportunities
        scaling_recommendations = self._check_scaling_opportunities(position, pnl_percent)
        
        return {
            'status': 'updated',
            'position_id': position_id,
            'pnl_percent': pnl_percent,
            'total_pnl': total_pnl,
            'scaling_recommendations': scaling_recommendations
        }
    
    def _check_scaling_opportunities(self, position: Dict, pnl_percent: float) -> List[Dict]:
        """
        Check for scaling opportunities.
        
        Args:
            position: Position data
            pnl_percent: Current P&L percentage
            
        Returns:
            List of scaling recommendations
        """
        recommendations = []
        
        # Scale 1: 30-50% profit
        if (pnl_percent >= self.scale_1_target and 
            'scale_1' not in position['scales_taken']):
            recommendations.append({
                'scale': 'scale_1',
                'target_percent': self.scale_1_target,
                'current_percent': pnl_percent,
                'action': 'take_50_percent'
            })
        
        # Scale 2: 70-100% profit
        if (pnl_percent >= self.scale_2_target and 
            'scale_2' not in position['scales_taken']):
            recommendations.append({
                'scale': 'scale_2',
                'target_percent': self.scale_2_target,
                'current_percent': pnl_percent,
                'action': 'take_30_percent'
            })
        
        return recommendations
    
    def execute_scale(self, position_id: int, scale_type: str) -> Dict:
        """
        Execute scaling action.
        
        Args:
            position_id: Position ID
            scale_type: 'scale_1' or 'scale_2'
            
        Returns:
            Dict with scale execution result
        """
        position = self._get_position(position_id)
        if not position:
            return {'status': 'position_not_found'}
        
        if scale_type in position['scales_taken']:
            return {'status': 'scale_already_taken'}
        
        # Calculate scale size
        if scale_type == 'scale_1':
            scale_percent = 0.50  # Take 50% of position
        elif scale_type == 'scale_2':
            scale_percent = 0.30  # Take 30% of position
        else:
            return {'status': 'invalid_scale_type'}
        
        # Calculate scale details
        contracts_to_sell = int(position['num_contracts'] * scale_percent)
        scale_value = contracts_to_sell * position['current_price']
        
        # Update position
        position['scales_taken'].append(scale_type)
        position['num_contracts'] -= contracts_to_sell
        
        # Update available cash
        self.available_cash += scale_value
        
        logger.info(f"Scale executed: {scale_type} - {contracts_to_sell} contracts")
        
        return {
            'status': 'executed',
            'scale_type': scale_type,
            'contracts_sold': contracts_to_sell,
            'scale_value': scale_value,
            'remaining_contracts': position['num_contracts']
        }
    
    def close_position(self, position_id: int, reason: str) -> Dict:
        """
        Close position completely.
        
        Args:
            position_id: Position ID
            reason: Reason for closing
            
        Returns:
            Dict with close result
        """
        position = self._get_position(position_id)
        if not position:
            return {'status': 'position_not_found'}
        
        # Calculate final P&L
        final_pnl = position.get('total_pnl', 0)
        self.daily_pnl += final_pnl
        
        # Update available cash
        self.available_cash += position['position_size'] + final_pnl
        
        # Remove position
        self.current_positions = [p for p in self.current_positions if p['id'] != position_id]
        
        logger.info(f"Position closed: {position_id} - Reason: {reason} - P&L: {final_pnl:.2f}")
        
        return {
            'status': 'closed',
            'position_id': position_id,
            'final_pnl': final_pnl,
            'reason': reason
        }
    
    def _get_position(self, position_id: int) -> Optional[Dict]:
        """Get position by ID."""
        for position in self.current_positions:
            if position['id'] == position_id:
                return position
        return None
    
    def get_position_summary(self) -> Dict:
        """Get current position summary."""
        total_positions = len(self.current_positions)
        total_risk = sum(p.get('total_pnl', 0) for p in self.current_positions)
        
        return {
            'total_positions': total_positions,
            'available_cash': self.available_cash,
            'total_risk': total_risk,
            'daily_pnl': self.daily_pnl,
            'max_daily_loss': self.max_daily_loss,
            'positions': self.current_positions.copy()
        }
    
    def check_daily_loss_limit(self) -> bool:
        """Check if daily loss limit reached."""
        return self.daily_pnl <= -self.max_daily_loss
    
    def reset_daily_pnl(self):
        """Reset daily P&L (call at start of new day)."""
        self.daily_pnl = 0.0
        logger.info("Daily P&L reset")
