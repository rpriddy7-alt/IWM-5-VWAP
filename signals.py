"""
CORRECTED Multi-Strategy Signal Detection for IWM 0DTE System
Stock trend analysis drives strategies, option contracts are only for alert purposes.
"""
import time
from typing import Dict, Tuple, Optional, List
from collections import deque
import numpy as np
from logger import setup_logger
from config import Config
from utils import get_et_time

logger = setup_logger("CorrectedSignals")


class CorrectedMultiStrategySignals:
    """
    CORRECTED multi-strategy signal detection system.
    Stock trends drive strategies, option contracts are only for alert purposes.
    """
    
    def __init__(self):
        # Data storage for STOCK ANALYSIS ONLY
        self.per_sec_data: deque = deque(maxlen=1200)  # 20 minutes of data
        self.daily_data: deque = deque(maxlen=390)  # Full trading day (6.5 hours)
        
        # Signal tracking
        self.last_signal_time: Dict[str, float] = {}
        self.signal_cooldown = 10  # 10 seconds between signals per strategy
        
        # Gap detection
        self.previous_close = None
        self.gap_threshold = 0.5  # 0.5% gap threshold
        
        # Volume analysis
        self.volume_profile = deque(maxlen=100)  # Last 100 volume readings
        
        # Strength indicators
        self.rsi_period = 14
        self.rsi_data = deque(maxlen=self.rsi_period)
        
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
        vwap = agg_data.get('a', 0)
        
        # Store per-second data
        self.per_sec_data.append({
            'timestamp': current_time,
            'price': current_price,
            'high': high_price,
            'low': low_price,
            'volume': volume,
            'vwap': vwap
        })
        
        # Store daily data for gap analysis
        self.daily_data.append({
            'timestamp': current_time,
            'price': current_price,
            'high': high_price,
            'low': low_price,
            'volume': volume,
            'vwap': vwap
        })
        
        # Update volume profile
        self.volume_profile.append(volume)
        
        # Update RSI data
        self._update_rsi(current_price)
        
        # Set previous close for gap detection (first data point of day)
        if self.previous_close is None and len(self.daily_data) == 1:
            self.previous_close = current_price
    
    def check_all_signals(self) -> Dict[str, Tuple[bool, Dict]]:
        """
        Check all strategies based on STOCK TRENDS ONLY.
        
        Returns:
            Dict with strategy names as keys and (signal_active, signal_data) tuples
        """
        signals = {}
        
        # Check VWAP strategy based on stock data only
        signals['vwap'] = self._check_vwap_signal()
        
        return signals
    
    def get_best_signal(self) -> Tuple[Optional[str], bool, Dict]:
        """
        Get the best signal from all strategies.
        Returns strategy combinations if multiple strategies are active.
        """
        all_signals = self.check_all_signals()
        
        # Find all active strategies
        active_strategies = []
        for strategy, (active, data) in all_signals.items():
            if active:
                active_strategies.append((strategy, data))
        
        if not active_strategies:
            return None, False, {}
        
        # If multiple strategies active, combine them
        if len(active_strategies) > 1:
            return self._combine_strategies(active_strategies)
        
        # Single strategy active
        strategy, data = active_strategies[0]
        return strategy, True, data
    
    def _combine_strategies(self, active_strategies: List[Tuple[str, Dict]]) -> Tuple[str, bool, Dict]:
        """
        Combine multiple active strategies into a single signal.
        """
        # Calculate combined confidence
        total_confidence = sum(data.get('confidence', 0) for _, data in active_strategies)
        avg_confidence = total_confidence / len(active_strategies)
        
        # Determine combined direction (majority wins)
        call_count = sum(1 for _, data in active_strategies if data.get('direction') == 'call')
        put_count = len(active_strategies) - call_count
        combined_direction = 'call' if call_count > put_count else 'put'
        
        # Get the strongest individual signal data
        strongest_strategy, strongest_data = max(active_strategies, 
                                               key=lambda x: x[1].get('confidence', 0))
        
        # Create combined signal data
        combined_data = {
            'strategy': 'combined',
            'strategies': [strategy for strategy, _ in active_strategies],
            'direction': combined_direction,
            'confidence': min(0.95, avg_confidence * 1.2),  # Boost for combination
            'current_price': strongest_data.get('current_price', 0),
            'vwap_1min': strongest_data.get('vwap_1min', 0),
            'timestamp': time.time(),
            'time_et': get_et_time().strftime('%H:%M:%S'),
            'strategy_count': len(active_strategies)
        }
        
        # Add strategy-specific data
        for strategy, data in active_strategies:
            if strategy == 'momentum':
                combined_data['momentum_momentum'] = data.get('price_momentum', 0)
                combined_data['momentum_vol_zscore'] = data.get('volume_zscore', 0)
            elif strategy == 'gap':
                combined_data['gap_percent'] = data.get('gap_percent', 0)
                combined_data['gap_volume_conf'] = data.get('volume_confirmation', False)
            elif strategy == 'volume':
                combined_data['volume_zscore'] = data.get('volume_zscore', 0)
                combined_data['volume_price_change'] = data.get('price_change', 0)
            elif strategy == 'strength':
                combined_data['strength_rsi'] = data.get('rsi', 0)
                combined_data['strength_trend'] = data.get('trend_strength', 0)
        
        return 'combined', True, combined_data
    
    def _check_momentum_signal(self) -> Tuple[bool, Dict]:
        """Check momentum strategy based on STOCK TRENDS ONLY."""
        if len(self.per_sec_data) < Config.VWAP_LOOKBACK_SECONDS:
            return False, {}
        
        # Check cooldown
        if self._is_cooldown_active('momentum'):
            return False, {}
        
        recent_data = list(self.per_sec_data)[-Config.VWAP_LOOKBACK_SECONDS:]
        
        # Calculate metrics
        vwap_1min = self._calculate_vwap(recent_data[-60:])
        current_price = recent_data[-1]['price']
        
        # Momentum conditions
        price_above_vwap = current_price > vwap_1min
        vwap_rising = self._check_vwap_rising(recent_data[-30:])
        volume_surge, vol_zscore = self._check_volume_surge(recent_data)
        price_momentum = self._check_price_momentum(recent_data[-30:])
        momentum_threshold_met = price_momentum >= Config.MIN_MOMENTUM_THRESHOLD
        
        # Calculate confidence
        confidence = 0
        if price_above_vwap:
            confidence += 0.3
        if vwap_rising:
            confidence += 0.2
        if volume_surge:
            confidence += 0.3
        if momentum_threshold_met:
            confidence += 0.2
        
        signal_active = (
            price_above_vwap and
            vwap_rising and
            volume_surge and
            momentum_threshold_met
        )
        
        # Determine direction based on STOCK TREND
        direction = 'call' if price_momentum > 0 else 'put'
        
        signal_data = {
            'strategy': 'momentum',
            'direction': direction,
            'current_price': current_price,
            'vwap_1min': vwap_1min,
            'vwap_distance': ((current_price - vwap_1min) / vwap_1min) * 100,
            'vwap_rising': vwap_rising,
            'volume_zscore': vol_zscore,
            'price_momentum': price_momentum,
            'confidence': confidence,
            'timestamp': time.time(),
            'time_et': get_et_time().strftime('%H:%M:%S')
        }
        
        if signal_active:
            self.last_signal_time['momentum'] = time.time()
            logger.warning(f"🚀 MOMENTUM SIGNAL: IWM ${current_price:.2f} > VWAP ${vwap_1min:.2f} "
                         f"(+{signal_data['vwap_distance']:.2f}%), Vol Z={vol_zscore:.1f}, "
                         f"Momentum={price_momentum:.3f}, Direction: {direction.upper()}, Confidence={confidence:.2f}")
        
        return signal_active, signal_data
    
    
    def _check_gap_signal(self) -> Tuple[bool, Dict]:
        """Check gap strategy based on STOCK TRENDS ONLY."""
        if len(self.daily_data) < 2 or self.previous_close is None:
            return False, {}
        
        # Check cooldown
        if self._is_cooldown_active('gap'):
            return False, {}
        
        current_price = self.daily_data[-1]['price']
        gap_percent = ((current_price - self.previous_close) / self.previous_close) * 100
        
        # Gap conditions
        gap_up = gap_percent > self.gap_threshold
        gap_down = gap_percent < -self.gap_threshold
        
        # Volume confirmation
        recent_volume = list(self.volume_profile)[-10:] if len(self.volume_profile) >= 10 else []
        avg_volume = np.mean(recent_volume) if recent_volume else 0
        current_volume = self.daily_data[-1]['volume']
        volume_confirmation = current_volume > avg_volume * 1.5
        
        # Determine signal based on STOCK GAP
        signal_active = False
        direction = 'neutral'
        confidence = 0
        
        if gap_up and volume_confirmation:
            signal_active = True
            direction = 'call'
            confidence = min(0.9, abs(gap_percent) / 2.0)
        elif gap_down and volume_confirmation:
            signal_active = True
            direction = 'put'
            confidence = min(0.9, abs(gap_percent) / 2.0)
        
        signal_data = {
            'strategy': 'gap',
            'direction': direction,
            'current_price': current_price,
            'previous_close': self.previous_close,
            'gap_percent': gap_percent,
            'volume_confirmation': volume_confirmation,
            'confidence': confidence,
            'timestamp': time.time(),
            'time_et': get_et_time().strftime('%H:%M:%S')
        }
        
        if signal_active:
            self.last_signal_time['gap'] = time.time()
            logger.warning(f"📈 GAP SIGNAL: IWM ${current_price:.2f} vs ${self.previous_close:.2f} "
                         f"({gap_percent:+.2f}%), Volume: {volume_confirmation}, "
                         f"Direction: {direction.upper()}, Confidence: {confidence:.2f}")
        
        return signal_active, signal_data
    
    def _check_volume_signal(self) -> Tuple[bool, Dict]:
        """Check volume surge strategy based on STOCK TRENDS ONLY."""
        if len(self.per_sec_data) < 60:
            return False, {}
        
        # Check cooldown
        if self._is_cooldown_active('volume'):
            return False, {}
        
        recent_data = list(self.per_sec_data)[-60:]
        current_price = recent_data[-1]['price']
        current_volume = recent_data[-1]['volume']
        
        # Volume analysis
        volumes = [d['volume'] for d in recent_data]
        volume_surge, vol_zscore = self._check_volume_surge(recent_data)
        
        # Price direction with volume
        price_change = (current_price - recent_data[0]['price']) / recent_data[0]['price'] * 100
        price_up = price_change > 0.1
        price_down = price_change < -0.1
        
        # Volume spike conditions
        volume_spike = vol_zscore > 2.5
        volume_breakout = current_volume > np.percentile(volumes[:-1], 98)
        
        # Determine signal based on STOCK VOLUME + PRICE
        signal_active = False
        direction = 'neutral'
        confidence = 0
        
        if volume_spike and volume_breakout:
            if price_up:
                signal_active = True
                direction = 'call'
                confidence = min(0.9, vol_zscore / 4.0)
            elif price_down:
                signal_active = True
                direction = 'put'
                confidence = min(0.9, vol_zscore / 4.0)
        
        signal_data = {
            'strategy': 'volume',
            'direction': direction,
            'current_price': current_price,
            'volume_zscore': vol_zscore,
            'price_change': price_change,
            'volume_spike': volume_spike,
            'volume_breakout': volume_breakout,
            'confidence': confidence,
            'timestamp': time.time(),
            'time_et': get_et_time().strftime('%H:%M:%S')
        }
        
        if signal_active:
            self.last_signal_time['volume'] = time.time()
            logger.warning(f"📊 VOLUME SIGNAL: IWM ${current_price:.2f} "
                         f"({price_change:+.2f}%), Vol Z={vol_zscore:.1f}, "
                         f"Direction: {direction.upper()}, Confidence: {confidence:.2f}")
        
        return signal_active, signal_data
    
    def _check_strength_signal(self) -> Tuple[bool, Dict]:
        """Check strength indicators based on STOCK TRENDS ONLY."""
        if len(self.per_sec_data) < 30 or len(self.rsi_data) < self.rsi_period:
            return False, {}
        
        # Check cooldown
        if self._is_cooldown_active('strength'):
            return False, {}
        
        current_price = self.per_sec_data[-1]['price']
        
        # RSI calculation
        rsi = self._calculate_rsi()
        
        # Trend strength
        recent_prices = [d['price'] for d in list(self.per_sec_data)[-20:]]
        trend_slope = self._compute_slope(np.array(recent_prices))
        trend_strength = abs(trend_slope) / current_price * 100 if current_price > 0 else 0
        
        # Momentum confirmation
        price_momentum = self._check_price_momentum(list(self.per_sec_data)[-20:])
        
        # Strength conditions
        rsi_oversold = rsi < 30
        rsi_overbought = rsi > 70
        strong_trend = trend_strength > 0.1
        momentum_confirmation = abs(price_momentum) > 0.002
        
        # Determine signal based on STOCK STRENGTH
        signal_active = False
        direction = 'neutral'
        confidence = 0
        
        if rsi_oversold and strong_trend and momentum_confirmation and price_momentum > 0:
            signal_active = True
            direction = 'call'
            confidence = min(0.9, (30 - rsi) / 30 * 0.5 + trend_strength * 2)
        elif rsi_overbought and strong_trend and momentum_confirmation and price_momentum < 0:
            signal_active = True
            direction = 'put'
            confidence = min(0.9, (rsi - 70) / 30 * 0.5 + trend_strength * 2)
        
        signal_data = {
            'strategy': 'strength',
            'direction': direction,
            'current_price': current_price,
            'rsi': rsi,
            'trend_strength': trend_strength,
            'price_momentum': price_momentum,
            'rsi_oversold': rsi_oversold,
            'rsi_overbought': rsi_overbought,
            'confidence': confidence,
            'timestamp': time.time(),
            'time_et': get_et_time().strftime('%H:%M:%S')
        }
        
        if signal_active:
            self.last_signal_time['strength'] = time.time()
            logger.warning(f"💪 STRENGTH SIGNAL: IWM ${current_price:.2f}, "
                         f"RSI={rsi:.1f}, Trend={trend_strength:.3f}, "
                         f"Direction: {direction.upper()}, Confidence: {confidence:.2f}")
        
        return signal_active, signal_data
    
    
    def get_strategy_duration(self, strategy: str) -> int:
        """Get expected duration for strategy (in minutes)."""
        return self.strategy_durations.get(strategy, 30)
    
    def _is_cooldown_active(self, strategy: str) -> bool:
        """Check if strategy is in cooldown period."""
        if strategy not in self.last_signal_time:
            return False
        return (time.time() - self.last_signal_time[strategy]) < self.signal_cooldown
    
    def _calculate_vwap(self, data: List[Dict]) -> float:
        """Calculate volume-weighted average price."""
        if not data:
            return 0.0
        
        total_vol = sum(d['volume'] for d in data)
        if total_vol == 0:
            return sum(d['price'] for d in data) / len(data)
        
        weighted_sum = sum(d['price'] * d['volume'] for d in data)
        return weighted_sum / total_vol
    
    def _check_vwap_rising(self, data: List[Dict]) -> bool:
        """Check if VWAP has positive slope over period."""
        if len(data) < 10:
            return False
        
        vwaps = np.array([self._calculate_vwap(data[:i+1]) for i in range(len(data))], dtype=float)
        slope = self._compute_slope(vwaps)
        return slope > 0
    
    def _check_volume_surge(self, data: List[Dict]) -> Tuple[bool, float]:
        """Check if current volume is surging."""
        if len(data) < 60:
            return False, 0.0
        
        volumes = [d['volume'] for d in data]
        current_vol = volumes[-1]
        
        percentile_threshold = np.percentile(volumes[:-1], Config.SPOT_VOLUME_PERCENTILE)
        mean_vol = np.mean(volumes[:-1])
        std_vol = np.std(volumes[:-1])
        zscore = (current_vol - mean_vol) / std_vol if std_vol > 0 else 0
        
        return current_vol > percentile_threshold, zscore
    
    def _check_price_momentum(self, data: List[Dict]) -> float:
        """Calculate price momentum (rate of change)."""
        if len(data) < 2:
            return 0.0
        
        prices = np.array([d['price'] for d in data], dtype=float)
        slope = self._compute_slope(prices)
        avg_price = float(np.mean(prices))
        if avg_price > 0:
            return (slope / avg_price) * 100
        return 0.0
    
    def _update_rsi(self, current_price: float):
        """Update RSI calculation data."""
        self.rsi_data.append(current_price)
    
    def _calculate_rsi(self) -> float:
        """Calculate RSI indicator."""
        if len(self.rsi_data) < self.rsi_period:
            return 50.0
        
        prices = list(self.rsi_data)
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def _compute_slope(values: np.ndarray) -> float:
        """Compute slope of best-fit line for sequence using least squares."""
        if values.size < 2:
            return 0.0
        x = np.arange(values.size, dtype=float)
        x_mean = x.mean()
        y_mean = values.mean()
        denom = np.sum((x - x_mean) ** 2)
        if denom == 0:
            return 0.0
        slope = np.sum((x - x_mean) * (values - y_mean)) / denom
        return float(slope)


