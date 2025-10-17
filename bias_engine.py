"""
IWM-5-VWAP Bias Engine
Determines daily long/short bias from 12-hour overnight session using Strat semantics.
"""
import time
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
import requests
from logger import setup_logger
from config import Config
from utils import get_et_time

logger = setup_logger("BiasEngine")


class StratBiasEngine:
    """
    Strat-based bias determination from 12-hour overnight session.
    Determines daily bias at 03:00 ET using Strat classification.
    """
    
    def __init__(self):
        self.polygon_api_key = Config.POLYGON_API_KEY
        self.base_url = "https://api.polygon.io"
        self.current_bias = None
        self.trigger_high = None
        self.trigger_low = None
        self.bias_timestamp = None
        
    def get_daily_bias(self) -> Dict:
        """
        Get current daily bias. If not set or expired, determine new bias.
        Returns:
            Dict with bias, triggerHigh, triggerLow, timestamp
        """
        # Check if we have a valid bias for today
        if self._is_bias_valid():
            return self._get_bias_dict()
        
        # Determine new bias
        return self._determine_bias()
    
    def _is_bias_valid(self) -> bool:
        """Check if current bias is valid for today."""
        if not self.current_bias or not self.bias_timestamp:
            return False
        
        # Bias is valid until 15:00 ET (market close)
        current_time = get_et_time()
        bias_time = datetime.fromtimestamp(self.bias_timestamp)
        
        # Check if bias is from today and before 15:00 ET
        return (bias_time.date() == current_time.date() and 
                current_time.hour < 15)
    
    def _determine_bias(self) -> Dict:
        """
        Determine daily bias from 12-hour overnight session.
        Uses Strat classification to determine bias.
        """
        try:
            # Get 12-hour extended hours data
            overnight_data = self._get_overnight_data()
            
            if not overnight_data:
                logger.warning("No overnight data available, defaulting to None bias")
                return self._get_bias_dict("None", 0, 0)
            
            # Analyze Strat pattern
            strat_classification = self._analyze_strat_pattern(overnight_data)
            
            # Determine bias and triggers
            bias, trigger_high, trigger_low = self._classify_bias(strat_classification, overnight_data)
            
            # Store bias
            self.current_bias = bias
            self.trigger_high = trigger_high
            self.trigger_low = trigger_low
            self.bias_timestamp = time.time()
            
            logger.info(f"📊 DAILY BIAS DETERMINED: {bias} | "
                       f"Trigger High: ${trigger_high:.2f} | Trigger Low: ${trigger_low:.2f}")
            
            return self._get_bias_dict(bias, trigger_high, trigger_low)
            
        except Exception as e:
            logger.error(f"Error determining bias: {e}")
            return self._get_bias_dict("None", 0, 0)
    
    def _get_overnight_data(self) -> Optional[Dict]:
        """Get 12-hour extended hours data from Polygon."""
        try:
            # Get data for last 12 hours (extended hours)
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=12)
            
            url = f"{self.base_url}/v2/aggs/ticker/IWM/range/1/hour/{start_time.strftime('%Y-%m-%d')}/{end_time.strftime('%Y-%m-%d')}"
            
            params = {
                'apikey': self.polygon_api_key,
                'adjusted': 'true',
                'sort': 'asc',
                'limit': 12
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') == 'OK' and data.get('results'):
                # Get the most recent 12-hour candle
                results = data['results']
                if len(results) >= 1:
                    latest = results[-1]
                    return {
                        'open': latest.get('o', 0),
                        'high': latest.get('h', 0),
                        'low': latest.get('l', 0),
                        'close': latest.get('c', 0),
                        'volume': latest.get('v', 0),
                        'timestamp': latest.get('t', 0)
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching overnight data: {e}")
            return None
    
    def _analyze_strat_pattern(self, data: Dict) -> str:
        """
        Analyze Strat pattern from overnight data.
        Returns: '1', '2-up', '2-down', or '3'
        """
        open_price = data['open']
        high_price = data['high']
        low_price = data['low']
        close_price = data['close']
        
        # Strat classification logic
        if close_price > high_price * 0.95:  # Close near high
            return '2-up'
        elif close_price < low_price * 1.05:  # Close near low
            return '2-down'
        elif high_price > open_price * 1.02 and low_price < open_price * 0.98:  # Wide range
            return '3'
        else:
            return '1'  # Inside day
    
    def _classify_bias(self, strat_class: str, data: Dict) -> Tuple[str, float, float]:
        """
        Classify bias based on Strat pattern.
        Returns: (bias, trigger_high, trigger_low)
        """
        high = data['high']
        low = data['low']
        
        if strat_class == '2-up':
            return 'Long', high, low
        elif strat_class == '2-down':
            return 'Short', high, low
        elif strat_class == '3':
            # Wide range - use breakout levels
            return 'Long', high, low
        else:  # '1' - Inside day
            return 'None', high, low
    
    def _get_bias_dict(self, bias: str = None, trigger_high: float = None, trigger_low: float = None) -> Dict:
        """Get bias dictionary."""
        return {
            'bias': bias or self.current_bias or 'None',
            'triggerHigh': trigger_high or self.trigger_high or 0,
            'triggerLow': trigger_low or self.trigger_low or 0,
            'timestamp': self.bias_timestamp or time.time()
        }
