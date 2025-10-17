"""
Time-adaptive filtering for different market periods.
Adjusts signal thresholds based on time of day to improve accuracy.
"""
from datetime import time
from typing import Dict
from utils import get_et_time
from logger import setup_logger

logger = setup_logger("TimeFilters")


class TimeAdaptiveFilters:
    """Adjust signal thresholds based on market microstructure by time of day."""
    
    # Time period definitions (ET)
    BLACKOUT_OPENING_START = time(9, 30)
    BLACKOUT_OPENING_END = time(9, 45)
    
    BLACKOUT_LUNCH_START = time(11, 30)
    BLACKOUT_LUNCH_END = time(13, 30)
    
    POWER_START = time(15, 0)
    POWER_END = time(15, 30)
    
    # Threshold multipliers by period (EXACT SPEC)
    MULTIPLIERS = {
        'blackout': {
            # BLACKOUT MODE: 9:30-9:45 ET and 11:30-13:30 ET
            'flow_zscore': 1.75,        # 2.0 → 3.5σ (VERY strict)
            'ask_side_pct': 1.154,      # 65% → 75% (VERY strict)
            'spread_max': 0.667,        # 3.0% → 2.0% (much tighter)
            'volume_percentile': 1.042, # 95th → 99th (very high)
            'relative_volume': 1.333,   # 1.5× → 2.0× (higher)
            'skew_point': 1.5,          # 1.0 → 1.5 vol points (stricter)
            'skew_median_offset': 2.0   # 0.5 → 1.0 above median (stricter)
        },
        'power': {
            # Power hour: standard thresholds
            'flow_zscore': 1.0,
            'ask_side_pct': 1.0,
            'spread_max': 1.0,
            'volume_percentile': 1.0,
            'relative_volume': 1.0,
            'skew_point': 1.0,
            'skew_median_offset': 1.0
        },
        'standard': {
            # Normal mid-day trading: standard thresholds
            'flow_zscore': 1.0,
            'ask_side_pct': 1.0,
            'spread_max': 1.0,
            'volume_percentile': 1.0,
            'relative_volume': 1.0,
            'skew_point': 1.0,
            'skew_median_offset': 1.0
        }
    }
    
    @classmethod
    def get_current_period(cls) -> str:
        """
        Determine current market period based on ET time.
        
        Returns:
            Period name: 'blackout', 'power', or 'standard'
        """
        now = get_et_time().time()
        
        # Check blackout windows (opening + lunch)
        if (cls.BLACKOUT_OPENING_START <= now < cls.BLACKOUT_OPENING_END or
            cls.BLACKOUT_LUNCH_START <= now < cls.BLACKOUT_LUNCH_END):
            return 'blackout'
        elif cls.POWER_START <= now < cls.POWER_END:
            return 'power'
        else:
            return 'standard'
    
    @classmethod
    def is_blackout_period(cls) -> bool:
        """
        Check if currently in blackout period.
        
        Returns:
            True if in blackout window (9:30-9:45 or 11:30-13:30 ET)
        """
        return cls.get_current_period() == 'blackout'
    
    @classmethod
    def get_adjusted_thresholds(cls, base_thresholds: Dict) -> Dict:
        """
        Get adjusted thresholds for current market period.
        
        Args:
            base_thresholds: Dict with keys like 'flow_zscore', 'ask_side_pct', etc.
            
        Returns:
            Adjusted thresholds dict
        """
        period = cls.get_current_period()
        multipliers = cls.MULTIPLIERS.get(period, cls.MULTIPLIERS['standard'])
        
        adjusted = {}
        for key, base_value in base_thresholds.items():
            multiplier = multipliers.get(key, 1.0)
            adjusted[key] = base_value * multiplier
        
        # Log if using non-standard thresholds
        if period != 'standard':
            logger.debug(f"Time period: {period.upper()} - Adjusted thresholds active")
        
        return adjusted
    
    @classmethod
    def get_period_info(cls) -> Dict:
        """
        Get current period info for logging/debugging.
        
        Returns:
            Dict with period, multipliers, and time info
        """
        period = cls.get_current_period()
        now = get_et_time()
        
        return {
            'period': period,
            'time_et': now.strftime('%H:%M:%S ET'),
            'multipliers': cls.MULTIPLIERS[period],
            'description': cls._get_period_description(period)
        }
    
    @classmethod
    def _get_period_description(cls, period: str) -> str:
        """Get human-readable description of period."""
        descriptions = {
            'blackout': 'BLACKOUT MODE - Opening/Lunch (VERY strict filters)',
            'power': 'Power hour (standard filters)',
            'standard': 'Normal trading (standard filters)'
        }
        return descriptions.get(period, 'Unknown period')

