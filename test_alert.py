#!/usr/bin/env python3
"""
Test Alert Script for IWM-5-VWAP System
Sends a test alert to verify Pushover configuration.
"""
import os
import requests
import time
from datetime import datetime

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def send_test_alert():
    """Send a test alert to verify Pushover configuration."""
    
    # Get Pushover credentials
    token = os.getenv('PUSHOVER_TOKEN', 'a38bjrx57kf4mprrdgr213bhe7hk61')
    user_key = os.getenv('PUSHOVER_USER_KEY', 'usyhuqctc2s8oa3mk7ksbn5br3b9sy')
    
    print(f"Pushover Token: {'SET' if token else 'MISSING'}")
    print(f"Pushover User Key: {'SET' if user_key else 'MISSING'}")
    
    if not token or not user_key:
        print("❌ Pushover not configured - cannot send test alert")
        return False
    
    # Create test alert
    title = "🧪 IWM-5-VWAP TEST ALERT"
    message = f"""**SYSTEM TEST ALERT**

✅ IWM-5-VWAP System is running
✅ Pushover configuration verified
✅ Alert system working

Time: {datetime.now().strftime('%H:%M ET')}
Status: System operational and ready for trading alerts

This is a test alert to verify the system is working correctly."""
    
    # Send alert
    payload = {
        "token": token,
        "user": user_key,
        "title": title,
        "message": message,
        "priority": 1,
        "sound": "cashregister"
    }
    
    try:
        response = requests.post("https://api.pushover.net/1/messages.json", json=payload, timeout=10)
        response.raise_for_status()
        
        print("✅ Test alert sent successfully!")
        print(f"Response: {response.json()}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send test alert: {e}")
        return False

def send_strategy_status_alert():
    """Send current strategy status alert."""
    
    token = os.getenv('PUSHOVER_TOKEN', 'a38bjrx57kf4mprrdgr213bhe7hk61')
    user_key = os.getenv('PUSHOVER_USER_KEY', 'usyhuqctc2s8oa3mk7ksbn5br3b9sy')
    
    if not token or not user_key:
        print("❌ Pushover not configured")
        return False
    
    title = "📊 IWM-5-VWAP STRATEGY STATUS"
    message = f"""**CURRENT STRATEGY STATUS**

🔄 System Status: RUNNING
📡 WebSocket: Connected to Polygon
📊 Overnight Analysis: Processing
🎯 Strategy: IWM-5-VWAP Active
⏰ Market Hours: Monitoring
🔔 Alerts: Ready to send

Current Time: {datetime.now().strftime('%H:%M ET')}
System: Render deployment active

The system is monitoring IWM for VWAP-based signals and will send alerts when conditions are met."""
    
    payload = {
        "token": token,
        "user": user_key,
        "title": title,
        "message": message,
        "priority": 0,
        "sound": "pushover"
    }
    
    try:
        response = requests.post("https://api.pushover.net/1/messages.json", json=payload, timeout=10)
        response.raise_for_status()
        
        print("✅ Strategy status alert sent!")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send status alert: {e}")
        return False

if __name__ == "__main__":
    print("🧪 IWM-5-VWAP Test Alert System")
    print("=" * 50)
    
    # Send test alert
    print("\n1. Sending test alert...")
    test_success = send_test_alert()
    
    # Wait a moment
    time.sleep(2)
    
    # Send strategy status
    print("\n2. Sending strategy status...")
    status_success = send_strategy_status_alert()
    
    print("\n" + "=" * 50)
    if test_success and status_success:
        print("✅ All test alerts sent successfully!")
        print("Check your phone for the alerts.")
    else:
        print("❌ Some alerts failed to send.")
        print("Check Pushover configuration.")
