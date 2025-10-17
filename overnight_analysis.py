"""
Overnight 12h Bar Analysis for IWM Strategy
Analyzes overnight 12h bars (03:00 ET close) for bias determination.
Implements 1-3-1 coil pattern recognition and trigger level tracking.
"""
import time
from typing import Dict, Optional, Tuple, List
from collections import deque
from datetime import datetime, timedelta
import pytz
from logger import setup_logger
from config import Config
from utils import get_et_time

logger = setup_logger("OvernightAnalysis")


class OvernightBarAnalysis:
    """
    Analyzes overnight 12h bars for bias determination.
    Implements 1-3-1 coil pattern recognition and trigger level tracking.
    """
    
    def __init__(self):
        # Overnight bar data (12h bars ending at 03:00 ET)
        self.overnight_bars: deque = deque(maxlen=10)  # Keep last 10 overnight bars
        
        # Current bias state
        self.current_bias: Optional[str] = None  # 'calls', 'puts', or None
        self.bias_confidence: float = 0.0  # 0.0 to 1.0
        
        # Trigger levels
        self.trigger_high: Optional[float] = None
        self.trigger_low: Optional[float] = None
        
        # 1-3-1 coil tracking
        self.coil_pattern: List[str] = []  # Track recent bar types
        self.inside_bar_high: Optional[float] = None
        self.inside_bar_low: Optional[float] = None
        
        # Session tracking
        self.last_analysis_time: Optional[datetime] = None
        
    def update_overnight_bar(self, bar_data: Dict) -> Dict:
        """
        Update with new overnight bar data.
        
        Args:
            bar_data: {
                'timestamp': float,
                'open': float,
                'high': float,
                'low': float,
                'close': float,
                'volume': int
            }
        
        Returns:
            Dict with analysis results
        """
        current_time = get_et_time()
        
        # Check if this is a new overnight bar (03:00 ET close)
        if not self._is_overnight_bar_complete(bar_data, current_time):
            return {'status': 'pending', 'bias': self.current_bias}
        
        # Classify the bar type
        bar_type = self._classify_bar_type(bar_data)
        
        # Store the bar
        overnight_bar = {
            'timestamp': bar_data['timestamp'],
            'open': bar_data['open'],
            'high': bar_data['high'],
            'low': bar_data['low'],
            'close': bar_data['close'],
            'volume': bar_data['volume'],
            'type': bar_type,
            'analysis_time': current_time
        }
        
        self.overnight_bars.append(overnight_bar)
        
        # Update coil pattern
        self._update_coil_pattern(bar_type, bar_data)
        
        # Determine bias
        bias_result = self._determine_bias(bar_data)
        
        # Update trigger levels
        self._update_trigger_levels(bar_data)
        
        # Log the analysis
        self._log_analysis(overnight_bar, bias_result)
        
        return {
            'status': 'complete',
            'bias': bias_result['bias'],
            'confidence': bias_result['confidence'],
            'trigger_high': self.trigger_high,
            'trigger_low': self.trigger_low,
            'bar_type': bar_type,
            'coil_pattern': self.coil_pattern.copy()
        }
    
    def _is_overnight_bar_complete(self, bar_data: Dict, current_time: datetime) -> bool:
        """Check if overnight bar is complete (03:00 ET close)."""
        # Overnight bar ends at 03:00 ET
        target_hour = 3
        target_minute = 0
        
        return (current_time.hour == target_hour and 
                current_time.minute == target_minute and
                current_time.second < 30)  # 30-second window
    
    def _classify_bar_type(self, bar_data: Dict) -> str:
        """
        Classify bar type: 1 (inside), 2-up, 2-down, or 3 (outside).
        
        Args:
            bar_data: Bar data with OHLC
            
        Returns:
            Bar type string
        """
        if len(self.overnight_bars) == 0:
            return 'first'  # First bar of the day
        
        previous_bar = self.overnight_bars[-1]
        
        current_high = bar_data['high']
        current_low = bar_data['low']
        current_close = bar_data['close']
        
        prev_high = previous_bar['high']
        prev_low = previous_bar['low']
        
        # Check if inside bar (1)
        if current_high <= prev_high and current_low >= prev_low:
            return '1'  # Inside bar
        
        # Check if outside bar (3)
        if current_high > prev_high and current_low < prev_low:
            return '3'  # Outside bar
        
        # Check directional breaks (2-up or 2-down)
        if current_close > prev_high:
            return '2-up'  # Break above previous high
        elif current_close < prev_low:
            return '2-down'  # Break below previous low
        
        # Default to inside if no clear break
        return '1'
    
    def _update_coil_pattern(self, bar_type: str, bar_data: Dict):
        """Update 1-3-1 coil pattern tracking."""
        self.coil_pattern.append(bar_type)
        
        # Keep only last 5 bars for pattern analysis
        if len(self.coil_pattern) > 5:
            self.coil_pattern.pop(0)
        
        # Track inside bar levels for trigger calculation
        if bar_type == '1':  # Inside bar
            self.inside_bar_high = bar_data['high']
            self.inside_bar_low = bar_data['low']
    
    def _determine_bias(self, bar_data: Dict) -> Dict:
        """
        Determine bias based on overnight bar analysis.
        
        Returns:
            Dict with bias and confidence
        """
        if len(self.overnight_bars) < 2:
            return {'bias': None, 'confidence': 0.0}
        
        current_bar = self.overnight_bars[-1]
        bar_type = current_bar['type']
        
        # Check for 1-3-1 coil pattern
        coil_strength = self._analyze_coil_pattern()
        
        # Determine bias based on bar type
        if bar_type == '2-up':
            # 2-up break - Bias Long (Calls)
            confidence = 0.7 + (coil_strength * 0.3)  # Higher confidence with coil
            return {'bias': 'calls', 'confidence': min(confidence, 1.0)}
        
        elif bar_type == '2-down':
            # 2-down break - Bias Short (Puts)
            confidence = 0.7 + (coil_strength * 0.3)  # Higher confidence with coil
            return {'bias': 'puts', 'confidence': min(confidence, 1.0)}
        
        elif bar_type == '1':
            # Still inside - No bias yet
            return {'bias': None, 'confidence': 0.0}
        
        else:
            # Outside bar or other - neutral
            return {'bias': None, 'confidence': 0.0}
    
    def _analyze_coil_pattern(self) -> float:
        """
        Analyze 1-3-1 coil pattern strength.
        
        Returns:
            Coil strength (0.0 to 1.0)
        """
        if len(self.coil_pattern) < 3:
            return 0.0
        
        # Look for 1-3-1 pattern in last 3 bars
        recent_pattern = self.coil_pattern[-3:]
        
        if recent_pattern == ['1', '3', '1']:
            return 1.0  # Perfect 1-3-1 coil
        elif '1' in recent_pattern and '3' in recent_pattern:
            return 0.5  # Partial coil
        else:
            return 0.0  # No coil
    
    def _update_trigger_levels(self, bar_data: Dict):
        """Update trigger levels based on inside bar or latest overnight bar."""
        if self.inside_bar_high is not None and self.inside_bar_low is not None:
            # Use inside bar levels if available
            self.trigger_high = self.inside_bar_high
            self.trigger_low = self.inside_bar_low
        else:
            # Use latest overnight bar levels
            self.trigger_high = bar_data['high']
            self.trigger_low = bar_data['low']
    
    def _log_analysis(self, overnight_bar: Dict, bias_result: Dict):
        """Log the overnight analysis results."""
        logger.info(f"Overnight Bar Analysis Complete:")
        logger.info(f"  Bar Type: {overnight_bar['type']}")
        logger.info(f"  Bias: {bias_result['bias']}")
        logger.info(f"  Confidence: {bias_result['confidence']:.2f}")
        logger.info(f"  Trigger High: {self.trigger_high}")
        logger.info(f"  Trigger Low: {self.trigger_low}")
        logger.info(f"  Coil Pattern: {self.coil_pattern}")
    
    def get_current_bias(self) -> Dict:
        """Get current bias state."""
        return {
            'bias': self.current_bias,
            'confidence': self.bias_confidence,
            'trigger_high': self.trigger_high,
            'trigger_low': self.trigger_low,
            'coil_pattern': self.coil_pattern.copy()
        }
    
    def is_bias_set(self) -> bool:
        """Check if bias is set for the day."""
        return self.current_bias is not None and self.bias_confidence > 0.5
    
    def get_trigger_levels(self) -> Tuple[Optional[float], Optional[float]]:
        """Get current trigger levels."""
        return self.trigger_high, self.trigger_low
