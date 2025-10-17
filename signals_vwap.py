"""
IWM-5-VWAP Advanced VWAP Strategy System
Advanced VWAP-based strategy for IWM options trading.
"""
import time
from typing import Dict, Tuple, Optional, List
from collections import deque
import numpy as np
from logger import setup_logger
from config import Config
from utils import get_et_time

logger = setup_logger("VWAPSignals")


class IWM5VWAPSignals:
    """
    IWM-5-VWAP Advanced VWAP Strategy System.
    Advanced VWAP-based strategy for IWM options trading.
    """
    
    def __init__(self):
        # Data storage for VWAP ANALYSIS ONLY
        self.per_sec_data: deque = deque(maxlen=1200)  # 20 minutes of data
        self.daily_data: deque = deque(maxlen=390)  # Full trading day (6.5 hours)
        
        # Signal tracking
        self.last_signal_time: Dict[str, float] = {}
        self.signal_cooldown = 10  # 10 seconds between signals
        
        # VWAP analysis
        self.vwap_5min_data = deque(maxlen=300)  # 5 minutes of data for VWAP calculation
        
        # Strategy duration tracking (for exit timing)
        self.strategy_durations = {
            'vwap': 30,  # 30 minutes average for VWAP strategy
        }
        
    def update(self, agg_data: Dict):
        """
        Process per-second aggregate from IWM stocks WebSocket.
        ONLY STOCK DATA - no option contract data here.
        """
        current_time = agg_data.get('t', time.time() * 1000) / 1000
        current_price = agg_data.get('c', 0)
        high_price = agg_data.get('h', current_price)
        low_price = agg_data.get('l', current_price)
        volume = agg_data.get('v', 0)
        
        # Calculate VWAP for this second
        vwap = self._calculate_second_vwap(high_price, low_price, current_price, volume)
        
        # Store data
        data_point = {
            'timestamp': current_time,
            'price': current_price,
            'high': high_price,
            'low': low_price,
            'volume': volume,
            'vwap': vwap
        }
        
        self.per_sec_data.append(data_point)
        self.daily_data.append(data_point)
        
        # Update 5-minute VWAP data
        self.vwap_5min_data.append(data_point)
    
    def check_all_signals(self) -> Dict:
        """
        Check VWAP strategy for entry signals.
        Returns:
            Dict with strategy names as keys and (signal_active, signal_data) tuples
        """
        signals = {}
        
        # Check VWAP strategy based on stock data only
        signals['vwap'] = self._check_vwap_signal()
        
        return signals
    
    def get_best_signal(self) -> Tuple[Optional[str], bool, Dict]:
        """
        Get the best signal from VWAP strategy.
        Returns:
            Tuple of (strategy_name, signal_active, signal_data)
        """
        signals = self.check_all_signals()
        
        # Find active signals
        active_signals = [(name, data) for name, (active, data) in signals.items() if active]
        
        if not active_signals:
            return None, False, {}
        
        # For single strategy, return the VWAP signal
        strategy_name, signal_data = active_signals[0]
        return strategy_name, True, signal_data
    
    def _check_vwap_signal(self) -> Tuple[bool, Dict]:
        """Check VWAP signal based on 5-minute VWAP analysis."""
        if len(self.per_sec_data) < 300:  # Need at least 5 minutes of data
            return False, {}
        
        # Check cooldown
        if self._is_cooldown_active('vwap'):
            return False, {}
        
        current_price = self.per_sec_data[-1]['price']
        current_vwap = self.per_sec_data[-1]['vwap']
        
        # 5-minute VWAP analysis
        vwap_analysis = self._analyze_5min_vwap()
        
        # VWAP signal conditions
        if vwap_analysis['signal']:
            # Set cooldown
            self.last_signal_time['vwap'] = time.time()
            
            signal_data = {
                'strategy': 'vwap',
                'direction': vwap_analysis['direction'],
                'current_price': current_price,
                'vwap': current_vwap,
                'vwap_5min': vwap_analysis['vwap_5min'],
                'price_vs_vwap': vwap_analysis['price_vs_vwap'],
                'trend_strength': vwap_analysis['trend_strength'],
                'reason': vwap_analysis['reason'],
                'timestamp': time.time(),
                'time_et': get_et_time()
            }
            
            logger.warning(f"📊 VWAP SIGNAL: IWM ${current_price:.2f} | "
                          f"5min VWAP ${vwap_analysis['vwap_5min']:.2f} | "
                          f"Direction: {vwap_analysis['direction'].upper()}")
            
            return True, signal_data
        
        return False, {}
    
    def _analyze_5min_vwap(self) -> Dict:
        """Analyze 5-minute VWAP for signal generation."""
        if len(self.vwap_5min_data) < 60:  # Need at least 1 minute
            return {'signal': False}
        
        current_price = self.vwap_5min_data[-1]['price']
        
        # Calculate 5-minute VWAP
        vwap_5min = self._calculate_vwap_5min()
        
        # Price vs VWAP analysis
        price_vs_vwap = ((current_price - vwap_5min) / vwap_5min) * 100
        
        # Trend strength (price momentum over 5 minutes)
        trend_strength = self._calculate_trend_strength()
        
        # Volume confirmation
        volume_confirmation = self._check_volume_confirmation()
        
        # Signal conditions
        signal_conditions = {
            'price_above_vwap': price_vs_vwap > 0.2,  # Price 0.2% above VWAP
            'strong_trend': abs(trend_strength) > 0.5,  # Strong trend
            'volume_confirmed': volume_confirmation,
            'sufficient_data': len(self.vwap_5min_data) >= 300  # 5 minutes of data
        }
        
        # Determine signal
        if all(signal_conditions.values()):
            direction = 'call' if trend_strength > 0 else 'put'
            reason = f"Price {price_vs_vwap:+.2f}% vs VWAP, trend {trend_strength:+.3f}, volume confirmed"
            
            return {
                'signal': True,
                'direction': direction,
                'vwap_5min': vwap_5min,
                'price_vs_vwap': price_vs_vwap,
                'trend_strength': trend_strength,
                'reason': reason
            }
        
        return {'signal': False}
    
    def _calculate_second_vwap(self, high: float, low: float, close: float, volume: float) -> float:
        """Calculate VWAP for a single second."""
        if volume == 0:
            return close
        
        # Typical price for this second
        typical_price = (high + low + close) / 3
        return typical_price
    
    def _calculate_vwap_5min(self) -> float:
        """Calculate 5-minute VWAP."""
        if not self.vwap_5min_data:
            return 0
        
        total_volume = sum(point['volume'] for point in self.vwap_5min_data)
        if total_volume == 0:
            return self.vwap_5min_data[-1]['price']
        
        weighted_sum = sum(
            ((point['high'] + point['low'] + point['price']) / 3) * point['volume']
            for point in self.vwap_5min_data
        )
        
        return weighted_sum / total_volume
    
    def _calculate_trend_strength(self) -> float:
        """Calculate trend strength over 5 minutes."""
        if len(self.vwap_5min_data) < 10:
            return 0
        
        prices = [point['price'] for point in self.vwap_5min_data]
        
        # Linear regression slope
        x = np.arange(len(prices))
        y = np.array(prices)
        
        if len(x) < 2:
            return 0
        
        slope = np.polyfit(x, y, 1)[0]
        return slope / prices[0] if prices[0] != 0 else 0
    
    def _check_volume_confirmation(self) -> bool:
        """Check if volume confirms the signal."""
        if len(self.vwap_5min_data) < 10:
            return False
        
        recent_volumes = [point['volume'] for point in list(self.vwap_5min_data)[-10:]]
        avg_volume = sum(recent_volumes) / len(recent_volumes)
        
        # Volume should be above average
        return recent_volumes[-1] > avg_volume * 1.2
    
    def get_strategy_duration(self, strategy: str) -> int:
        """Get expected duration for strategy (in minutes)."""
        return self.strategy_durations.get(strategy, 30)
    
    def _is_cooldown_active(self, strategy: str) -> bool:
        """Check if strategy is in cooldown period."""
        if strategy not in self.last_signal_time:
            return False
        
        time_since_last = time.time() - self.last_signal_time[strategy]
        return time_since_last < self.signal_cooldown
