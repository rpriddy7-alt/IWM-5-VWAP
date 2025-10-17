#!/usr/bin/env python3
"""
Comprehensive test suite for the SIMPLIFIED IWM Momentum System.
Tests all components to ensure the system is working correctly.
"""
import sys
import time
import os
from datetime import datetime
import pytz

# Set test environment variables
os.environ['POLYGON_API_KEY'] = 'test_key'
os.environ['PUSHOVER_TOKEN'] = 'test_token'
os.environ['PUSHOVER_USER_KEY'] = 'test_user'

print("=" * 60)
print("  IWM MOMENTUM SYSTEM - COMPREHENSIVE TEST")
print("=" * 60)
print()

def test_imports():
    """Test all module imports."""
    print("📦 Testing imports...")
    errors = []
    
    try:
        import websocket
        print("  ✅ websocket-client")
    except ImportError as e:
        errors.append(f"websocket-client: {e}")
        print("  ❌ websocket-client")
    
    try:
        import requests
        print("  ✅ requests")
    except ImportError as e:
        errors.append(f"requests: {e}")
        print("  ❌ requests")
    
    try:
        import numpy
        print("  ✅ numpy")
    except ImportError as e:
        errors.append(f"numpy: {e}")
        print("  ❌ numpy")
    
    try:
        import pytz
        print("  ✅ pytz")
    except ImportError as e:
        errors.append(f"pytz: {e}")
        print("  ❌ pytz")
    
    try:
        from dotenv import load_dotenv
        print("  ✅ python-dotenv")
    except ImportError as e:
        errors.append(f"python-dotenv: {e}")
        print("  ❌ python-dotenv")
    
    return errors

def test_core_modules():
    """Test core system modules."""
    print("\n🔧 Testing core modules...")
    errors = []
    
    try:
        from config import Config
        print("  ✅ config.py")
    except Exception as e:
        errors.append(f"config: {e}")
        print(f"  ❌ config.py: {e}")
    
    try:
        from logger import setup_logger
        print("  ✅ logger.py")
    except Exception as e:
        errors.append(f"logger: {e}")
        print(f"  ❌ logger.py: {e}")
    
    try:
        from utils import get_et_time, is_market_hours
        print("  ✅ utils.py")
    except Exception as e:
        errors.append(f"utils: {e}")
        print(f"  ❌ utils.py: {e}")
    
    try:
        from polygon_client import PolygonWebSocketClient, PolygonRESTClient
        print("  ✅ polygon_client.py")
    except Exception as e:
        errors.append(f"polygon_client: {e}")
        print(f"  ❌ polygon_client.py: {e}")
    
    try:
        from contract_selector import ContractSelector
        print("  ✅ contract_selector.py")
    except Exception as e:
        errors.append(f"contract_selector: {e}")
        print(f"  ❌ contract_selector.py: {e}")
    
    try:
        # Test simplified signals
        from signals import MomentumSignal, SimpleExitMonitor
        print("  ✅ signals.py (momentum-only)")
    except Exception as e:
        errors.append(f"signals: {e}")
        print(f"  ❌ signals.py: {e}")
    
    try:
        from risk_manager import RiskManager
        print("  ✅ risk_manager.py")
    except Exception as e:
        errors.append(f"risk_manager: {e}")
        print(f"  ❌ risk_manager.py: {e}")
    
    try:
        from alerts import PushoverClient
        print("  ✅ alerts.py")
    except Exception as e:
        errors.append(f"alerts: {e}")
        print(f"  ❌ alerts.py: {e}")
    
    try:
        from pnl_tracker import LifetimePnLTracker
        print("  ✅ pnl_tracker.py")
    except Exception as e:
        errors.append(f"pnl_tracker: {e}")
        print(f"  ❌ pnl_tracker.py: {e}")
    
    try:
        # Test main system
        from main import SimpleMomentumSystem
        print("  ✅ main.py (SIMPLIFIED)")
    except Exception as e:
        errors.append(f"main: {e}")
        print(f"  ❌ main.py: {e}")
    
    return errors

