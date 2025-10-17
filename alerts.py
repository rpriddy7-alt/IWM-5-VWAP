"""
CORRECTED Multi-Strategy Alert System for IWM 0DTE System
Properly handles put contracts and shows strategy combinations.
"""
import time
import requests
from typing import Dict, Optional, List
from logger import setup_logger
from config import Config
from tradier_client import TradierTradingClient

logger = setup_logger("CorrectedAlerts")


class CorrectedMultiStrategyPushoverClient:
    """CORRECTED Pushover client with proper put/call handling and strategy combinations."""
    
    def __init__(self):
        self.api_url = Config.PUSHOVER_API_URL
        self.token = Config.PUSHOVER_TOKEN
        self.user_key = Config.PUSHOVER_USER_KEY
        
        # Check if Pushover is configured
        self.is_configured = bool(self.token and self.user_key)
        if not self.is_configured:
            logger.warning("Pushover not configured - alerts will be logged only")
        
        # Initialize Tradier trading client
        self.tradier_client = TradierTradingClient()
        
        # Track sent alerts to avoid duplicates
        self.sent_alerts = set()
        
        # Strategy-specific emojis and sounds
        self.strategy_emojis = {
            'momentum': '🚀',
            'gap': '📈',
            'volume': '📊',
            'strength': '💪',
            'combined': '🔥'
        }
        
        self.strategy_sounds = {
            'momentum': 'cashregister',
            'gap': 'pushover',
            'volume': 'cosmic',
            'strength': 'intermission',
            'combined': 'cashregister'
        }
    
    def send_buy_alert(self, signal_data: Dict, contract_data: Dict, 
                       entry_price: float, strategy: str = 'momentum', execute_trade: bool = True) -> bool:
        """
        Send BUY alert with CORRECTED put/call information and strategy combinations.
        """
        logger.warning(f"🚨 CORRECTED ALERT: send_buy_alert called!")
        logger.warning(f"🚨 CORRECTED ALERT: strategy={strategy}, signal_data keys: {list(signal_data.keys())}")
        logger.warning(f"🚨 CORRECTED ALERT: contract_data: {contract_data}")
        
        # Extract signal metrics (STOCK TREND DATA)
        current_price = signal_data.get('current_price', 0)
        vwap = signal_data.get('vwap_1min', 0)
        confidence = signal_data.get('confidence', 0)
        direction = signal_data.get('direction', 'call')
        
        # Contract details (OPTION CONTRACT FOR ALERT PURPOSES ONLY)
        symbol = contract_data.get('symbol', 'N/A')
        strike = contract_data.get('strike', 0)
        delta = contract_data.get('delta', 0)
        iv = contract_data.get('iv', 0)
        mid = contract_data.get('mid', 0)
        spread_pct = contract_data.get('spread_pct', 0)
        bid_size = contract_data.get('bid_size', 0)
        ask_size = contract_data.get('ask_size', 0)
        contract_type = contract_data.get('contract_type', 'call')
        
        from utils import get_todays_expiry
        expiry = get_todays_expiry()
        
        # Format offset
        offset = entry_price - mid
        
        # Check if blackout mode
        from time_filters import TimeAdaptiveFilters
        is_blackout = TimeAdaptiveFilters.is_blackout_period()
        mode_flag = " [BLACKOUT MODE]" if is_blackout else ""
        
        # Strategy-specific formatting
        strategy_emoji = self.strategy_emojis.get(strategy, '📈')
        strategy_name = strategy.upper()
        
        # CORRECTED Direction-specific formatting
        if direction == 'call':
            direction_emoji = '📞'
            direction_text = 'CALL'
            direction_explanation = 'BULLISH (IWM rising)'
        else:
            direction_emoji = '📉'
            direction_text = 'PUT'
            direction_explanation = 'BEARISH (IWM falling)'
        
        # CORRECTED Contract type validation
        if contract_type != direction:
            logger.error(f"CONTRACT TYPE MISMATCH: Signal direction={direction}, Contract type={contract_type}")
            # This should not happen with corrected contract selection
        
        # CORRECTED Put contract information
        if contract_type == 'put':
            # For puts, delta should be negative, strike should be above current price for OTM puts
            delta_display = f"Δ{delta:.2f}" if delta < 0 else f"Δ{abs(delta):.2f}"
            strike_analysis = f"Strike: {strike:.0f}c (OTM Put)" if strike > current_price else f"Strike: {strike:.0f}c (ITM Put)"
        else:
            # For calls, delta should be positive, strike should be below current price for OTM calls
            delta_display = f"Δ{delta:.2f}" if delta > 0 else f"Δ{abs(delta):.2f}"
            strike_analysis = f"Strike: {strike:.0f}c (OTM Call)" if strike < current_price else f"Strike: {strike:.0f}c (ITM Call)"
        
        # Construct message with CORRECTED layout
        vwap_line = "VWAP N/A" if vwap <= 0 else f"VWAP ${vwap:.2f}"
        
        # Show strategy combinations if applicable
        if strategy == 'combined':
            strategies = signal_data.get('strategies', [strategy])
            strategy_count = signal_data.get('strategy_count', 1)
            strategy_display = f"{strategy_name} ({strategy_count} strategies: {', '.join(strategies).upper()})"
        else:
            strategy_display = strategy_name
        
        title = f"{strategy_emoji} IWM 0DTE {direction_text} — {strategy_display} BUY{mode_flag}"
        
        message_lines = [
            f"📊 STOCK TREND: IWM ${current_price:.2f} | {vwap_line}",
            f"🎯 DIRECTION: {direction_explanation}",
            f"⚡ STRATEGY: {strategy_display} | Confidence: {confidence:.2f}",
            "",
            f"📋 CONTRACT INFO: {symbol} ({expiry})",
            f"Type: {contract_type.upper()} | {strike_analysis} | {delta_display}",
            f"IV: {iv:.1f}% | Entry: ~${entry_price:.2f} (mid ${mid:.2f} | +${offset:.2f})",
            f"Spread: {spread_pct:.1f}% | Size: {bid_size}×{ask_size}",
            "",
            f"⚠️ EXIT TIMING: Strategy-specific | Time {Config.HARD_TIME_STOP} ET"
        ]
        
        # Add strategy-specific information
        if strategy == 'momentum' or (strategy == 'combined' and 'momentum' in signal_data.get('strategies', [])):
            momentum = signal_data.get('momentum_momentum', signal_data.get('price_momentum', 0))
            vol_zscore = signal_data.get('momentum_vol_zscore', signal_data.get('volume_zscore', 0))
            message_lines.insert(3, f"🚀 Momentum: {momentum:+.3f}/s | Vol Z: {vol_zscore:.1f}")
        
        if strategy == 'gap' or (strategy == 'combined' and 'gap' in signal_data.get('strategies', [])):
            gap_percent = signal_data.get('gap_percent', 0)
            gap_vol_conf = signal_data.get('gap_volume_conf', signal_data.get('volume_confirmation', False))
            message_lines.insert(3, f"📈 Gap: {gap_percent:+.2f}% | Volume: {'✓' if gap_vol_conf else '✗'}")
        
        if strategy == 'volume' or (strategy == 'combined' and 'volume' in signal_data.get('strategies', [])):
            vol_zscore = signal_data.get('volume_zscore', 0)
            price_change = signal_data.get('volume_price_change', signal_data.get('price_change', 0))
            message_lines.insert(3, f"📊 Vol Z: {vol_zscore:.1f} | Price Δ: {price_change:+.2f}%")
        
        if strategy == 'strength' or (strategy == 'combined' and 'strength' in signal_data.get('strategies', [])):
            rsi = signal_data.get('strength_rsi', signal_data.get('rsi', 0))
            trend_strength = signal_data.get('strength_trend', signal_data.get('trend_strength', 0))
            message_lines.insert(3, f"💪 RSI: {rsi:.1f} | Trend: {trend_strength:.3f}")
        
        if is_blackout:
            message_lines.append("⚡ BLACKOUT MODE — High conviction window")
        
        message = "\n".join(message_lines)
        
        # Use strategy-specific sound
        sound = self.strategy_sounds.get(strategy, 'pushover')
        
        # Execute trade silently in background (no alert changes)
        if execute_trade and self.tradier_client.is_configured:
            try:
                logger.info(f"Executing trade for {strategy} signal")
                trade_result = self.tradier_client.execute_signal_trade(signal_data, strategy)
                if trade_result:
                    logger.info(f"Trade executed successfully: {trade_result.get('id', 'Unknown')}")
                else:
                    logger.warning("Trade execution failed")
            except Exception as e:
                logger.error(f"Error executing trade: {e}")
        
        return self._send_alert(title, message, priority=0, sound=sound)
    
    def send_sell_alert(self, position_summary: Dict, market_data: Dict, 
                       pnl_stats: Optional[Dict] = None, strategy: str = 'momentum') -> bool:
        """
        Send SELL alert with CORRECTED information.
        """
        contract = position_summary.get('contract', 'N/A')
        entry_price = position_summary.get('entry_price', 0)
        peak_mark = position_summary.get('peak_mark', 0)
        current_mark = position_summary.get('current_mark', 0)
        pnl_pct = position_summary.get('pnl_percent', 0)
        exit_reason = position_summary.get('exit_reason', 'Unknown')
        is_call = position_summary.get('is_call', True)
        duration_minutes = position_summary.get('duration_minutes', 0)
        
        iwm_price = market_data.get('spot_price', 0)
        vwap = market_data.get('vwap_1min', 0)
        
        # Format P&L color
        pnl_emoji = "🟢" if pnl_pct > 0 else "🔴" if pnl_pct < 0 else "⚪"
        
        # Strategy-specific formatting
        strategy_emoji = self.strategy_emojis.get(strategy, '📈')
        strategy_name = strategy.upper()
        
        # CORRECTED Direction-specific formatting
        direction_text = 'CALL' if is_call else 'PUT'
        direction_emoji = '📞' if is_call else '📉'
        
        title = f"{strategy_emoji} IWM 0DTE {direction_text} — {strategy_name} SELL"
        
        message_lines = [
            f"📊 STOCK TREND: IWM ${iwm_price:.2f} | VWAP ${vwap:.2f}",
            f"⚡ STRATEGY: {strategy_name} | Reason: {exit_reason}",
            f"⏱️ DURATION: {duration_minutes:.0f}min",
            "",
            f"📋 CONTRACT: {contract}",
            f"Peak ${peak_mark:.2f} → Now ${current_mark:.2f}",
            f"{pnl_emoji} P&L: {pnl_pct:+.1f}%"
        ]
        
        # Add strategy-specific exit information
        if strategy == 'gap':
            message_lines.insert(3, f"📈 Gap play exit (30min max)")
        elif strategy == 'volume':
            message_lines.insert(3, f"📊 Volume play exit (tight management)")
        elif strategy == 'strength':
            message_lines.insert(3, f"💪 Strength play exit (longer hold)")
        elif strategy == 'combined':
            message_lines.insert(3, f"🔥 Combined strategy exit")
        
        # Add lifetime P&L stats if provided
        if pnl_stats:
            lifetime_balance = pnl_stats['lifetime_balance']
            lifetime_emoji = "💰" if lifetime_balance >= 0 else "⚠️"
            
            message_lines.extend([
                "",
                f"{lifetime_emoji} Lifetime: ${lifetime_balance:+.2f}",
                f"📈 Record: {pnl_stats['wins']}W-{pnl_stats['losses']}L ({pnl_stats['win_rate']:.1f}%)"
            ])
        
        message_lines.extend(["", "✅ Close at market / best bid"])
        
        message = "\n".join(message_lines)
        
        return self._send_alert(title, message, priority=0, sound="intermission")
    
    def send_strategy_combination_alert(self, signal_data: Dict, contract_data: Dict, 
                                      entry_price: float) -> bool:
        """
        Send alert showing which strategies were combined.
        """
        strategies = signal_data.get('strategies', [])
        direction = signal_data.get('direction', 'call')
        confidence = signal_data.get('confidence', 0)
        current_price = signal_data.get('current_price', 0)
        
        strategy_emoji = '🔥'
        direction_text = 'CALL' if direction == 'call' else 'PUT'
        
        title = f"{strategy_emoji} STRATEGY COMBINATION — {direction_text}"
        
        message_lines = [
            f"📊 IWM ${current_price:.2f} | Combined Confidence: {confidence:.2f}",
            f"⚡ Active Strategies: {', '.join(strategies).upper()}",
            f"🎯 Direction: {direction_text}",
            "",
            f"📋 Contract: {contract_data.get('symbol', 'N/A')}",
            f"Entry: ~${entry_price:.2f}",
            "",
            "Multiple strategies aligned - high conviction signal!"
        ]
        
        message = "\n".join(message_lines)
        
        return self._send_alert(title, message, priority=0, sound="cashregister")
    
    def send_data_stall_alert(self, feed_type: str, duration: int) -> bool:
        """Send data stall warning."""
        title = "⚠️ DATA STALL WARNING"
        message = (
            f"{feed_type.upper()} feed silent for {duration}s\n"
            f"Multi-strategy signal generation paused until recovery"
        )
        
        return self._send_alert(title, message, priority=1)
    
    def send_system_alert(self, message: str, priority: int = 0) -> bool:
        """Send generic system alert."""
        title = "🤖 IWM Multi-Strategy System Alert"
        return self._send_alert(title, message, priority=priority)
    
    def send_strategy_summary_alert(self, strategy_stats: Dict) -> bool:
        """Send strategy performance summary."""
        title = "📊 Multi-Strategy Performance Summary"
        
        message_lines = ["Strategy Performance Today:", ""]
        
        for strategy, stats in strategy_stats.items():
            signals = stats.get('signals', 0)
            wins = stats.get('wins', 0)
            losses = stats.get('losses', 0)
            win_rate = stats.get('win_rate', 0)
            
            strategy_emoji = self.strategy_emojis.get(strategy, '📈')
            message_lines.append(f"{strategy_emoji} {strategy.upper()}: {signals} signals, {wins}W-{losses}L ({win_rate:.1f}%)")
        
        message = "\n".join(message_lines)
        
        return self._send_alert(title, message, priority=0)
    
    
    def _send_alert(self, title: str, message: str, priority: int = 0,
                    sound: Optional[str] = None) -> bool:
        """Internal method to send Pushover notification with retry logic."""
        # If Pushover not configured, just log the alert
        if not self.is_configured:
            logger.warning(f"CORRECTED ALERT (Pushover not configured): {title} - {message}")
            return True
        
        # Create idempotency key
        alert_hash = hash((title, message, int(time.time() / 60)))  # 1-min window
        
        if alert_hash in self.sent_alerts:
            logger.debug(f"Skipping duplicate corrected alert: {title}")
            return True
        
        payload = {
            'token': self.token,
            'user': self.user_key,
            'title': title,
            'message': message,
            'priority': priority
        }
        
        if sound:
            payload['sound'] = sound
        
        # Retry logic
        for attempt in range(Config.PUSHOVER_RETRY_ATTEMPTS):
            try:
                response = requests.post(
                    self.api_url,
                    data=payload,
                    timeout=3
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('status') == 1:
                        logger.info(f"✓ Corrected alert sent: {title}")
                        self.sent_alerts.add(alert_hash)
                        return True
                    else:
                        logger.error(f"Pushover API error: {result}")
                else:
                    logger.error(f"Pushover HTTP {response.status_code}: {response.text}")
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Pushover request failed (attempt {attempt + 1}): {e}")
            
            # Exponential backoff
            if attempt < Config.PUSHOVER_RETRY_ATTEMPTS - 1:
                wait_time = Config.PUSHOVER_RETRY_BACKOFF_BASE ** attempt
                time.sleep(wait_time)
        
        logger.error(f"Failed to send corrected alert after {Config.PUSHOVER_RETRY_ATTEMPTS} attempts")
        return False
    
    def check_and_close_positions(self, current_price: float) -> List[Dict]:
        """
        Check exit conditions and close positions if needed.
        Silent background operation - no alert changes.
        
        Args:
            current_price: Current IWM price
            
        Returns:
            List of closed positions with P&L data
        """
        if not self.tradier_client.is_configured:
            return []
        
        try:
            closed_positions = self.tradier_client.check_exit_conditions(current_price)
            
            # Log closed positions silently (no alert changes)
            for position in closed_positions:
                logger.info(f"Position closed: {position.get('symbol')} P&L: ${position.get('pnl', 0):.2f}")
            
            return closed_positions
            
        except Exception as e:
            logger.error(f"Error checking exit conditions: {e}")
            return []
    
    
    
    def send_alert(self, title: str, message: str, priority: int = 0, sound: str = None) -> bool:
        """Send alert using Pushover."""
        return self._send_alert(title, message, priority, sound)
    
    def clear_history(self):
        """Clear sent alert history (called daily)."""
        self.sent_alerts.clear()
        logger.debug("Corrected alert history cleared")