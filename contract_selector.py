"""
CORRECTED Multi-Strategy Contract Selection for IWM 0DTE System
Properly handles put contracts with correct strike/delta information.
"""
from typing import Dict, List, Optional, Tuple
from logger import setup_logger
from config import Config
from utils import calculate_mid_price, calculate_spread_percent, get_todays_expiry

logger = setup_logger("CorrectedContractSelector")


class CorrectedMultiStrategyContractSelector:
    """
    CORRECTED contract selector that properly handles put contracts.
    Option contracts are only for alert purposes - stock trends drive strategies.
    """
    
    def __init__(self):
        self.tracked_contracts: Dict[str, List[str]] = {
            'calls': [],
            'puts': []
        }
        self.contract_data: Dict[str, Dict] = {}
        
        # Strategy-specific delta ranges (CORRECTED for puts)
        self.strategy_deltas = {
            'momentum': {'calls': (0.30, 0.45), 'puts': (0.30, 0.45)},
            'gap': {'calls': (0.25, 0.40), 'puts': (0.25, 0.40)},
            'volume': {'calls': (0.35, 0.50), 'puts': (0.35, 0.50)},
            'strength': {'calls': (0.40, 0.55), 'puts': (0.40, 0.55)},
            'combined': {'calls': (0.30, 0.50), 'puts': (0.30, 0.50)}
        }
        
        # Strategy-specific spread tolerances
        self.strategy_spreads = {
            'momentum': 4.0,
            'gap': 5.0,      # Gap plays can tolerate wider spreads
            'volume': 3.5,   # Volume plays need tighter spreads
            'strength': 4.5, # Strength plays can handle wider spreads
            'combined': 4.0  # Combined strategies use moderate spreads
        }
    
    def filter_and_rank_contracts(self, chain_data: List[Dict]) -> Dict[str, List[str]]:
        """
        Select top 0DTE contracts for both calls and puts.
        CORRECTED to properly handle put contract information.
        """
        if not chain_data:
            return {'calls': [], 'puts': []}
        
        # Only log contract selection when chain data changes significantly
        if not hasattr(self, '_last_chain_size') or self._last_chain_size != len(chain_data):
            logger.info(f"Selecting CORRECTED multi-strategy contracts from {len(chain_data)} in chain")
            self._last_chain_size = len(chain_data)
        
        target_expiry = get_todays_expiry()
        call_candidates = []
        put_candidates = []
        
        for contract in chain_data:
            # Extract contract details
            details = contract.get('details', {})
            greeks = contract.get('greeks', {})
            day_data = contract.get('day', {})
            
            contract_type = details.get('contract_type', '')
            expiry = details.get('expiration_date', '')
            strike = details.get('strike_price', 0)
            contract_symbol = details.get('ticker', '')
            
            # 0DTE only
            if expiry != target_expiry:
                continue
            
            # Extract pricing and greeks
            last_quote = contract.get('last_quote', {})
            bid = last_quote.get('bid', 0)
            ask = last_quote.get('ask', 0)
            bid_size = last_quote.get('bid_size', 0)
            ask_size = last_quote.get('ask_size', 0)
            
            # Get delta and IV
            delta = greeks.get('delta')
            iv = contract.get('implied_volatility')
            
            # CORRECTED delta calculation for puts
            if delta is None and strike > 0:
                last_trade = contract.get('last_trade', {})
                underlying_price = last_trade.get('underlying_price', 0)
                
                if underlying_price > 0:
                    pct_diff = (underlying_price - strike) / underlying_price
                    if contract_type == 'call':
                        # For calls: delta ≈ 0.5 at ATM, approaches 0/1 at extremes
                        if pct_diff > 0:  # ITM
                            delta = min(0.50 + pct_diff * 8.0, 0.99)
                        else:  # OTM
                            delta = max(0.50 + pct_diff * 8.0, 0.01)
                    else:  # put
                        # For puts: delta ≈ -0.5 at ATM, approaches 0/-1 at extremes
                        if pct_diff > 0:  # ITM
                            delta = max(-0.50 - pct_diff * 8.0, -0.99)
                        else:  # OTM
                            delta = min(-0.50 - pct_diff * 8.0, -0.01)
            
            # Normalize delta
            try:
                if delta is not None:
                    delta = float(delta)
            except (TypeError, ValueError):
                delta = None
            
            if delta is None:
                continue
            
            volume = day_data.get('volume', 0)
            open_interest = details.get('open_interest', 0)
            
            # Basic filters
            if volume < 100 or bid <= 0 or ask <= 0:
                continue
            
            mid = calculate_mid_price(bid, ask)
            spread_pct = calculate_spread_percent(bid, ask)
            notional = volume * mid * 100
            
            # CORRECTED contract info with proper put handling
            contract_info = {
                'symbol': contract_symbol,
                'strike': strike,
                'delta': delta,  # Keep original delta (negative for puts)
                'iv': iv,
                'mid': mid,
                'bid': bid,
                'ask': ask,
                'spread_pct': spread_pct,
                'bid_size': bid_size,
                'ask_size': ask_size,
                'volume': volume,
                'open_interest': open_interest,
                'notional': notional,
                'contract_type': contract_type
            }
            
            # Separate calls and puts
            if contract_type == 'call':
                call_candidates.append(contract_info)
            elif contract_type == 'put':
                put_candidates.append(contract_info)
        
        # Sort and select top contracts for each type
        call_candidates.sort(key=lambda x: x['notional'], reverse=True)
        put_candidates.sort(key=lambda x: x['notional'], reverse=True)
        
        # Select top N for each type
        top_calls = call_candidates[:Config.MAX_CONTRACTS_TO_TRACK]
        top_puts = put_candidates[:Config.MAX_CONTRACTS_TO_TRACK]
        
        # Update tracked contracts
        self.tracked_contracts['calls'] = [c['symbol'] for c in top_calls]
        self.tracked_contracts['puts'] = [p['symbol'] for p in top_puts]
        
        # Update contract data
        all_contracts = top_calls + top_puts
        self.contract_data = {c['symbol']: c for c in all_contracts}
        
        if top_calls or top_puts:
            call_info = f"{len(top_calls)} calls" if top_calls else "0 calls"
            put_info = f"{len(top_puts)} puts" if top_puts else "0 puts"
            logger.info(f"✓ CORRECTED MULTI-STRATEGY: Selected {call_info}, {put_info}")
            
            # Only log top contracts when they change significantly
            current_calls = [f"{c['symbol']}({c['strike']},Δ{c['delta']:.2f})" for c in top_calls[:3]]
            current_puts = [f"{p['symbol']}({p['strike']},Δ{p['delta']:.2f})" for p in top_puts[:3]]
            
            if not hasattr(self, '_last_top_calls') or self._last_top_calls != current_calls:
                logger.info(f"  Top calls: {', '.join(current_calls)}")
                self._last_top_calls = current_calls
            
            if not hasattr(self, '_last_top_puts') or self._last_top_puts != current_puts:
                logger.info(f"  Top puts: {', '.join(current_puts)}")
                self._last_top_puts = current_puts
        else:
            logger.warning("⚠️ NO contracts available for corrected multi-strategy monitoring!")
        
        return self.tracked_contracts
    
    def get_best_entry_contract(self, signal_data: Dict, strategy: str = 'momentum') -> Optional[Dict]:
        """
        Select the best contract for entry based on strategy and signal direction.
        CORRECTED to properly handle put contracts.
        """
        if not self.contract_data:
            return None
        
        direction = signal_data.get('direction', 'call')
        confidence = signal_data.get('confidence', 0)
        
        # Get appropriate contract type
        if direction == 'call':
            available_contracts = [c for c in self.contract_data.values() 
                                 if c['contract_type'] == 'call']
        elif direction == 'put':
            available_contracts = [c for c in self.contract_data.values() 
                                 if c['contract_type'] == 'put']
        else:
            logger.warning(f"Unknown direction: {direction}")
            return None
        
        if not available_contracts:
            logger.warning(f"No {direction} contracts available")
            return None
        
        # Get strategy-specific criteria
        delta_range = self.strategy_deltas.get(strategy, {'calls': (0.30, 0.45), 'puts': (0.30, 0.45)})
        max_spread = self.strategy_spreads.get(strategy, 4.0)
        
        # CORRECTED delta range filtering for puts (pluralize direction for dict lookup)
        direction_key = direction + 's'  # 'call' -> 'calls', 'put' -> 'puts'
        min_delta, max_delta = delta_range[direction_key]
        
        delta_filtered = []
        for contract in available_contracts:
            if direction == 'put':
                abs_delta = abs(contract['delta'])
                if min_delta <= abs_delta <= max_delta:
                    delta_filtered.append(contract)
            else:
                if min_delta <= contract['delta'] <= max_delta:
                    delta_filtered.append(contract)

        if not delta_filtered:
            logger.warning(
                f"No {direction} contracts in delta range {min_delta}-{max_delta} for {strategy}"
            )
            return None

        # Filter by spread tolerance but retain fallback if all are wide
        candidates = [c for c in delta_filtered if c['spread_pct'] <= max_spread]

        if not candidates:
            tightest = min(delta_filtered, key=lambda c: c['spread_pct'])
            logger.warning(
                f"No {direction} contracts within spread tolerance {max_spread}% for {strategy}. "
                f"Falling back to {tightest['symbol']} (spread {tightest['spread_pct']:.2f}%)."
            )
            candidates = [tightest]
        
        # Score candidates based on strategy
        scored_candidates = []
        
        for contract in candidates:
            score = self._calculate_strategy_score(contract, strategy, confidence, direction)
            scored_candidates.append({
                **contract,
                'total_score': score
            })
        
        # Return highest scoring contract
        best = max(scored_candidates, key=lambda x: x['total_score'])
        
        # CORRECTED logging with proper put information
        delta_display = f"Δ{best['delta']:.2f}" if direction == 'call' else f"Δ{best['delta']:.2f}"
        logger.info(f"Selected {strategy} {direction} contract: {best['symbol']} "
                   f"({delta_display}, spread {best['spread_pct']:.1f}%, "
                   f"score {best['total_score']:.2f})")
        
        return best
    
    def _calculate_strategy_score(self, contract: Dict, strategy: str, confidence: float, direction: str) -> float:
        """
        Calculate contract score based on strategy.
        CORRECTED for proper put handling.
        """
        # CORRECTED delta scoring for puts
        if direction == 'put':
            # For puts, prefer delta closer to -0.40 (absolute value)
            abs_delta = abs(contract['delta'])
            delta_score = 1.0 - abs(abs_delta - 0.40)  # Closer to 0.40 = better
        else:
            # For calls, prefer delta closer to 0.40
            delta_score = 1.0 - abs(contract['delta'] - 0.40)
        
        spread_score = 1.0 - (contract['spread_pct'] / 5.0)  # Prefer tighter spreads
        liquidity_score = min(1.0, contract['volume'] / 1000)  # Prefer higher volume
        
        # Strategy-specific adjustments
        if strategy == 'momentum':
            # Momentum prefers tighter spreads and higher liquidity
            return 0.4 * delta_score + 0.4 * spread_score + 0.2 * liquidity_score
        
        elif strategy == 'gap':
            # Gap plays can tolerate wider spreads, prefer liquidity
            return 0.3 * delta_score + 0.2 * spread_score + 0.5 * liquidity_score
        
        elif strategy == 'volume':
            # Volume plays need tight spreads and high liquidity
            return 0.2 * delta_score + 0.5 * spread_score + 0.3 * liquidity_score
        
        elif strategy == 'strength':
            # Strength plays prefer delta accuracy over spread tightness
            return 0.5 * delta_score + 0.2 * spread_score + 0.3 * liquidity_score
        
        elif strategy == 'combined':
            # Combined strategies use balanced scoring
            return 0.35 * delta_score + 0.35 * spread_score + 0.3 * liquidity_score
        
        else:
            # Default scoring
            return 0.4 * delta_score + 0.4 * spread_score + 0.2 * liquidity_score
    
    def calculate_entry_price(self, contract: Dict, strategy: str = 'momentum') -> float:
        """
        Calculate suggested entry price based on strategy.
        """
        mid = contract['mid']
        spread = contract['ask'] - contract['bid']
        
        # Strategy-specific entry price calculations
        if strategy == 'momentum':
            # Momentum plays: aggressive entry
            if spread <= 0.05:
                offset_pct = 0.05
            elif spread <= 0.10:
                offset_pct = 0.10
            else:
                offset_pct = 0.15
        
        elif strategy == 'gap':
            # Gap plays: more aggressive entry
            if spread <= 0.05:
                offset_pct = 0.10
            elif spread <= 0.10:
                offset_pct = 0.15
            else:
                offset_pct = 0.20
        
        elif strategy == 'volume':
            # Volume plays: conservative entry
            if spread <= 0.05:
                offset_pct = 0.03
            elif spread <= 0.10:
                offset_pct = 0.08
            else:
                offset_pct = 0.12
        
        elif strategy == 'strength':
            # Strength plays: moderate entry
            if spread <= 0.05:
                offset_pct = 0.07
            elif spread <= 0.10:
                offset_pct = 0.12
            else:
                offset_pct = 0.18
        
        elif strategy == 'combined':
            # Combined strategies: moderate entry
            if spread <= 0.05:
                offset_pct = 0.08
            elif spread <= 0.10:
                offset_pct = 0.12
            else:
                offset_pct = 0.16
        
        else:
            # Default
            offset_pct = 0.10
        
        offset = spread * offset_pct
        entry_price = mid + offset
        
        # Don't exceed ask
        entry_price = min(entry_price, contract['ask'])
        
        return round(entry_price, 2)
    
    def get_contract_data(self, symbol: str) -> Optional[Dict]:
        """Get cached data for a specific contract."""
        return self.contract_data.get(symbol)
    
    def is_tracking(self, symbol: str) -> bool:
        """Check if a contract is currently being tracked."""
        return symbol in self.contract_data
    
    def get_contracts_by_type(self, contract_type: str) -> List[Dict]:
        """Get all tracked contracts of a specific type."""
        return [c for c in self.contract_data.values() 
                if c['contract_type'] == contract_type]
    
    def get_contracts_by_strategy(self, strategy: str, direction: str) -> List[Dict]:
        """Get contracts suitable for a specific strategy and direction."""
        if direction not in ['call', 'put']:
            return []
        
        contracts = self.get_contracts_by_type(direction)
        delta_range = self.strategy_deltas.get(strategy, {'calls': (0.30, 0.45), 'puts': (0.30, 0.45)})
        max_spread = self.strategy_spreads.get(strategy, 4.0)
        
        min_delta, max_delta = delta_range[direction]
        
        # CORRECTED filtering for puts
        if direction == 'put':
            return [c for c in contracts 
                    if min_delta <= abs(c['delta']) <= max_delta 
                    and c['spread_pct'] <= max_spread]
        else:
            return [c for c in contracts 
                    if min_delta <= c['delta'] <= max_delta 
                    and c['spread_pct'] <= max_spread]
    
    def validate_contract_selection(self, contract: Dict, direction: str) -> bool:
        """
        Validate that contract selection matches signal direction.
        """
        contract_type = contract.get('contract_type', '')
        
        if direction == 'call' and contract_type != 'call':
            logger.error(f"CONTRACT TYPE MISMATCH: Signal direction=call, Contract type={contract_type}")
            return False
        
        if direction == 'put' and contract_type != 'put':
            logger.error(f"CONTRACT TYPE MISMATCH: Signal direction=put, Contract type={contract_type}")
            return False
        
        # CORRECTED delta validation for puts
        if direction == 'put' and contract.get('delta', 0) > 0:
            logger.warning(f"PUT CONTRACT WITH POSITIVE DELTA: {contract['symbol']} delta={contract['delta']}")
        
        if direction == 'call' and contract.get('delta', 0) < 0:
            logger.warning(f"CALL CONTRACT WITH NEGATIVE DELTA: {contract['symbol']} delta={contract['delta']}")
        
        return True