"""
IWM-5-VWAP Execution Engine
Monitors 5-minute VWAP and level breaks for trade signals.
"""
import time
from typing import Dict, Optional, Tuple
from collections import deque
from datetime import datetime
from logger import setup_logger
from config import Config
from utils import get_et_time

logger = setup_logger("ExecutionEngine")


class VWAPExecutionEngine:
    """
    Execution engine for 5-minute VWAP and level break monitoring.
    Generates trade signals based on bias triggers and VWAP confirmation.
    """
    
    def __init__(self, bias_engine):
        self.bias_engine = bias_engine
        self.vwap_data = deque(maxlen=300)  # 5 minutes of data
        self.last_5min_close = None
        self.current_vwap = 0
        self.signal_cooldown = 300  # 5 minutes between signals
        
    def update(self, agg_data: Dict):
        """
        Update execution engine with new market data.
        Args:
            agg_data: Real-time aggregate data from Polygon
        """
        current_time = agg_data.get('t', time.time() * 1000) / 1000
        current_price = agg_data.get('c', 0)
        high_price = agg_data.get('h', current_price)
        low_price = agg_data.get('l', current_price)
        volume = agg_data.get('v', 0)
        
        # Calculate VWAP for this tick
        vwap = self._calculate_tick_vwap(high_price, low_price, current_price, volume)
        
        # Store data
        data_point = {
            'timestamp': current_time,
            'price': current_price,
            'high': high_price,
            'low': low_price,
            'volume': volume,
            'vwap': vwap
        }
        
        self.vwap_data.append(data_point)
        self.current_vwap = vwap
        
        # Check for 5-minute close
        if self._is_5min_close(current_time):
            self._check_5min_triggers()
    
    def _calculate_tick_vwap(self, high: float, low: float, close: float, volume: float) -> float:
        """Calculate VWAP for a single tick."""
        if volume == 0:
            return close
        
        # Typical price for this tick
        typical_price = (high + low + close) / 3
        return typical_price
    
    def _is_5min_close(self, current_time: float) -> bool:
        """Check if we're at a 5-minute candle close."""
        # Check if we're at a 5-minute boundary
        dt = datetime.fromtimestamp(current_time)
        return dt.minute % 5 == 0 and dt.second < 5
    
    def _check_5min_triggers(self) -> Optional[Dict]:
        """
        Check for 5-minute trigger conditions.
        Returns trade signal if conditions are met.
        """
        if len(self.vwap_data) < 10:
            return None
        
        # Get current bias
        bias_data = self.bias_engine.get_daily_bias()
        bias = bias_data.get('bias', 'None')
        trigger_high = bias_data.get('triggerHigh', 0)
        trigger_low = bias_data.get('triggerLow', 0)
        
        if bias == 'None':
            return None
        
        current_price = self.vwap_data[-1]['price']
        current_vwap = self.current_vwap
        
        # Check trigger conditions
        if bias == 'Long':
            # Long bias: price above trigger high AND above VWAP
            if current_price > trigger_high and current_price > current_vwap:
                return self._generate_trade_signal('Long', current_price, current_vwap, trigger_high)
        
        elif bias == 'Short':
            # Short bias: price below trigger low AND below VWAP
            if current_price < trigger_low and current_price < current_vwap:
                return self._generate_trade_signal('Short', current_price, current_vwap, trigger_low)
        
        return None
    
    def _generate_trade_signal(self, bias: str, price: float, vwap: float, trigger: float) -> Dict:
        """Generate trade signal."""
        signal = {
            'signal': 'ENTRY',
            'bias': bias,
            'symbol': 'IWM',
            'spot': price,
            'vwap': vwap,
            'trigger': trigger,
            'timestamp': time.time(),
            'time_et': get_et_time()
        }
        
        logger.warning(f"🚀 TRADE SIGNAL: {bias} IWM @ ${price:.2f} | "
                      f"VWAP ${vwap:.2f} | Trigger ${trigger:.2f}")
        
        return signal
    
    def get_current_vwap(self) -> float:
        """Get current VWAP."""
        return self.current_vwap
    
    def get_vwap_trend(self) -> str:
        """Get VWAP trend direction."""
        if len(self.vwap_data) < 10:
            return 'neutral'
        
        recent_vwap = [point['vwap'] for point in list(self.vwap_data)[-10:]]
        if recent_vwap[-1] > recent_vwap[0]:
            return 'rising'
        elif recent_vwap[-1] < recent_vwap[0]:
            return 'falling'
        else:
            return 'neutral'
