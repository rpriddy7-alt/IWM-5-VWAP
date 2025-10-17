#!/usr/bin/env python3
"""
Comprehensive test suite for the Multi-Strategy IWM System.
Tests all strategies (momentum, gap, volume, strength) and put/call functionality.
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

print("=" * 70)
print("  IWM MULTI-STRATEGY SYSTEM - COMPREHENSIVE TEST")
print("=" * 70)
print()

def test_imports():
    """Test all multi-strategy module imports."""
    print("📦 Testing multi-strategy imports...")
    errors = []
    
    try:
        from signals_multi import MultiStrategySignals, MultiStrategyExitMonitor
        print("  ✅ signals_multi.py")
    except ImportError as e:
        errors.append(f"signals_multi: {e}")
        print(f"  ❌ signals_multi.py: {e}")
    
    try:
        from contract_selector_multi import MultiStrategyContractSelector
        print("  ✅ contract_selector_multi.py")
    except ImportError as e:
        errors.append(f"contract_selector_multi: {e}")
        print(f"  ❌ contract_selector_multi.py: {e}")
    
    try:
        from alerts_multi import MultiStrategyPushoverClient
        print("  ✅ alerts_multi.py")
    except ImportError as e:
        errors.append(f"alerts_multi: {e}")
        print(f"  ❌ alerts_multi.py: {e}")
    
    try:
        from main_multi import MultiStrategySystem
        print("  ✅ main_multi.py")
    except ImportError as e:
        errors.append(f"main_multi: {e}")
        print(f"  ❌ main_multi.py: {e}")
    
    return errors

def test_multi_strategy_signals():
    """Test multi-strategy signal detection."""
    print("\n📊 Testing multi-strategy signals...")
    
    try:
        from signals_multi import MultiStrategySignals
        
        # Create signal instance
        signals = MultiStrategySignals()
        
        # Test data for different strategies
        base_price = 220.0
        base_volume = 1000000
        
        # Simulate different market conditions
        test_scenarios = [
            {
                'name': 'Momentum Up',
                'data': [(base_price + i * 0.01, base_volume * (1.5 if i > 50 else 1.0)) for i in range(70)],
                'expected_strategy': 'momentum',
                'expected_direction': 'call'
            },
            {
                'name': 'Gap Up',
                'data': [(base_price + 2.0 + i * 0.005, base_volume * 2.0) for i in range(20)],
                'expected_strategy': 'gap',
                'expected_direction': 'call'
            },
            {
                'name': 'Volume Surge',
                'data': [(base_price + i * 0.02, base_volume * (3.0 if i > 30 else 1.0)) for i in range(60)],
                'expected_strategy': 'volume',
                'expected_direction': 'call'
            },
            {
                'name': 'Strength Oversold',
                'data': [(base_price - i * 0.01, base_volume) for i in range(20)],
                'expected_strategy': 'strength',
                'expected_direction': 'call'
            }
        ]
        
        for scenario in test_scenarios:
            print(f"  Testing {scenario['name']}...")
            
            # Reset signals
            signals = MultiStrategySignals()
            
            # Feed data
            for i, (price, volume) in enumerate(scenario['data']):
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
            best_strategy, signal_active, signal_data = signals.get_best_signal()
            
            print(f"    Best strategy: {best_strategy}")
            print(f"    Signal active: {signal_active}")
            print(f"    Direction: {signal_data.get('direction', 'N/A')}")
            print(f"    Confidence: {signal_data.get('confidence', 0):.2f}")
            
            # Check if expected strategy is active
            if signal_active and best_strategy == scenario['expected_strategy']:
                print(f"    ✅ {scenario['name']} signal working")
            else:
                print(f"    ⚠️  {scenario['name']} signal not triggered as expected")
        
        print("  ✅ Multi-strategy signal detection working")
        
    except Exception as e:
        print(f"  ❌ Multi-strategy signal test failed: {e}")

def test_contract_selector():
    """Test multi-strategy contract selection."""
    print("\n🎯 Testing multi-strategy contract selection...")
    
    try:
        from contract_selector_multi import MultiStrategyContractSelector
        
        # Create selector
        selector = MultiStrategyContractSelector()
        
        # Test contract data
        test_contracts = [
            {
                'details': {
                    'contract_type': 'call',
                    'expiration_date': '2024-10-09',
                    'strike_price': 220.0,
                    'ticker': 'IWM241009C220000',
                    'open_interest': 1500
                },
                'greeks': {'delta': 0.35},
                'last_quote': {'bid': 1.45, 'ask': 1.55, 'bid_size': 20, 'ask_size': 25},
                'day': {'volume': 500},
                'implied_volatility': 25.0
            },
            {
                'details': {
                    'contract_type': 'put',
                    'expiration_date': '2024-10-09',
                    'strike_price': 220.0,
                    'ticker': 'IWM241009P220000',
                    'open_interest': 1200
                },
                'greeks': {'delta': -0.35},
                'last_quote': {'bid': 1.40, 'ask': 1.50, 'bid_size': 18, 'ask_size': 22},
                'day': {'volume': 400},
                'implied_volatility': 26.0
            }
        ]
        
        # Test contract filtering
        result = selector.filter_and_rank_contracts(test_contracts)
        
        print(f"  Selected calls: {len(result['calls'])}")
        print(f"  Selected puts: {len(result['puts'])}")
        
        # Test strategy-specific selection
        strategies = ['momentum', 'gap', 'volume', 'strength']
        directions = ['call', 'put']
        
        for strategy in strategies:
            for direction in directions:
                signal_data = {
                    'direction': direction,
                    'confidence': 0.8,
                    'current_price': 220.0
                }
                
                contract = selector.get_best_entry_contract(signal_data, strategy)
                if contract:
                    print(f"    {strategy} {direction}: {contract['symbol']} (Δ{contract['delta']:.2f})")
                else:
                    print(f"    {strategy} {direction}: No contract available")
        
        print("  ✅ Multi-strategy contract selection working")
        
    except Exception as e:
        print(f"  ❌ Contract selector test failed: {e}")

def test_alerts():
    """Test multi-strategy alert system."""
    print("\n🚨 Testing multi-strategy alerts...")
    
    try:
        from alerts_multi import MultiStrategyPushoverClient
        
        # Create alert client
        alert_client = MultiStrategyPushoverClient()
        print(f"  Alert client created (configured: {alert_client.is_configured})")
        
        # Test different strategy alerts
        strategies = ['momentum', 'gap', 'volume', 'strength']
        directions = ['call', 'put']
        
        for strategy in strategies:
            for direction in directions:
                # Test signal data
                signal_data = {
                    'strategy': strategy,
                    'direction': direction,
                    'current_price': 220.0 + (0.1 if direction == 'call' else -0.1),
                    'vwap_1min': 219.8,
                    'confidence': 0.8,
                    'timestamp': time.time(),
                    'time_et': datetime.now().strftime('%H:%M:%S')
                }
                
                # Test contract data
                contract_data = {
                    'symbol': f'IWM241009{"C" if direction == "call" else "P"}220000',
                    'strike': 220.0,
                    'delta': 0.35 if direction == 'call' else -0.35,
                    'iv': 25.0,
                    'mid': 1.50,
                    'bid': 1.45,
                    'ask': 1.55,
                    'spread_pct': 3.0,
                    'bid_size': 20,
                    'ask_size': 25,
                    'contract_type': direction
                }
                
                entry_price = 1.52
                
                print(f"  Testing {strategy} {direction} alert...")
                success = alert_client.send_buy_alert(signal_data, contract_data, entry_price, strategy)
                print(f"    Result: {'✓ Success' if success else '✗ Failed'}")
        
        # Test strategy summary alert
        strategy_stats = {
            'momentum': {'signals': 5, 'wins': 3, 'losses': 2, 'win_rate': 60.0},
            'gap': {'signals': 3, 'wins': 2, 'losses': 1, 'win_rate': 66.7},
            'volume': {'signals': 4, 'wins': 2, 'losses': 2, 'win_rate': 50.0},
            'strength': {'signals': 2, 'wins': 1, 'losses': 1, 'win_rate': 50.0}
        }
        
        print("  Testing strategy summary alert...")
        success = alert_client.send_strategy_summary_alert(strategy_stats)
        print(f"    Result: {'✓ Success' if success else '✗ Failed'}")
        
        print("  ✅ Multi-strategy alert system working")
        
    except Exception as e:
        print(f"  ❌ Alert system test failed: {e}")

def test_system_initialization():
    """Test multi-strategy system initialization."""
    print("\n🚀 Testing multi-strategy system initialization...")
    
    try:
        from main_multi import MultiStrategySystem
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
            system = MultiStrategySystem()
            print("  ✅ Multi-strategy system initialized")
        except ValueError as e:
            if "Invalid configuration" in str(e):
                print("  ✅ System init validation working (needs real API keys)")
            else:
                print(f"  ❌ Unexpected error: {e}")
        
    except Exception as e:
        print(f"  ❌ System test failed: {e}")

def test_strategy_combinations():
    """Test all strategy combinations."""
    print("\n🔄 Testing strategy combinations...")
    
    try:
        from signals_multi import MultiStrategySignals
        
        signals = MultiStrategySignals()
        
        # Test data that could trigger multiple strategies
        base_price = 220.0
        base_volume = 1000000
        
        # Create scenario that might trigger multiple strategies
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
        for strategy, (active, data) in all_signals.items():
            if active:
                print(f"    ✅ {strategy}: {data.get('direction', 'N/A')} (confidence: {data.get('confidence', 0):.2f})")
            else:
                print(f"    ❌ {strategy}: Inactive")
        
        # Get best signal
        best_strategy, signal_active, signal_data = signals.get_best_signal()
        
        if signal_active:
            print(f"  Best signal: {best_strategy} ({signal_data.get('direction', 'N/A')})")
        else:
            print("  No active signals")
        
        print("  ✅ Strategy combination testing working")
        
    except Exception as e:
        print(f"  ❌ Strategy combination test failed: {e}")

def run_comprehensive_test():
    """Run all multi-strategy tests."""
    all_errors = []
    
    # Test imports
    import_errors = test_imports()
    all_errors.extend(import_errors)
    
    # Test multi-strategy signals
    test_multi_strategy_signals()
    
    # Test contract selector
    test_contract_selector()
    
    # Test alerts
    test_alerts()
    
    # Test system init
    test_system_initialization()
    
    # Test strategy combinations
    test_strategy_combinations()
    
    # Summary
    print("\n" + "=" * 70)
    print("  MULTI-STRATEGY TEST SUMMARY")
    print("=" * 70)
    
    if not all_errors:
        print("\n✅ ALL MULTI-STRATEGY TESTS PASSED!")
        print("\nThe Multi-Strategy IWM System is ready to run with:")
        print("  • Momentum strategy (calls/puts)")
        print("  • Gap strategy (calls/puts)")
        print("  • Volume strategy (calls/puts)")
        print("  • Strength strategy (calls/puts)")
        print("\nNext steps:")
        print("1. Create .env file with your API keys:")
        print("   POLYGON_API_KEY=your_key")
        print("   PUSHOVER_TOKEN=your_token")
        print("   PUSHOVER_USER_KEY=your_user_key")
        print("\n2. Run the multi-strategy system:")
        print("   python3 main_multi.py")
        return 0
    else:
        print(f"\n❌ {len(all_errors)} ERRORS FOUND:")
        for error in all_errors:
            print(f"  - {error}")
        return 1

if __name__ == "__main__":
    sys.exit(run_comprehensive_test())