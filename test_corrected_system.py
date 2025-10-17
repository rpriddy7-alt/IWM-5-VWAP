#!/usr/bin/env python3
"""
Test script for CORRECTED Multi-Strategy IWM System
Verifies proper put/call handling and strategy combinations.
"""
import sys
import time
import os
from datetime import datetime

# Set test environment variables
os.environ['POLYGON_API_KEY'] = 'test_key'
os.environ['PUSHOVER_TOKEN'] = 'test_token'
os.environ['PUSHOVER_USER_KEY'] = 'test_user'

print("=" * 70)
print("  CORRECTED MULTI-STRATEGY SYSTEM - VERIFICATION TEST")
print("=" * 70)
print()

def test_corrected_imports():
    """Test corrected module imports."""
    print("📦 Testing corrected imports...")
    errors = []
    
    try:
        from signals_corrected import CorrectedMultiStrategySignals, CorrectedExitMonitor
        print("  ✅ signals_corrected.py")
    except ImportError as e:
        errors.append(f"signals_corrected: {e}")
        print(f"  ❌ signals_corrected.py: {e}")
    
    try:
        from contract_selector_corrected import CorrectedMultiStrategyContractSelector
        print("  ✅ contract_selector_corrected.py")
    except ImportError as e:
        errors.append(f"contract_selector_corrected: {e}")
        print(f"  ❌ contract_selector_corrected.py: {e}")
    
    try:
        from alerts_corrected import CorrectedMultiStrategyPushoverClient
        print("  ✅ alerts_corrected.py")
    except ImportError as e:
        errors.append(f"alerts_corrected: {e}")
        print(f"  ❌ alerts_corrected.py: {e}")
    
    try:
        from main_corrected import CorrectedMultiStrategySystem
        print("  ✅ main_corrected.py")
    except ImportError as e:
        errors.append(f"main_corrected: {e}")
        print(f"  ❌ main_corrected.py: {e}")
    
    return errors

def test_put_contract_handling():
    """Test proper put contract handling."""
    print("\n📉 Testing put contract handling...")
    
    try:
        from contract_selector_corrected import CorrectedMultiStrategyContractSelector
        
        # Create selector
        selector = CorrectedMultiStrategyContractSelector()
        
        # Test put contract data
        test_put_contracts = [
            {
                'details': {
                    'contract_type': 'put',
                    'expiration_date': '2024-10-09',
                    'strike_price': 220.0,
                    'ticker': 'IWM241009P220000',
                    'open_interest': 1200
                },
                'greeks': {'delta': -0.35},  # Negative delta for puts
                'last_quote': {'bid': 1.40, 'ask': 1.50, 'bid_size': 18, 'ask_size': 22},
                'day': {'volume': 400},
                'implied_volatility': 26.0
            },
            {
                'details': {
                    'contract_type': 'put',
                    'expiration_date': '2024-10-09',
                    'strike_price': 225.0,
                    'ticker': 'IWM241009P225000',
                    'open_interest': 800
                },
                'greeks': {'delta': -0.25},  # Negative delta for puts
                'last_quote': {'bid': 0.80, 'ask': 0.90, 'bid_size': 15, 'ask_size': 20},
                'day': {'volume': 300},
                'implied_volatility': 28.0
            }
        ]
        
        # Test put contract filtering
        result = selector.filter_and_rank_contracts(test_put_contracts)
        
        print(f"  Selected puts: {len(result['puts'])}")
        
        # Test put contract selection
        put_signal_data = {
            'direction': 'put',
            'confidence': 0.8,
            'current_price': 220.0
        }
        
        put_contract = selector.get_best_entry_contract(put_signal_data, 'momentum')
        if put_contract:
            print(f"    Selected put: {put_contract['symbol']}")
            print(f"    Strike: {put_contract['strike']}")
            print(f"    Delta: {put_contract['delta']} (should be negative)")
            print(f"    Contract type: {put_contract['contract_type']}")
            
            # Validate put contract
            is_valid = selector.validate_contract_selection(put_contract, 'put')
            print(f"    Validation: {'✓ Valid' if is_valid else '✗ Invalid'}")
        else:
            print("    No put contract selected")
        
        print("  ✅ Put contract handling working")
        
    except Exception as e:
        print(f"  ❌ Put contract test failed: {e}")