class CorrectedExitMonitor:
    """
    CORRECTED exit monitor that accounts for strategy duration differences.
    """
    
    def __init__(self):
        self.vwap_below_start: Optional[float] = None
        self.strategy_exits: Dict[str, Dict] = {}
        self.position_start_time: Optional[float] = None
        self.strategy_duration: int = 30  # Default 30 minutes
    
    def set_position_info(self, strategy: str, is_call: bool):
        """Set position information for proper exit timing."""
        self.position_start_time = time.time()
        self.strategy_duration = self._get_strategy_duration(strategy)
        logger.info(f"Position started: {strategy} {('call' if is_call else 'put')}, "
                   f"expected duration: {self.strategy_duration}min")
    
    def _get_strategy_duration(self, strategy: str) -> int:
        """Get expected duration for strategy."""
        durations = {
            'momentum': 15,  # 15 minutes average
            'gap': 30,       # 30 minutes average
            'volume': 20,    # 20 minutes average
            'strength': 45,  # 45 minutes average
            'combined': 30   # 30 minutes for combined strategies
        }
        return durations.get(strategy, 30)
    
    def should_exit(self, position_data: Dict, market_data: Dict, 
                   strategy: str = 'momentum') -> Tuple[bool, str]:
        """
        Check exit conditions with strategy-specific timing.
        """
        current_price = market_data.get('spot_price', 0)
        vwap = market_data.get('vwap_1min', 0)
        giveback = position_data.get('giveback_percent', 0)
        pnl = position_data.get('pnl_percent', 0)
        is_call = position_data.get('is_call', True)
        
        # Check if we've held long enough for this strategy
        if self.position_start_time:
            hold_time_minutes = (time.time() - self.position_start_time) / 60.0
            min_hold_time = self.strategy_duration * 0.3  # 30% of expected duration
            
            if hold_time_minutes < min_hold_time:
                # Too early to exit - only allow stop losses
                if pnl <= -15:  # Hard stop loss
                    return True, f"Hard stop loss hit ({pnl:.1f}%) - too early for normal exit"
                return False, ""
        
        # Strategy-specific exits
        if strategy == 'gap':
            return self._check_gap_exit(position_data, market_data, is_call)
        elif strategy == 'volume':
            return self._check_volume_exit(position_data, market_data, is_call)
        elif strategy == 'strength':
            return self._check_strength_exit(position_data, market_data, is_call)
        elif strategy == 'combined':
            return self._check_combined_exit(position_data, market_data, is_call)
        else:  # momentum and default
            return self._check_momentum_exit(position_data, market_data, is_call)
    
    def _check_momentum_exit(self, position_data: Dict, market_data: Dict, 
                            is_call: bool) -> Tuple[bool, str]:
        """Momentum strategy exit conditions."""
        current_price = market_data.get('spot_price', 0)
        vwap = market_data.get('vwap_1min', 0)
        giveback = position_data.get('giveback_percent', 0)
        pnl = position_data.get('pnl_percent', 0)
        
        # Hard giveback
        if giveback >= Config.MAX_GIVEBACK_PERCENT:
            return True, f"Hard giveback {giveback:.1f}%"
        
        # Adaptive giveback when below VWAP
        if current_price < vwap and giveback >= Config.TIGHTEN_GIVEBACK_PERCENT:
            return True, f"Below VWAP with {giveback:.1f}% giveback"
        
        # Extended time below VWAP
        now = time.time()
        required_duration = Config.VWAP_EXIT_BLOCKS * 30
        if current_price < vwap:
            if self.vwap_below_start is None:
                self.vwap_below_start = now
            else:
                elapsed = now - self.vwap_below_start
                if elapsed >= required_duration:
                    blocks = max(Config.VWAP_EXIT_BLOCKS, int(elapsed // 30))
                    return True, f"Extended time below VWAP ({blocks} blocks)"
        else:
            self.vwap_below_start = None
        
        # Stop loss
        if pnl <= -15:
            return True, f"Stop loss hit ({pnl:.1f}%)"
        
        # Time stop
        from utils import should_force_exit
        if should_force_exit():
            return True, f"Time stop {Config.HARD_TIME_STOP} ET"
        
        return False, ""
    
    def _check_gap_exit(self, position_data: Dict, market_data: Dict, 
                       is_call: bool) -> Tuple[bool, str]:
        """Gap strategy exit conditions."""
        pnl = position_data.get('pnl_percent', 0)
        duration_minutes = position_data.get('duration_minutes', 0)
        
        # Quick profit taking for gap plays
        if pnl >= 20:  # 20% profit target
            return True, f"Gap profit target hit ({pnl:.1f}%)"
        
        # Quick stop for gap plays
        if pnl <= -10:  # 10% stop loss
            return True, f"Gap stop loss hit ({pnl:.1f}%)"
        
        # Time-based exit for gap plays (shorter hold time)
        if duration_minutes >= 30:  # 30 minutes max hold
            return True, f"Gap time limit reached ({duration_minutes:.0f}min)"
        
        # Time stop
        from utils import should_force_exit
        if should_force_exit():
            return True, f"Time stop {Config.HARD_TIME_STOP} ET"
        
        return False, ""
    
    def _check_volume_exit(self, position_data: Dict, market_data: Dict, 
                          is_call: bool) -> Tuple[bool, str]:
        """Volume strategy exit conditions."""
        pnl = position_data.get('pnl_percent', 0)
        giveback = position_data.get('giveback_percent', 0)
        
        # Volume plays need tighter management
        if giveback >= 15:  # 15% giveback limit
            return True, f"Volume giveback limit hit ({giveback:.1f}%)"
        
        # Quick profit taking
        if pnl >= 25:  # 25% profit target
            return True, f"Volume profit target hit ({pnl:.1f}%)"
        
        # Stop loss
        if pnl <= -12:  # 12% stop loss
            return True, f"Volume stop loss hit ({pnl:.1f}%)"
        
        # Time stop
        from utils import should_force_exit
        if should_force_exit():
            return True, f"Time stop {Config.HARD_TIME_STOP} ET"
        
        return False, ""
    
    def _check_strength_exit(self, position_data: Dict, market_data: Dict, 
                            is_call: bool) -> Tuple[bool, str]:
        """Strength strategy exit conditions."""
        pnl = position_data.get('pnl_percent', 0)
        giveback = position_data.get('giveback_percent', 0)
        duration_minutes = position_data.get('duration_minutes', 0)
        
        # Strength plays can run longer
        if giveback >= 25:  # 25% giveback limit
            return True, f"Strength giveback limit hit ({giveback:.1f}%)"
        
        # Profit targets
        if pnl >= 30:  # 30% profit target
            return True, f"Strength profit target hit ({pnl:.1f}%)"
        
        # Stop loss
        if pnl <= -15:  # 15% stop loss
            return True, f"Strength stop loss hit ({pnl:.1f}%)"
        
        # Time stop
        from utils import should_force_exit
        if should_force_exit():
            return True, f"Time stop {Config.HARD_TIME_STOP} ET"
        
        return False, ""
    
    def _check_combined_exit(self, position_data: Dict, market_data: Dict, 
                            is_call: bool) -> Tuple[bool, str]:
        """Combined strategy exit conditions."""
        pnl = position_data.get('pnl_percent', 0)
        giveback = position_data.get('giveback_percent', 0)
        
        # Combined strategies use moderate settings
        if giveback >= 20:  # 20% giveback limit
            return True, f"Combined giveback limit hit ({giveback:.1f}%)"
        
        # Profit targets
        if pnl >= 25:  # 25% profit target
            return True, f"Combined profit target hit ({pnl:.1f}%)"
        
        # Stop loss
        if pnl <= -15:  # 15% stop loss
            return True, f"Combined stop loss hit ({pnl:.1f}%)"
        
        # Time stop
        from utils import should_force_exit
        if should_force_exit():
            return True, f"Time stop {Config.HARD_TIME_STOP} ET"
        
        return False, ""