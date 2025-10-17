#!/usr/bin/env python3
"""
Quick diagnostic check for IWM Momentum System.
Run this to verify your setup and identify potential issues.
"""
import os
import sys
from datetime import datetime

def check_env_vars():
    """Check required environment variables."""
    print("\n📋 Checking Environment Variables...")
    print("-" * 50)
    
    required_vars = {
        'POLYGON_API_KEY': 'Polygon.io API key',
        'PUSHOVER_TOKEN': 'Pushover app token',
        'PUSHOVER_USER_KEY': 'Pushover user key'
    }
    
    all_present = True
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            masked = value[:8] + '...' if len(value) > 8 else '***'
            print(f"  ✅ {var}: {masked}")
        else:
            print(f"  ❌ {var}: MISSING ({description})")
            all_present = False
    
    return all_present

def check_imports():
    """Check required Python packages."""
    print("\n📦 Checking Python Packages...")
    print("-" * 50)
    
    packages = {
        'websocket': 'websocket-client',
        'requests': 'requests',
        'numpy': 'numpy',
        'pytz': 'pytz',
        'dotenv': 'python-dotenv'
    }
    
    all_present = True
    for module, package in packages.items():
        try:
            __import__(module)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} - Install with: pip install {package}")
            all_present = False
    
    return all_present

def check_modules():
    """Check that system modules can be imported."""
    print("\n🔧 Checking System Modules...")
    print("-" * 50)
    
    modules = [
        'config',
        'logger',
        'polygon_client',
        'contract_selector',
        'signals',
        'risk_manager',
        'alerts',
        'utils'
    ]
    
    all_present = True
    for module in modules:
        try:
            __import__(module)
            print(f"  ✅ {module}.py")
        except Exception as e:
            print(f"  ❌ {module}.py - Error: {e}")
            all_present = False
    
    return all_present

def check_config():
    """Check configuration settings."""
    print("\n⚙️  Checking Configuration...")
    print("-" * 50)
    
    try:
        from config import Config
        
        print(f"  Symbol: {Config.UNDERLYING_SYMBOL}")
        print(f"  Delta Range: {Config.DELTA_MIN} - {Config.DELTA_MAX}")
        print(f"  Entry Cutoff: {Config.NO_ENTRY_AFTER} ET")
        print(f"  Hard Time Stop: {Config.HARD_TIME_STOP} ET")
        print(f"  Max Giveback: {Config.MAX_GIVEBACK_PERCENT}%")
        
        validation = Config.validate()
        if validation['valid']:
            print("\n  ✅ Configuration valid")
            return True
        else:
            print("\n  ❌ Configuration errors:")
            for error in validation['errors']:
                print(f"    - {error}")
            return False
    except Exception as e:
        print(f"  ❌ Error loading config: {e}")
        return False

def check_market_hours():
    """Check if currently in market hours."""
    print("\n🕐 Checking Market Hours...")
    print("-" * 50)
    
    try:
        from utils import is_market_hours, can_enter_trade, get_et_time
        
        now_et = get_et_time()
        print(f"  Current time: {now_et.strftime('%Y-%m-%d %H:%M:%S ET')}")
        print(f"  Day of week: {now_et.strftime('%A')}")
        
        in_market_hours = is_market_hours()
        can_enter = can_enter_trade()
        
        print(f"  Market hours (9:30-16:00): {'✅ Yes' if in_market_hours else '❌ No'}")
        print(f"  Can enter trades: {'✅ Yes' if can_enter else '❌ No (after cutoff or outside hours)'}")
        
        return True
    except Exception as e:
        print(f"  ❌ Error checking market hours: {e}")
        return False

def main():
    """Run all diagnostic checks."""
    print("=" * 60)
    print("  IWM MOMENTUM SYSTEM - DIAGNOSTIC CHECK")
    print("=" * 60)
    
    # Run all checks
    checks = [
        ("Environment Variables", check_env_vars),
        ("Python Packages", check_imports),
        ("System Modules", check_modules),
        ("Configuration", check_config),
        ("Market Hours", check_market_hours)
    ]
    
    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"\n❌ Error in {name}: {e}")
            results[name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    
    all_passed = all(results.values())
    
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} - {name}")
    
    if all_passed:
        print("\n✅ All checks passed! System should be ready to run.")
        print("\nNext steps:")
        print("  1. Run: python main.py")
        print("  2. Monitor logs for diagnostic messages")
        print("  3. See DIAGNOSTIC_LOGGING.md for troubleshooting")
    else:
        print("\n❌ Some checks failed. Please fix the issues above.")
        print("\nFor help:")
        print("  - Check .env.example for required environment variables")
        print("  - Run: pip install -r requirements.txt")
        print("  - See README.md for setup instructions")
    
    print("\n" + "=" * 60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
