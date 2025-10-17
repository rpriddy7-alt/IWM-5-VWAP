"""
Utility functions for the IWM momentum system.
"""
from datetime import datetime, time
from typing import Optional, Tuple
import pytz
from config import Config


def get_et_time() -> datetime:
    """Get current time in Eastern timezone."""
    return datetime.now(pytz.timezone(Config.TIMEZONE))


def is_market_hours() -> bool:
    """Check if current time is within regular market hours (9:30-16:00 ET)."""
    now = get_et_time()
    market_open = time(9, 30)
    market_close = time(16, 0)
    return market_open <= now.time() <= market_close


def can_enter_trade() -> bool:
    """Check if new trades can be entered (before NO_ENTRY_AFTER cutoff)."""
    now = get_et_time()
    cutoff_hour, cutoff_minute = map(int, Config.NO_ENTRY_AFTER.split(':'))
    cutoff = time(cutoff_hour, cutoff_minute)
    return now.time() < cutoff and is_market_hours()


def should_force_exit() -> bool:
    """Check if we've hit the hard time stop (must exit all positions)."""
    now = get_et_time()
    stop_hour, stop_minute = map(int, Config.HARD_TIME_STOP.split(':'))
    stop_time = time(stop_hour, stop_minute)
    return now.time() >= stop_time


def get_todays_expiry() -> str:
    """
    Get today's date in YYYY-MM-DD format (for 0DTE options).
    Uses ET timezone.
    """
    return get_et_time().strftime('%Y-%m-%d')


def calculate_mid_price(bid: float, ask: float) -> float:
    """Calculate mid price from bid/ask."""
    return (bid + ask) / 2.0


def calculate_spread_percent(bid: float, ask: float) -> float:
    """Calculate bid-ask spread as percentage of mid."""
    mid = calculate_mid_price(bid, ask)
    if mid == 0:
        return float('inf')
    return ((ask - bid) / mid) * 100.0


def determine_aggressor_side(trade_price: float, bid: float, ask: float, tick_size: float = 0.05) -> str:
    """
    Determine if trade was buyer or seller initiated.
    
    Args:
        trade_price: Execution price
        bid: NBBO bid at trade time
        ask: NBBO ask at trade time
        tick_size: Minimum price increment
        
    Returns:
        'buy' if at/above ask, 'sell' if at/below bid, 'mid' otherwise
    """
    if trade_price >= (ask - 0.5 * tick_size):
        return 'buy'
    elif trade_price <= (bid + 0.5 * tick_size):
        return 'sell'
    else:
        return 'mid'


def format_contract_symbol(underlying: str, expiry: str, strike: float, option_type: str = 'C') -> str:
    """
    Format option contract symbol in OCC format.
    
    Args:
        underlying: Ticker (e.g., 'IWM')
        expiry: Expiry date 'YYYY-MM-DD'
        strike: Strike price
        option_type: 'C' for call, 'P' for put
        
    Returns:
        Formatted contract symbol (e.g., 'O:IWM251002C00210000')
    """
    # Parse expiry
    expiry_dt = datetime.strptime(expiry, '%Y-%m-%d')
    expiry_str = expiry_dt.strftime('%y%m%d')
    
    # Format strike (8 digits: 5 before decimal, 3 after)
    strike_str = f"{int(strike * 1000):08d}"
    
    return f"O:{underlying}{expiry_str}{option_type}{strike_str}"


def parse_contract_symbol(symbol: str) -> Optional[Tuple[str, str, float, str]]:
    """
    Parse OCC format contract symbol.
    
    Args:
        symbol: Contract symbol (e.g., 'O:IWM251002C00210000')
        
    Returns:
        Tuple of (underlying, expiry_date, strike, option_type) or None if invalid
    """
    try:
        # Remove 'O:' prefix if present
        if symbol.startswith('O:'):
            symbol = symbol[2:]
        
        # Extract components (varies by underlying length, IWM is 3 chars)
        underlying = symbol[:3]
        expiry_str = symbol[3:9]  # YYMMDD
        option_type = symbol[9]   # C or P
        strike_str = symbol[10:]  # 8 digits
        
        # Parse expiry
        expiry_dt = datetime.strptime(expiry_str, '%y%m%d')
        expiry_date = expiry_dt.strftime('%Y-%m-%d')
        
        # Parse strike
        strike = int(strike_str) / 1000.0
        
        return underlying, expiry_date, strike, option_type
    except (ValueError, IndexError):
        return None


def calculate_dollar_notional(price: float, size: int, multiplier: int = 100) -> float:
    """
    Calculate dollar notional for an options trade.
    
    Args:
        price: Option price per share
        size: Number of contracts
        multiplier: Contract multiplier (default 100 for standard options)
        
    Returns:
        Dollar notional value
    """
    return price * size * multiplier


def interpolate_iv_at_delta(contracts: list, target_delta: float) -> Optional[float]:
    """
    Interpolate IV at a specific delta from a list of contracts.
    
    Args:
        contracts: List of contract dicts with 'delta' and 'implied_volatility'
        target_delta: Target delta to interpolate at
        
    Returns:
        Interpolated IV or None if insufficient data
    """
    if len(contracts) < 2:
        return None
    
    # Sort by delta
    sorted_contracts = sorted(contracts, key=lambda x: abs(x.get('delta', 0)))
    
    # Find bracketing contracts
    lower, upper = None, None
    for contract in sorted_contracts:
        delta = abs(contract.get('delta', 0))
        if delta <= target_delta:
            lower = contract
        if delta >= target_delta and upper is None:
            upper = contract
    
    if lower is None or upper is None:
        # Return nearest if exact bracketing not available
        return min(contracts, key=lambda x: abs(abs(x.get('delta', 0)) - target_delta)).get('implied_volatility')
    
    # Linear interpolation
    lower_delta = abs(lower.get('delta', 0))
    upper_delta = abs(upper.get('delta', 0))
    lower_iv = lower.get('implied_volatility', 0)
    upper_iv = upper.get('implied_volatility', 0)
    
    if upper_delta == lower_delta:
        return lower_iv
    
    weight = (target_delta - lower_delta) / (upper_delta - lower_delta)
    return lower_iv + weight * (upper_iv - lower_iv)

