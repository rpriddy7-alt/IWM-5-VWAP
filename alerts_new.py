"""
IWM-5-VWAP Alert System
Specific alert system for the IWM-5-VWAP strategy with overnight analysis, VWAP control, and 5-minute confirmation.
"""
import time
import requests
from typing import Dict, Optional, List
from logger import setup_logger
from config import Config

logger = setup_logger("IWM5VWAPAlerts")


class IWM5VWAPAlertClient:
    """Alert client specifically for IWM-5-VWAP strategy."""
    
    def __init__(self):
        self.api_url = Config.PUSHOVER_API_URL
        self.token = Config.PUSHOVER_TOKEN
        self.user_key = Config.PUSHOVER_USER_KEY
        
        # Check if Pushover is configured
        self.is_configured = bool(self.token and self.user_key)
        if not self.is_configured:
            logger.warning("Pushover not configured - alerts will be logged only")
        
        # Track sent alerts to avoid duplicates
        self.sent_alerts = set()
    
    def send_entry_alert(self, position_data: Dict, contract_data: Dict) -> bool:
        """
        Send ENTRY alert for IWM-5-VWAP strategy.
        
        Args:
            position_data: Position information from strategy
            contract_data: Selected options contract details
        """
        logger.info("🚨 IWM-5-VWAP ENTRY ALERT")
        
        # Extract position data
        current_price = position_data.get('current_price', 0)
        vwap = position_data.get('vwap', 0)
        bias = position_data.get('bias', 'unknown')
        trigger_level = position_data.get('trigger_level', 0)
        entry_reason = position_data.get('entry_reason', 'Strategy trigger')
        
        # Extract contract data
        symbol = contract_data.get('symbol', 'N/A')
        strike = contract_data.get('strike', 0)
        delta = contract_data.get('delta', 0)
        iv = contract_data.get('iv', 0)
        price = contract_data.get('price', 0)
        contract_type = contract_data.get('contract_type', 'call')
        expiry = contract_data.get('expiry', 'Today')
        
        # Position sizing
        position_size = position_data.get('position_size', 0)
        max_risk = position_data.get('max_risk', 0)
        
        # Create alert title
        bias_emoji = "📞" if bias == 'calls' else "📉" if bias == 'puts' else "❓"
        title = f"{bias_emoji} IWM-5-VWAP {contract_type.upper()} ENTRY"
        
        # Create alert message
        message_lines = [
            f"🎯 STRATEGY: IWM-5-VWAP | Bias: {bias.upper()}",
            f"📊 STOCK: IWM ${current_price:.2f} | VWAP ${vwap:.2f}",
            f"⚡ TRIGGER: ${trigger_level:.2f} | Reason: {entry_reason}",
            "",
            f"📋 CONTRACT: {symbol}",
            f"Type: {contract_type.upper()} | Strike: ${strike:.0f} | Δ{delta:.2f}",
            f"Price: ${price:.2f} | IV: {iv:.1f}% | Expiry: {expiry}",
            "",
            f"💰 POSITION: ${position_size:.0f} | Max Risk: ${max_risk:.0f}",
            f"⏰ ENTRY TIME: {time.strftime('%H:%M:%S ET')}",
            "",
            "⚠️ EXIT: 35% profit target or 3:30 PM ET hard stop"
        ]
        
        message = "\n".join(message_lines)
        
        return self._send_alert(title, message, priority=0, sound="cashregister")
    
    def send_exit_alert(self, position_data: Dict, exit_data: Dict) -> bool:
        """
        Send EXIT alert for IWM-5-VWAP strategy.
        
        Args:
            position_data: Original position information
            exit_data: Exit information and P&L
        """
        logger.info("💰 IWM-5-VWAP EXIT ALERT")
        
        # Extract position data
        entry_price = position_data.get('entry_price', 0)
        entry_time = position_data.get('entry_time', 'Unknown')
        contract = position_data.get('contract', 'N/A')
        contract_type = position_data.get('contract_type', 'call')
        
        # Extract exit data
        exit_price = exit_data.get('exit_price', 0)
        exit_reason = exit_data.get('exit_reason', 'Unknown')
        duration = exit_data.get('duration', 'Unknown')
        pnl = exit_data.get('pnl', 0)
        pnl_percent = exit_data.get('pnl_percent', 0)
        lifetime_pnl = exit_data.get('lifetime_pnl', 0)
        
        # Create alert title
        pnl_emoji = "💰" if pnl >= 0 else "📉"
        title = f"{pnl_emoji} IWM-5-VWAP {contract_type.upper()} EXIT"
        
        # Create alert message
        message_lines = [
            f"📊 POSITION CLOSED: {contract}",
            f"💰 P&L: ${pnl:+.2f} ({pnl_percent:+.1f}%) | Entry: ${entry_price:.2f} → Exit: ${exit_price:.2f}",
            f"⏱️ Duration: {duration} | Entry: {entry_time}",
            f"🎯 Exit Reason: {exit_reason}",
            "",
            f"📈 LIFETIME P&L: ${lifetime_pnl:+.2f}",
            f"⏰ EXIT TIME: {time.strftime('%H:%M:%S ET')}",
            "",
            "✅ Position closed successfully"
        ]
        
        message = "\n".join(message_lines)
        
        return self._send_alert(title, message, priority=0, sound="pushover")
    
    def send_system_alert(self, alert_type: str, message: str, priority: int = 0) -> bool:
        """
        Send system alert (startup, error, etc.).
        
        Args:
            alert_type: Type of system alert
            message: Alert message
            priority: Alert priority (0-2)
        """
        logger.info(f"🔧 IWM-5-VWAP SYSTEM ALERT: {alert_type}")
        
        # System alert emojis
        system_emojis = {
            'startup': '🚀',
            'error': '❌',
            'warning': '⚠️',
            'info': 'ℹ️',
            'data_stall': '📡'
        }
        
        emoji = system_emojis.get(alert_type, '🔧')
        title = f"{emoji} IWM-5-VWAP {alert_type.upper()}"
        
        return self._send_alert(title, message, priority=priority, sound="pushover")
    
    def _send_alert(self, title: str, message: str, priority: int = 0, sound: str = "pushover") -> bool:
        """
        Send alert via Pushover.
        
        Args:
            title: Alert title
            message: Alert message
            priority: Alert priority (0-2)
            sound: Alert sound
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
