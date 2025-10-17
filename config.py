"""
Configuration management for Miyagi 0DTE momentum system.
Loads settings from environment variables with sensible defaults.
"""
import os
from dotenv import load_dotenv
from typing import Dict, Any

# Load environment variables (if .env file exists)
load_dotenv(override=False)


class Config:
    """Central configuration class."""
    
    # API Keys (MUST be provided by user)
    POLYGON_API_KEY: str = os.getenv('POLYGON_API_KEY', '')
    PUSHOVER_TOKEN: str = os.getenv('PUSHOVER_TOKEN', 'a38bjrx57kf4mprrdgr213bhe7hk61')
    PUSHOVER_USER_KEY: str = os.getenv('PUSHOVER_USER_KEY', 'usyhuqctc2s8oa3mk7ksbn5br3b9sy')
    
    # Tradier Trading API (Optional - for live trading)
    TRADIER_TOKEN: str = os.getenv('TRADIER_TOKEN', '')
    TRADIER_ACCOUNT_ID: str = os.getenv('TRADIER_ACCOUNT_ID', '')
    TRADIER_BASE_URL: str = os.getenv('TRADIER_BASE_URL', 'https://api.tradier.com')
    TRADIER_ENABLED: bool = os.getenv('TRADIER_ENABLED', 'OFF').upper() in ['ON', 'TRUE', '1']
    
    # Trading parameters
    UNDERLYING_SYMBOL: str = os.getenv('UNDERLYING_SYMBOL', 'IWM')
    TIMEZONE: str = os.getenv('TIMEZONE', 'America/New_York')
    
    # Multi-symbol support for Overnight Bias Strategy
    # Tier 1 (Best structure, clean flow, daily liquidity)
    OVERNIGHT_BIAS_SYMBOLS_TIER1: list = os.getenv('OVERNIGHT_BIAS_SYMBOLS_TIER1', 'SPY,IWM,QQQ,AAPL,MSFT').split(',')
    
    # Tier 2 (Works well but needs tighter risk control)
    OVERNIGHT_BIAS_SYMBOLS_TIER2: list = os.getenv('OVERNIGHT_BIAS_SYMBOLS_TIER2', 'META,AMD,NVDA,TSLA,AMZN').split(',')
    
    # Tier 3 (Only in strong trend environments)
    OVERNIGHT_BIAS_SYMBOLS_TIER3: list = os.getenv('OVERNIGHT_BIAS_SYMBOLS_TIER3', 'GOOGL,NFLX,BA,INTC,COIN,XLF,XLK,XLE').split(',')
    
    # Default active symbols (Tier 1 only for production)
    OVERNIGHT_BIAS_SYMBOLS: list = os.getenv('OVERNIGHT_BIAS_SYMBOLS', 'SPY,IWM,QQQ').split(',')
    VWAP_STRATEGY_SYMBOLS: list = os.getenv('VWAP_STRATEGY_SYMBOLS', 'SPY,IWM').split(',')
    
    # Symbol tier configuration
    SYMBOL_TIERS = {
        'tier1': OVERNIGHT_BIAS_SYMBOLS_TIER1,
        'tier2': OVERNIGHT_BIAS_SYMBOLS_TIER2,
        'tier3': OVERNIGHT_BIAS_SYMBOLS_TIER3
    }
    
    # Risk control per tier
    TIER_RISK_CONTROLS = {
        'tier1': {'max_positions': 2, 'position_size_multiplier': 1.0, 'time_stop_minutes': 45},
        'tier2': {'max_positions': 1, 'position_size_multiplier': 0.7, 'time_stop_minutes': 30},
        'tier3': {'max_positions': 1, 'position_size_multiplier': 0.5, 'time_stop_minutes': 20}
    }
    
    # Strategy toggles
    ENABLE_VWAP_STRATEGY: bool = os.getenv('ENABLE_VWAP_STRATEGY', 'true').lower() in ['true', '1', 'yes']
    ENABLE_OVERNIGHT_BIAS_STRATEGY: bool = os.getenv('ENABLE_OVERNIGHT_BIAS_STRATEGY', 'true').lower() in ['true', '1', 'yes']
    
    # Tradier Trading Settings
    TRADIER_POSITION_SIZE: float = float(os.getenv('TRADIER_POSITION_SIZE', '100.0'))  # Dollar amount per trade
    TRADIER_MAX_POSITIONS: int = int(os.getenv('TRADIER_MAX_POSITIONS', '3'))  # Max concurrent positions
    TRADIER_STOP_LOSS_PCT: float = float(os.getenv('TRADIER_STOP_LOSS_PCT', '2.0'))  # Stop loss percentage
    TRADIER_TAKE_PROFIT_PCT: float = float(os.getenv('TRADIER_TAKE_PROFIT_PCT', '3.0'))  # Take profit percentage
    
    # Polygon endpoints
    POLYGON_WS_STOCKS: str = "wss://socket.polygon.io/stocks"
    POLYGON_WS_OPTIONS: str = "wss://socket.polygon.io/options"
    POLYGON_REST_BASE: str = "https://api.polygon.io"
    
    # Pushover endpoint
    PUSHOVER_API_URL: str = "https://api.pushover.net/1/messages.json"
    
    # Market hours (Eastern Time)
    MARKET_OPEN: str = "09:30"
    MARKET_CLOSE: str = "16:00"
    HARD_TIME_STOP: str = os.getenv('HARD_TIME_STOP', '15:55')
    NO_ENTRY_AFTER: str = os.getenv('NO_ENTRY_AFTER', '15:55')
    
    # Contract selection criteria
    DELTA_MIN: float = float(os.getenv('DELTA_MIN', '0.30'))
    DELTA_MAX: float = float(os.getenv('DELTA_MAX', '0.45'))
    MIN_BID_ASK_SPREAD_PCT: float = float(os.getenv('MIN_BID_ASK_SPREAD_PCT', '3.0'))
    MAX_ENTRY_SPREAD_PCT: float = 4.0  # Hard limit for entry
    MIN_NBBO_SIZE: int = int(os.getenv('MIN_NBBO_SIZE', '20'))
    MIN_VOLUME: int = int(os.getenv('MIN_VOLUME', '500'))
    MIN_OPEN_INTEREST: int = int(os.getenv('MIN_OPEN_INTEREST', '1000'))
    MAX_CONTRACTS_TO_TRACK: int = int(os.getenv('MAX_CONTRACTS_TO_TRACK', '3'))
    
    # Momentum signal thresholds (realistic for practical trading)
    VWAP_RISING_SECONDS: int = 10  # VWAP must be rising for 10 seconds (was 30)
    SPOT_VOLUME_PERCENTILE: float = 60.0  # Volume surge threshold (60th percentile, was 95th)
    VWAP_LOOKBACK_SECONDS: int = 60
    MIN_MOMENTUM_THRESHOLD: float = 0.0005  # Minimum 0.05% per second momentum (was 0.2%)
    
    # Risk management
    MAX_GIVEBACK_PERCENT: float = float(os.getenv('MAX_GIVEBACK_PERCENT', '30'))
    TIGHTEN_GIVEBACK_PERCENT: float = float(os.getenv('TIGHTEN_GIVEBACK_PERCENT', '20'))
    VWAP_EXIT_BLOCKS: int = 2  # 30-second blocks below VWAP before exit
    
    
    # Anti-chop filters (relaxed for more signals)
    RELATIVE_VOLUME_MIN: float = float(os.getenv('RELATIVE_VOLUME_MIN', '1.2'))  # Was 1.5
    SPY_IWM_LAG_THRESHOLD: float = float(os.getenv('SPY_IWM_LAG_THRESHOLD', '0.30'))  # Was 0.20
    
    # Additional realistic thresholds
    MIN_PRICE_MOVE_PCT: float = 0.1  # Minimum 0.1% price move to trigger
    MAX_SPREAD_PCT: float = 5.0  # Maximum 5% bid-ask spread for entry
    
    # Data refresh intervals
    CHAIN_SNAPSHOT_INTERVAL_SECONDS: int = 60  # Professional: Update chain every 60 seconds
    
    # Resilience
    WS_SILENCE_ALERT_SECONDS: int = 5
    CHAIN_SNAPSHOT_MAX_AGE_SECONDS: int = 60
    PUSHOVER_RETRY_ATTEMPTS: int = 3
    PUSHOVER_RETRY_BACKOFF_BASE: float = 2.0
    
    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE: str = os.getenv('LOG_FILE', 'miyagi_momentum.log')
    
    @classmethod
    def validate(cls) -> Dict[str, Any]:
        """
        Validate that required configuration is present.
        Returns dict with 'valid' bool and 'errors' list.
        """
        errors = []
        
        # Debug environment variable loading
        import os
        from logger import setup_logger
        debug_logger = setup_logger("ConfigDebug")
        
        debug_logger.info(f"Environment check - RENDER: {os.getenv('RENDER', 'Not set')}")
        debug_logger.info(f"POLYGON_API_KEY: {'SET' if cls.POLYGON_API_KEY else 'MISSING'}")
        debug_logger.info(f"PUSHOVER_TOKEN: {'SET' if cls.PUSHOVER_TOKEN else 'MISSING'}")
        debug_logger.info(f"PUSHOVER_USER_KEY: {'SET' if cls.PUSHOVER_USER_KEY else 'MISSING'}")
        debug_logger.info(f"TRADIER_ENABLED: {cls.TRADIER_ENABLED}")
        debug_logger.info(f"TRADIER_TOKEN: {'SET' if cls.TRADIER_TOKEN else 'MISSING'}")
        
        if not cls.POLYGON_API_KEY:
            errors.append("POLYGON_API_KEY is required")
        if not cls.PUSHOVER_TOKEN:
            errors.append("PUSHOVER_TOKEN is required")
        if not cls.PUSHOVER_USER_KEY:
            errors.append("PUSHOVER_USER_KEY is required")
        
        # Tradier validation (only if enabled)
        if cls.TRADIER_ENABLED:
            if not cls.TRADIER_TOKEN:
                errors.append("TRADIER_TOKEN is required when TRADIER_ENABLED=true")
            if not cls.TRADIER_ACCOUNT_ID:
                errors.append("TRADIER_ACCOUNT_ID is required when TRADIER_ENABLED=true")
            
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    @classmethod
    def get_config_summary(cls) -> str:
        """Return a summary of current configuration (safe for logging)."""
        return f"""
Miyagi 0DTE Momentum System Configuration:
  Symbol: {cls.UNDERLYING_SYMBOL}
  Delta Range: {cls.DELTA_MIN} - {cls.DELTA_MAX}
  Max Contracts Tracked: {cls.MAX_CONTRACTS_TO_TRACK}
  Entry Cutoff: {cls.NO_ENTRY_AFTER} ET
  Hard Stop: {cls.HARD_TIME_STOP} ET
  Max Giveback: {cls.MAX_GIVEBACK_PERCENT}%
  Polygon API: {'✓ Configured' if cls.POLYGON_API_KEY else '✗ MISSING'}
  Pushover: {'✓ Configured' if cls.PUSHOVER_TOKEN and cls.PUSHOVER_USER_KEY else '✗ MISSING'}
  Tradier Trading: {'✓ Enabled' if cls.TRADIER_ENABLED and cls.TRADIER_TOKEN else '✗ Disabled'}
"""


if __name__ == "__main__":
    # Quick config check
    validation = Config.validate()
    if validation['valid']:
        print("✓ Configuration valid")
        print(Config.get_config_summary())
    else:
        print("✗ Configuration errors:")
        for error in validation['errors']:
            print(f"  - {error}")