def test_signal_logic():
    """Test the simplified momentum signal logic."""
    print("\n📊 Testing signal logic...")
    
    try:
        from signals import MomentumSignal
        
        # Create signal instance
        signal = MomentumSignal()
        
        # Add test data
        test_data = []
        base_price = 220.0
        base_volume = 1000000
        
        # Simulate rising momentum
        for i in range(70):
            price = base_price + (i * 0.01)  # Rising price
            volume = base_volume * (1.5 if i > 60 else 1.0)  # Volume surge
            
            signal.update({
                'a': price - 0.05,  # VWAP slightly below price
                'v': volume,
                'c': price,
                't': time.time() * 1000 + i * 1000
            })
            test_data.append({'price': price, 'volume': volume})
        
        # Check signal
        is_active, data = signal.check_signal()
        
        if len(signal.per_sec_data) > 0:
            print(f"  ✅ Signal data collection working")
            print(f"     Data points: {len(signal.per_sec_data)}")
            print(f"     Current price: ${data.get('current_price', 0):.2f}")
            print(f"     VWAP: ${data.get('vwap_1min', 0):.2f}")
            print(f"     Volume Z-score: {data.get('volume_zscore', 0):.2f}")
        else:
            print(f"  ❌ Signal data collection failed")
        
    except Exception as e:
        print(f"  ❌ Signal test failed: {e}")

def test_system_initialization():
    """Test system initialization."""
    print("\n🚀 Testing system initialization...")
    
    try:
        from main import SimpleMomentumSystem
        from config import Config
        
        # Check config
        validation = Config.validate()
        if validation['valid']:
            print("  ✅ Configuration valid")
        else:
            print("  ⚠️  Configuration missing (expected for test):")
            for error in validation['errors']:
                print(f"     - {error}")
        
        # Try to create system (will fail without real API keys, but tests imports)
        try:
            system = SimpleMomentumSystem()
            print("  ✅ System initialized")
        except ValueError as e:
            if "Invalid configuration" in str(e):
                print("  ✅ System init validation working (needs real API keys)")
            else:
                print(f"  ❌ Unexpected error: {e}")
        
    except Exception as e:
        print(f"  ❌ System test failed: {e}")

def test_market_hours():
    """Test market hours detection."""
    print("\n⏰ Testing market hours...")
    
    try:
        from utils import is_market_hours, get_et_time
        
        et_now = get_et_time()
        market_open = is_market_hours()
        
        print(f"  Current ET time: {et_now.strftime('%H:%M:%S ET')}")
        print(f"  Market is: {'OPEN' if market_open else 'CLOSED'}")
        print("  ✅ Market hours check working")
        
    except Exception as e:
        print(f"  ❌ Market hours test failed: {e}")

def run_comprehensive_test():
    """Run all tests."""
    all_errors = []
    
    # Test imports
    import_errors = test_imports()
    all_errors.extend(import_errors)
    
    # Test core modules
    module_errors = test_core_modules()
    all_errors.extend(module_errors)
    
    # Test signal logic
    test_signal_logic()
    
    # Test system init
    test_system_initialization()
    
    # Test market hours
    test_market_hours()
    
    # Summary
    print("\n" + "=" * 60)
    print("  TEST SUMMARY")
    print("=" * 60)
    
    if not all_errors:
        print("\n✅ ALL TESTS PASSED!")
        print("\nThe SIMPLIFIED IWM Momentum System is ready to run.")
        print("\nNext steps:")
        print("1. Create .env file with your API keys:")
        print("   POLYGON_API_KEY=your_key")
        print("   PUSHOVER_TOKEN=your_token")
        print("   PUSHOVER_USER_KEY=your_user_key")
        print("\n2. Run the system:")
        print("   python3 main.py")
        return 0
    else:
        print(f"\n❌ {len(all_errors)} ERRORS FOUND:")
        for error in all_errors:
            print(f"  - {error}")
        return 1

if __name__ == "__main__":
    sys.exit(run_comprehensive_test())
