"""
Session VWAP Analysis for IWM Strategy
Implements session VWAP as fairness line for intraday control.
Tracks VWAP alignment and control for entry/exit decisions.
"""
import time
from typing import Dict, Optional, Tuple
from collections import deque
from datetime import datetime
import numpy as np
from logger import setup_logger
from config import Config
from utils import get_et_time

logger = setup_logger("SessionVWAP")


class SessionVWAP:
    """
    Session VWAP analysis for intraday control.
    Tracks VWAP alignment and control for entry/exit decisions.
    """
    
    def __init__(self):
        # Session data storage
        self.session_data: deque = deque(maxlen=10000)  # Full session data
        self.current_vwap: float = 0.0
        self.session_volume: float = 0.0
        self.session_pv: float = 0.0  # Price * Volume sum
        
        # VWAP control tracking
        self.vwap_control_side: Optional[str] = None  # 'above' or 'below'
        self.consecutive_closes_above: int = 0
        self.consecutive_closes_below: int = 0
        
        # Session state
        self.session_start_time: Optional[datetime] = None
        self.session_active: bool = False
        
        # VWAP alignment tracking
        self.price_vs_vwap: Optional[str] = None  # 'above', 'below', or 'at'
        self.vwap_strength: float = 0.0  # 0.0 to 1.0
        
    def start_session(self):
        """Start new trading session."""
        self.session_start_time = get_et_time()
        self.session_active = True
        self.session_data.clear()
        self.current_vwap = 0.0
        self.session_volume = 0.0
        self.session_pv = 0.0
        self.vwap_control_side = None
        self.consecutive_closes_above = 0
        self.consecutive_closes_below = 0
        
        logger.info("Session VWAP started")
    
    def update(self, tick_data: Dict) -> Dict:
        """
        Update session VWAP with new tick data.
        
        Args:
            tick_data: {
                'timestamp': float,
                'price': float,
                'volume': int
            }
        
        Returns:
            Dict with VWAP analysis
        """
        if not self.session_active:
            return {'status': 'inactive'}
        
        # Extract data
        timestamp = tick_data.get('timestamp', time.time())
        price = tick_data.get('price', 0.0)
        volume = tick_data.get('volume', 0)
        
        # Store tick data
        tick_entry = {
            'timestamp': timestamp,
            'price': price,
            'volume': volume
        }
        self.session_data.append(tick_entry)
        
        # Update session totals
        self.session_volume += volume
        self.session_pv += price * volume
        
        # Calculate current VWAP
        if self.session_volume > 0:
            self.current_vwap = self.session_pv / self.session_volume
        
        # Analyze VWAP control
        control_analysis = self._analyze_vwap_control(price)
        
        # Determine VWAP alignment
        alignment = self._determine_vwap_alignment(price)
        
        # Calculate VWAP strength
        strength = self._calculate_vwap_strength()
        
        return {
            'status': 'active',
            'current_vwap': self.current_vwap,
            'session_volume': self.session_volume,
            'price_vs_vwap': alignment,
            'vwap_control_side': self.vwap_control_side,
            'consecutive_closes_above': self.consecutive_closes_above,
            'consecutive_closes_below': self.consecutive_closes_below,
            'vwap_strength': strength,
            'control_analysis': control_analysis
        }
    
    def _analyze_vwap_control(self, current_price: float) -> Dict:
        """
        Analyze VWAP control and consecutive closes.
        
        Args:
            current_price: Current price to analyze
            
        Returns:
            Dict with control analysis
        """
        if self.current_vwap == 0:
            return {'control': 'none', 'consecutive': 0}
        
        # Determine current side
        if current_price > self.current_vwap:
            current_side = 'above'
        elif current_price < self.current_vwap:
            current_side = 'below'
        else:
            current_side = 'at'
        
        # Update consecutive closes
        if current_side == 'above':
            self.consecutive_closes_above += 1
            self.consecutive_closes_below = 0
        elif current_side == 'below':
            self.consecutive_closes_below += 1
            self.consecutive_closes_above = 0
        else:
            # At VWAP - reset counters
            self.consecutive_closes_above = 0
            self.consecutive_closes_below = 0
        
        # Determine control side
        if self.consecutive_closes_above >= 2:
            self.vwap_control_side = 'above'
        elif self.consecutive_closes_below >= 2:
            self.vwap_control_side = 'below'
        else:
            self.vwap_control_side = None
        
        return {
            'control': self.vwap_control_side,
            'consecutive_above': self.consecutive_closes_above,
            'consecutive_below': self.consecutive_closes_below,
            'current_side': current_side
        }
    
    def _determine_vwap_alignment(self, current_price: float) -> str:
        """
        Determine price alignment with VWAP.
        
        Args:
            current_price: Current price to analyze
            
        Returns:
            Alignment string
        """
        if self.current_vwap == 0:
            return 'unknown'
        
        price_diff = abs(current_price - self.current_vwap)
        vwap_pct = price_diff / self.current_vwap
        
        if vwap_pct < 0.001:  # Within 0.1%
            return 'at'
        elif current_price > self.current_vwap:
            return 'above'
        else:
            return 'below'
    
    def _calculate_vwap_strength(self) -> float:
        """
        Calculate VWAP strength based on recent price action.
        
        Returns:
            VWAP strength (0.0 to 1.0)
        """
        if len(self.session_data) < 10:
            return 0.0
        
        # Get recent price data
        recent_prices = [tick['price'] for tick in list(self.session_data)[-10:]]
        
        if not recent_prices:
            return 0.0
        
        # Calculate price momentum
        price_momentum = np.std(recent_prices) / np.mean(recent_prices)
        
        # Calculate VWAP distance
        current_price = recent_prices[-1]
        vwap_distance = abs(current_price - self.current_vwap) / self.current_vwap
        
        # Combine factors for strength
        strength = min(price_momentum * vwap_distance * 10, 1.0)
        
        return strength
    
    def is_price_above_vwap(self) -> bool:
        """Check if current price is above VWAP."""
        if not self.session_data:
            return False
        
        current_price = self.session_data[-1]['price']
        return current_price > self.current_vwap
    
    def is_price_below_vwap(self) -> bool:
        """Check if current price is below VWAP."""
        if not self.session_data:
            return False
        
        current_price = self.session_data[-1]['price']
        return current_price < self.current_vwap
    
    def get_vwap_control_status(self) -> Dict:
        """Get current VWAP control status."""
        return {
            'current_vwap': self.current_vwap,
            'control_side': self.vwap_control_side,
            'consecutive_above': self.consecutive_closes_above,
            'consecutive_below': self.consecutive_closes_below,
            'price_vs_vwap': self.price_vs_vwap,
            'vwap_strength': self.vwap_strength
        }
    
    def is_vwap_aligned_for_bias(self, bias: str) -> bool:
        """
        Check if VWAP is aligned for the given bias.
        
        Args:
            bias: 'calls' or 'puts'
            
        Returns:
            True if aligned, False otherwise
        """
        if bias == 'calls':
            return self.is_price_above_vwap()
        elif bias == 'puts':
            return self.is_price_below_vwap()
        else:
            return False
    
    def has_vwap_control(self, bias: str) -> bool:
        """
        Check if VWAP control is established for the given bias.
        
        Args:
            bias: 'calls' or 'puts'
            
        Returns:
            True if control established, False otherwise
        """
        if bias == 'calls':
            return self.vwap_control_side == 'above'
        elif bias == 'puts':
            return self.vwap_control_side == 'below'
        else:
            return False
    
    def end_session(self):
        """End trading session."""
        self.session_active = False
        logger.info(f"Session VWAP ended - Final VWAP: {self.current_vwap:.2f}")
