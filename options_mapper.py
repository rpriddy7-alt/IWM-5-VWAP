"""
IWM-5-VWAP Options Mapper
Maps trade signals to exact option contracts with delta targeting.
"""
import time
from typing import Dict, List, Optional
from datetime import datetime
import requests
from logger import setup_logger
from config import Config

logger = setup_logger("OptionsMapper")


class OptionsMapper:
    """
    Maps trade signals to specific option contracts.
    Targets delta ~0.5 for optimal risk/reward.
    """
    
    def __init__(self):
        self.polygon_api_key = Config.POLYGON_API_KEY
        self.base_url = "https://api.polygon.io"
        
    def map_signal_to_option(self, signal: Dict) -> Optional[Dict]:
        """
        Map trade signal to specific option contract.
        Args:
            signal: Trade signal from execution engine
        Returns:
            Option contract details or None
        """
        try:
            # Get options chain for today's expiry
            chain = self._get_options_chain(signal['symbol'], signal['timestamp'])
            
            if not chain:
                logger.warning("No options chain available")
                return None
            
            # Filter and sort options
            options = self._filter_options(chain, signal)
            
            if not options:
                logger.warning("No suitable options found")
                return None
            
            # Select best option
            selected_option = self._select_best_option(options, signal)
            
            if selected_option:
                logger.info(f"📋 OPTION SELECTED: {selected_option['contract']} | "
                           f"Strike: ${selected_option['strike']:.2f} | "
                           f"Delta: {selected_option['delta']:.3f}")
            
            return selected_option
            
        except Exception as e:
            logger.error(f"Error mapping signal to option: {e}")
            return None
    
    def _get_options_chain(self, symbol: str, timestamp: float) -> Optional[List]:
        """Get options chain for today's expiry."""
        try:
            # Get today's date for expiry
            today = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
            
            url = f"{self.base_url}/v3/reference/options/contracts"
            params = {
                'underlying_ticker': symbol,
                'expiration_date': today,
                'apikey': self.polygon_api_key,
                'limit': 1000
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') == 'OK' and data.get('results'):
                return data['results']
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching options chain: {e}")
            return None
    
    def _filter_options(self, chain: List, signal: Dict) -> List:
        """Filter options by type and basic criteria."""
        bias = signal['bias']
        spot = signal['spot']
        
        # Filter by option type
        option_type = 'call' if bias == 'Long' else 'put'
        
        filtered = []
        for option in chain:
            if option.get('option_type') == option_type:
                # Add basic filtering criteria
                strike = option.get('strike_price', 0)
                if strike > 0:  # Valid strike price
                    filtered.append(option)
        
        return filtered
    
    def _select_best_option(self, options: List, signal: Dict) -> Optional[Dict]:
        """Select best option based on delta targeting and proximity to spot."""
        spot = signal['spot']
        bias = signal['bias']
        
        # Sort by proximity to spot price
        options.sort(key=lambda x: abs(x.get('strike_price', 0) - spot))
        
        # Target delta ~0.5
        target_delta = 0.5
        best_option = None
        best_delta_diff = float('inf')
        
        for option in options:
            strike = option.get('strike_price', 0)
            delta = option.get('delta', 0)
            
            # Calculate delta difference from target
            delta_diff = abs(delta - target_delta)
            
            # Prefer options closer to target delta
            if delta_diff < best_delta_diff:
                best_delta_diff = delta_diff
                best_option = option
        
        if best_option:
            return {
                'contract': best_option.get('ticker', ''),
                'strike': best_option.get('strike_price', 0),
                'delta': best_option.get('delta', 0),
                'ask': best_option.get('ask_price', 0),
                'bid': best_option.get('bid_price', 0),
                'spot': spot,
                'bias': bias,
                'expiry': best_option.get('expiration_date', ''),
                'option_type': best_option.get('option_type', '')
            }
        
        return None
    
    def get_option_quote(self, contract: str) -> Optional[Dict]:
        """Get real-time quote for specific option contract."""
        try:
            url = f"{self.base_url}/v2/last/trade/{contract}"
            params = {'apikey': self.polygon_api_key}
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') == 'OK' and data.get('results'):
                result = data['results']
                return {
                    'contract': contract,
                    'last_price': result.get('p', 0),
                    'timestamp': result.get('t', 0)
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching option quote: {e}")
            return None
