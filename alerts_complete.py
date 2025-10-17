"""
IWM-5-VWAP Complete Alert System
Comprehensive alert system with overnight analysis, market day reports, and live trading alerts.
"""
import time
import requests
from typing import Dict, Optional, List
from datetime import datetime
from logger import setup_logger
from config import Config
from silent_tradier_executor import silent_executor

logger = setup_logger("IWM5VWAPCompleteAlerts")


class IWM5VWAPCompleteAlertClient:
    """Complete alert system for IWM-5-VWAP strategy with all required alert types."""
    
    def __init__(self):
        self.api_url = Config.PUSHOVER_API_URL
        self.token = Config.PUSHOVER_TOKEN
        self.user_key = Config.PUSHOVER_USER_KEY
        
        # Check if Pushover is configured
        self.is_configured = bool(self.token and self.user_key)
        if not self.is_configured:
            logger.warning("Pushover not configured - alerts will be logged only")
        
        # Alert numbering system
        self.alert_number = 1
        self.active_positions = {}  # Track active positions by number
        
        # Lifetime P&L tracking (for strategy alerts only - ROBINHOOD ACCOUNT)
        self.lifetime_stats = {
            'total_pnl': 0.0,
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'calls_pnl': 0.0,
            'calls_trades': 0,
            'calls_wins': 0,
            'calls_losses': 0,
            'puts_pnl': 0.0,
            'puts_trades': 0,
            'puts_wins': 0,
            'puts_losses': 0
        }
        
        # Robinhood account balance (SEPARATE FROM TRADIER)
        self.robinhood_balance = 7100.0  # Your Robinhood settled cash
        self.available_robinhood_balance = 7100.0  # Current available for alerts
        
        # Separate tracking for SELL MAX alerts (against strategy)
        self.sell_max_stats = {
            'total_pnl': 0.0,
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'calls_pnl': 0.0,
            'calls_trades': 0,
            'calls_wins': 0,
            'calls_losses': 0,
            'puts_pnl': 0.0,
            'puts_trades': 0,
            'puts_wins': 0,
            'puts_losses': 0
        }
    
    def send_overnight_analysis_alert(self, analysis_data: Dict) -> bool:
        """
        Send overnight analysis alert at 3:00 AM ET after 12h candle completion.
        Shows if strategy will be active and what bias (CALLS/PUTS).
        """
        logger.info("🌙 OVERNIGHT ANALYSIS ALERT")
        
        # Extract analysis data
        bias = analysis_data.get('bias', 'unknown')
        confidence = analysis_data.get('confidence', 0.0)
        strategy_match = analysis_data.get('strategy_match', False)
        coil_pattern = analysis_data.get('coil_pattern', False)
        trigger_levels = analysis_data.get('trigger_levels', {})
        
        # Get lifetime stats
        total_pnl = self.lifetime_stats['total_pnl']
        total_trades = self.lifetime_stats['total_trades']
        wins = self.lifetime_stats['wins']
        losses = self.lifetime_stats['losses']
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        
        calls_pnl = self.lifetime_stats['calls_pnl']
        calls_trades = self.lifetime_stats['calls_trades']
        calls_wins = self.lifetime_stats['calls_wins']
        calls_losses = self.lifetime_stats['calls_losses']
        calls_win_rate = (calls_wins / calls_trades * 100) if calls_trades > 0 else 0
        
        puts_pnl = self.lifetime_stats['puts_pnl']
        puts_trades = self.lifetime_stats['puts_trades']
        puts_wins = self.lifetime_stats['puts_wins']
        puts_losses = self.lifetime_stats['puts_losses']
        puts_win_rate = (puts_wins / puts_trades * 100) if puts_trades > 0 else 0
        
        # Create title
        title = "🌙 IWM-5-VWAP OVERNIGHT ANALYSIS"
        
        # Determine strategy status
        if strategy_match and bias in ['calls', 'puts']:
            bias_text = f"**{bias.upper()}**" if bias == 'calls' else f"**{bias.upper()}**"
            strategy_status = f"STRATEGY ACTIVE - {bias_text} BIAS"
        else:
            strategy_status = "STRATEGY INACTIVE - No clear bias"
        
        # Create message
        message_lines = [
            f"**{strategy_status}**",
            "",
            f"📊 LIFETIME P&L: ${total_pnl:+.2f} | {wins}W/{losses}L ({win_rate:.1f}%)",
            "",
            f"📞 CALLS: ${calls_pnl:+.2f} | {calls_wins}W/{calls_losses}L ({calls_win_rate:.1f}%)",
            f"📉 PUTS: ${puts_pnl:+.2f} | {puts_wins}W/{puts_losses}L ({puts_win_rate:.1f}%)",
            "",
            f"🎯 Confidence: {confidence:.1f}% | Coil Pattern: {'✓' if coil_pattern else '✗'}",
            f"⏰ Analysis Time: {datetime.now().strftime('%H:%M ET')}"
        ]
        
        message = "\n".join(message_lines)
        
        return self._send_alert(title, message, priority=1, sound="cashregister")
    
    def send_market_day_review_alert(self, day_data: Dict) -> bool:
        """
        Send end-of-day review alert showing daily performance.
        """
        logger.info("📊 MARKET DAY REVIEW ALERT")
        
        # Extract day data
        day_bias = day_data.get('day_bias', 'unknown')
        day_pnl = day_data.get('day_pnl', 0.0)
        alerts_sent = day_data.get('alerts_sent', 0)
        day_wins = day_data.get('day_wins', 0)
        day_losses = day_data.get('day_losses', 0)
        day_win_rate = (day_wins / (day_wins + day_losses) * 100) if (day_wins + day_losses) > 0 else 0
        
        # Create title
        title = "📊 IWM-5-VWAP DAILY REVIEW"
        
        # Create message
        message_lines = [
            f"📅 MARKET DAY: {day_bias.upper()} BIAS",
            f"💰 DAILY P&L: ${day_pnl:+.2f}",
            f"📱 ALERTS SENT: {alerts_sent}",
            f"📊 DAILY RESULTS: {day_wins}W/{day_losses}L ({day_win_rate:.1f}%)",
            "",
            f"⏰ Market Close: {datetime.now().strftime('%H:%M ET')}"
        ]
        
        message = "\n".join(message_lines)
        
        return self._send_alert(title, message, priority=0, sound="pushover")
    
    def send_buy_alert(self, position_data: Dict, contract_data: Dict) -> bool:
        """
        Send BUY alert with clean design and critical information.
        """
        logger.info(f"🚨 BUY ALERT #{self.alert_number}")
        
        # Extract position data
        current_price = position_data.get('current_price', 0)
        vwap = position_data.get('vwap', 0)
        bias = position_data.get('bias', 'unknown')
        contract_type = contract_data.get('contract_type', 'call')
        
        # Extract contract data
        symbol = contract_data.get('symbol', 'N/A')
        strike = contract_data.get('strike', 0)
        price = contract_data.get('price', 0)
        quantity = contract_data.get('quantity', 0)
        profit_target = contract_data.get('profit_target', 0)
        
        # Create simplified contract name
        contract_name = f"IWM {strike:.0f}" if contract_type == 'call' else f"IWM {strike:.0f}"
        
        # Create title
        title = f"**BUY**"
        
        # Create message
        message_lines = [
            f"**IWM-5-VWAP {contract_type.upper()}**",
            f"Contract: {contract_name}",
            f"Price: ${price:.2f}",
            f"Quantity: {quantity}",
            f"Profit Target: ${profit_target:.2f}",
            f"**VWAP: ${vwap:.2f}**",
            "",
            f"Alert #{self.alert_number} | {datetime.now().strftime('%H:%M ET')}"
        ]
        
        message = "\n".join(message_lines)
        
        # Track active position
        self.active_positions[self.alert_number] = {
            'contract_name': contract_name,
            'contract_type': contract_type,
            'entry_price': price,
            'entry_time': datetime.now()
        }
        
        # Increment alert number
        self.alert_number += 1
        
        # Execute silent buy order (completely separate from alerts)
        try:
            silent_executor.execute_silent_buy({
                'symbol': 'IWM',
                'current_price': current_price,
                'strategy': 'IWM-5-VWAP',
                'confidence': position_data.get('confidence', 0.0),
                'bias': bias,
                'vwap': vwap
            })
        except Exception as e:
            logger.error(f"Silent buy execution failed: {e}")
        
        return self._send_alert(title, message, priority=1, sound="cashregister")
    
    def send_sell_alert(self, position_data: Dict, exit_data: Dict) -> bool:
        """
        Send SELL alert with position details and exit reason.
        May include SELL MAX info if trend is still favorable.
        """
        alert_num = exit_data.get('alert_number', self.alert_number - 1)
        logger.info(f"💰 SELL ALERT #{alert_num}")
        
        # Extract position data
        contract_name = position_data.get('contract_name', 'N/A')
        contract_type = position_data.get('contract_type', 'call')
        entry_price = position_data.get('entry_price', 0)
        entry_time = position_data.get('entry_time', datetime.now())
        
        # Extract exit data
        exit_price = exit_data.get('exit_price', 0)
        exit_reason = exit_data.get('exit_reason', 'Unknown')
        duration = exit_data.get('duration', 'Unknown')
        pnl = exit_data.get('pnl', 0)
        lifetime_pnl = exit_data.get('lifetime_pnl', 0)
        lifetime_wins = exit_data.get('lifetime_wins', 0)
        lifetime_losses = exit_data.get('lifetime_losses', 0)
        lifetime_win_rate = (lifetime_wins / (lifetime_wins + lifetime_losses) * 100) if (lifetime_wins + lifetime_losses) > 0 else 0
        
        # Check if SELL MAX info should be included
        trend_favorable = exit_data.get('trend_favorable', False)
        max_profit_reached = exit_data.get('max_profit_reached', False)
        trend_strength = exit_data.get('trend_strength', 'WEAK')
        risk_percentage = exit_data.get('risk_percentage', 0)
        
        # Create title
        title = f"**SELL**"
        
        # Create message
        message_lines = [
            f"**IWM-5-VWAP {contract_type.upper()}**",
            f"Contract: {contract_name}",
            f"Time Held: {duration}",
            f"P&L: ${pnl:+.2f} | Lifetime: ${lifetime_pnl:+.2f}",
            f"Lifetime Record: {lifetime_wins}W/{lifetime_losses}L ({lifetime_win_rate:.1f}%)",
            f"Exit Reason: {exit_reason}",
            "",
            f"Alert #{alert_num} | {datetime.now().strftime('%H:%M ET')}"
        ]
        
        # Add SELL MAX info ONLY if trend is still favorable and max profit reached
        if trend_favorable and max_profit_reached:
            message_lines.append("")
            message_lines.append("🔔 SELL MAX INFO:")
            message_lines.append(f"Trend: {trend_strength} | Risk: {risk_percentage:.1f}%")
            message_lines.append("⚠️ Consider holding for more profit")
        
        message = "\n".join(message_lines)
        
        # Execute silent sell order (completely separate from alerts)
        try:
            silent_executor.execute_silent_sell({
                'symbol': 'IWM',
                'current_price': exit_price,
                'strategy': 'IWM-5-VWAP',
                'exit_reason': exit_reason,
                'pnl': pnl
            })
        except Exception as e:
            logger.error(f"Silent sell execution failed: {e}")
        
        return self._send_alert(title, message, priority=1, sound="pushover")
    
    def check_robinhood_balance(self) -> Dict:
        """
        Check Robinhood account balance for alerts (SEPARATE FROM TRADIER).
        
        Returns:
            Dict with balance information
        """
        return {
            'robinhood_balance': self.robinhood_balance,
            'available_balance': self.available_robinhood_balance,
            'account_type': 'Robinhood',
            'separate_from_tradier': True
        }
    
    def update_robinhood_balance(self, trade_amount: float):
        """
        Update Robinhood balance after trade (SEPARATE FROM TRADIER).
        
        Args:
            trade_amount: Amount used in trade
        """
        self.available_robinhood_balance -= trade_amount
        logger.info(f"Robinhood balance updated: ${self.available_robinhood_balance:.2f} remaining (SEPARATE FROM TRADIER)")
    
    def reset_daily_robinhood_balance(self):
        """Reset Robinhood balance for new trading day (SEPARATE FROM TRADIER)."""
        self.available_robinhood_balance = self.robinhood_balance
        logger.info(f"Robinhood balance reset: ${self.robinhood_balance:.2f} available (SEPARATE FROM TRADIER)")
    
    def send_sell_max_alert(self, position_data: Dict, max_profit_data: Dict) -> bool:
        """
        Send SELL MAX alert - RARE alert only when strong movement detected.
        Simple and clear - time to sell if you didn't sell earlier.
        """
        alert_num = max_profit_data.get('alert_number', self.alert_number - 1)
        logger.info(f"💰 SELL MAX ALERT #{alert_num} - RARE ALERT")
        
        # Extract data
        contract_name = position_data.get('contract_name', 'N/A')
        contract_type = position_data.get('contract_type', 'call')
        current_profit = max_profit_data.get('current_profit', 0)
        trend_strength = max_profit_data.get('trend_strength', 'WEAK')
        
        # Create title
        title = f"💰 SELL MAX #{alert_num}"
        
        # Create simple, clear message
        message_lines = [
            f"**IWM-5-VWAP {contract_type.upper()}**",
            f"Contract: {contract_name}",
            f"Current Profit: ${current_profit:+.2f}",
            f"Trend: {trend_strength}",
            "",
            "🚨 DEFINITELY TIME TO SELL NOW",
            "⚠️ Strong movement detected - sell immediately",
            "",
            f"Alert #{alert_num} | {datetime.now().strftime('%H:%M ET')}"
        ]
        
        message = "\n".join(message_lines)
        
        return self._send_alert(title, message, priority=1, sound="cashregister")
    
    def _send_alert(self, title: str, message: str, priority: int = 0, sound: str = "pushover") -> bool:
        """
        Send alert via Pushover.
        """
        if not self.is_configured:
            logger.warning(f"Pushover not configured - would send: {title}")
            return False
        
        try:
            payload = {
                "token": self.token,
                "user": self.user_key,
                "title": title,
                "message": message,
                "priority": priority,
                "sound": sound
            }
            
            response = requests.post(self.api_url, json=payload, timeout=10)
            response.raise_for_status()
            
            logger.info(f"✅ Alert sent successfully: {title}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send alert: {e}")
            return False