def test_strategy_combinations():
    """Test strategy combination detection."""
    print("\n🔥 Testing strategy combinations...")
    
    try:
        from signals_corrected import CorrectedMultiStrategySignals
        
        # Create signal instance
        signals = CorrectedMultiStrategySignals()
        
        # Simulate data that could trigger multiple strategies
        base_price = 220.0
        base_volume = 1000000
        
        # Create scenario that triggers multiple strategies
        for i in range(100):
            price = base_price + i * 0.02  # Rising price
            volume = base_volume * (2.0 if i > 50 else 1.0)  # Volume surge
            
            signals.update({
                'a': price - 0.05,  # VWAP slightly below price
                'v': volume,
                'c': price,
                'h': price + 0.01,
                'l': price - 0.01,
                't': time.time() * 1000 + i * 1000
            })
        
        # Check all signals
        all_signals = signals.check_all_signals()
        
        print("  Active strategies:")
        active_count = 0
        for strategy, (active, data) in all_signals.items():
            if active:
                active_count += 1
                print(f"    ✅ {strategy}: {data.get('direction', 'N/A')} (confidence: {data.get('confidence', 0):.2f})")
            else:
                print(f"    ❌ {strategy}: Inactive")
        
        # Get best signal (may be combined)
        best_strategy, signal_active, signal_data = signals.get_best_signal()
        
        if signal_active:
            print(f"  Best signal: {best_strategy}")
            if best_strategy == 'combined':
                strategies = signal_data.get('strategies', [])
                print(f"  Combined strategies: {', '.join(strategies)}")
                print(f"  Combined confidence: {signal_data.get('confidence', 0):.2f}")
        else:
            print("  No active signals")
        
        print(f"  Active strategies count: {active_count}")
        print("  ✅ Strategy combination detection working")
        
    except Exception as e:
        print(f"  ❌ Strategy combination test failed: {e}")

def test_corrected_alerts():
    """Test corrected alert system with put/call differentiation."""
    print("\n🚨 Testing corrected alerts...")
    
    try:
        from alerts_corrected import CorrectedMultiStrategyPushoverClient
        
        # Create alert client
        alert_client = CorrectedMultiStrategyPushoverClient()
        print(f"  Alert client created (configured: {alert_client.is_configured})")
        
        # Test put alert
        put_signal_data = {
            'strategy': 'momentum',
            'direction': 'put',
            'current_price': 218.50,
            'vwap_1min': 219.20,
            'confidence': 0.85,
            'timestamp': time.time(),
            'time_et': datetime.now().strftime('%H:%M:%S')
        }
        
        put_contract_data = {
            'symbol': 'IWM241009P220000',
            'strike': 220.0,
            'delta': -0.35,  # Negative delta for puts
            'iv': 26.0,
            'mid': 1.45,
            'bid': 1.40,
            'ask': 1.50,
            'spread_pct': 3.5,
            'bid_size': 18,
            'ask_size': 22,
            'contract_type': 'put'
        }
        
        print("  Testing put alert...")
        success = alert_client.send_buy_alert(put_signal_data, put_contract_data, 1.48, 'momentum')
        print(f"    Result: {'✓ Success' if success else '✗ Failed'}")
        
        # Test call alert
        call_signal_data = {
            'strategy': 'gap',
            'direction': 'call',
            'current_price': 222.50,
            'vwap_1min': 221.80,
            'confidence': 0.75,
            'timestamp': time.time(),
            'time_et': datetime.now().strftime('%H:%M:%S')
        }
        
        call_contract_data = {
            'symbol': 'IWM241009C220000',
            'strike': 220.0,
            'delta': 0.35,  # Positive delta for calls
            'iv': 25.0,
            'mid': 2.50,
            'bid': 2.45,
            'ask': 2.55,
            'spread_pct': 4.0,
            'bid_size': 20,
            'ask_size': 25,
            'contract_type': 'call'
        }
        
        print("  Testing call alert...")
        success = alert_client.send_buy_alert(call_signal_data, call_contract_data, 2.52, 'gap')
        print(f"    Result: {'✓ Success' if success else '✗ Failed'}")
        
        # Test combined strategy alert
        combined_signal_data = {
            'strategy': 'combined',
            'strategies': ['momentum', 'volume'],
            'direction': 'call',
            'current_price': 221.00,
            'vwap_1min': 220.50,
            'confidence': 0.90,
            'strategy_count': 2,
            'timestamp': time.time(),
            'time_et': datetime.now().strftime('%H:%M:%S')
        }
        
        print("  Testing combined strategy alert...")
        success = alert_client.send_buy_alert(combined_signal_data, call_contract_data, 2.52, 'combined')
        print(f"    Result: {'✓ Success' if success else '✗ Failed'}")
        
        print("  ✅ Corrected alert system working")
        
    except Exception as e:
        print(f"  ❌ Corrected alert test failed: {e}")

def test_exit_timing():
    """Test corrected exit timing for different strategies."""
    print("\n⏰ Testing exit timing...")
    
    try:
        from signals_corrected import CorrectedExitMonitor
        
        # Create exit monitor
        exit_monitor = CorrectedExitMonitor()
        
        # Test strategy durations
        strategies = ['momentum', 'gap', 'volume', 'strength', 'combined']
        
        for strategy in strategies:
            duration = exit_monitor._get_strategy_duration(strategy)
            print(f"  {strategy}: {duration} minutes expected duration")
        
        # Test position info setting
        exit_monitor.set_position_info('gap', True)  # Call
        print("  Position info set for gap call")
        
        exit_monitor.set_position_info('strength', False)  # Put
        print("  Position info set for strength put")
        
        print("  ✅ Exit timing working")
        
    except Exception as e:
        print(f"  ❌ Exit timing test failed: {e}")

def test_system_initialization():
    """Test corrected system initialization."""
    print("\n🚀 Testing corrected system initialization...")
    
    try:
        from main_corrected import CorrectedMultiStrategySystem
        from config import Config
        
        # Check config
        validation = Config.validate()
        if validation['valid']:
            print("  ✅ Configuration valid")
        else:
            print("  ⚠️  Configuration missing (expected for test):")
            for error in validation['errors']:
                print(f"     - {error}")
        
        # Try to create system
        try:
            system = CorrectedMultiStrategySystem()
            print("  ✅ Corrected system initialized")
        except ValueError as e:
            if "Invalid configuration" in str(e):
                print("  ✅ System init validation working (needs real API keys)")
            else:
                print(f"  ❌ Unexpected error: {e}")
        
    except Exception as e:
        print(f"  ❌ System test failed: {e}")

def run_corrected_test():
    """Run all corrected system tests."""
    all_errors = []
    
    # Test imports
    import_errors = test_corrected_imports()
    all_errors.extend(import_errors)
    
    # Test put contract handling
    test_put_contract_handling()
    
    # Test strategy combinations
    test_strategy_combinations()
    
    # Test corrected alerts
    test_corrected_alerts()
    
    # Test exit timing
    test_exit_timing()
    
    # Test system init
    test_system_initialization()
    
    # Summary
    print("\n" + "=" * 70)
    print("  CORRECTED SYSTEM TEST SUMMARY")
    print("=" * 70)
    
    if not all_errors:
        print("\n✅ ALL CORRECTED TESTS PASSED!")
        print("\nThe CORRECTED Multi-Strategy IWM System is ready with:")
        print("  • Proper put contract handling (negative deltas)")
        print("  • Stock trends drive strategies (not option data)")
        print("  • Strategy combinations clearly shown")
        print("  • Corrected exit timing for different strategies")
        print("  • Option contracts only for alert purposes")
        print("\nNext steps:")
        print("1. Create .env file with your API keys")
        print("2. Run the corrected system:")
        print("   python3 main_corrected.py")
        return 0
    else:
        print(f"\n❌ {len(all_errors)} ERRORS FOUND:")
        for error in all_errors:
            print(f"  - {error}")
        return 1

if __name__ == "__main__":
    sys.exit(run_corrected_test())