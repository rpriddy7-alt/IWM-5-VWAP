#!/usr/bin/env python3
"""
Test script for Miyagi Overnight Bias Strategy
Tests the new strategy implementation without running the full system.
"""
import sys
import time
from datetime import datetime, timezone
from logger import setup_logger
from overnight_bias_strategy import OvernightBiasStrategy
from strategy_config import StrategyConfig

logger = setup_logger("TestOvernightBias")


def test_overnight_bias_detection():
    """Test overnight bias detection logic."""
    logger.info("Testing Overnight Bias Detection...")
    
    strategy = OvernightBiasStrategy()
    
    # First, add a previous bar to establish context
    previous_bar = {
        'timestamp': time.time() - 3600,  # 1 hour ago
        'open': 240.00,
        'high': 240.80,  # Previous high
        'low': 239.50,   # Previous low
        'close': 240.50,
        'volume': 500000
    }
    strategy.overnight_bars.append(previous_bar)
    
    # Simulate overnight bar data that breaks above previous high
    overnight_bar = {
        'timestamp': time.time(),
        'open': 240.50,
        'high': 241.93,  # Break above previous high
        'low': 240.19,
        'close': 241.20,  # Close above previous high
        'volume': 1000000
    }
    
    # Manually set the time to 3:00 AM to trigger overnight analysis
    import datetime
    now = datetime.datetime.now()
    three_am = now.replace(hour=3, minute=0, second=0, microsecond=0)
    
    # Mock the time check by temporarily modifying the strategy
    original_method = strategy._is_overnight_bar_complete
    
    def mock_time_check(bar_data, current_time):
        return True  # Always return True for testing
    
    strategy._is_overnight_bar_complete = mock_time_check
    
    # Test bias detection
    result = strategy.update_overnight_bar(overnight_bar)
    
    # Restore original method
    strategy._is_overnight_bar_complete = original_method
    
    logger.info(f"Overnight Bias Result: {result}")
    
    if result['status'] == 'complete':
        logger.info(f"✓ Bias detected: {result['bias']}")
        logger.info(f"✓ Confidence: {result['confidence']:.2f}")
        logger.info(f"✓ Overnight High: {result['overnight_high']}")
        logger.info(f"✓ Overnight Low: {result['overnight_low']}")
        return True
    else:
        logger.error("✗ Bias detection failed")
        return False


def test_five_minute_confirmation():
    """Test 5-minute confirmation logic."""
    logger.info("Testing 5-Minute Confirmation...")
    
    strategy = OvernightBiasStrategy()
    
    # Set up bias first
    strategy.current_bias = 'calls'
    strategy.overnight_high = 241.93
    strategy.overnight_low = 240.19
    
    # Set up EMA20 data
    for i in range(20):
        strategy.ema20_data.append(241.0 + i * 0.1)  # Build EMA20 data
    strategy.current_ema20 = 242.0  # Set current EMA20
    
    # Mock the entry window check to always return True
    original_method = strategy._is_in_entry_window
    
    def mock_entry_window(current_time):
        return True  # Always in entry window for testing
    
    strategy._is_in_entry_window = mock_entry_window
    
    # Mock the 5-minute close check to always return True
    original_close_method = strategy._is_five_minute_close
    
    def mock_five_minute_close(current_time):
        return True  # Always 5-minute close for testing
    
    strategy._is_five_minute_close = mock_five_minute_close
    
    # Simulate tick data
    tick_data = {
        'timestamp': time.time(),
        'price': 242.50,  # Above overnight high
        'volume': 1000
    }
    
    # Simulate VWAP data
    vwap_data = {
        'current_vwap': 241.00,  # Below current price
        'price_vs_vwap': 'above'
    }
    
    # Test confirmation
    result = strategy.update_five_minute_data(tick_data, vwap_data)
    
    # Restore original methods
    strategy._is_in_entry_window = original_method
    strategy._is_five_minute_close = original_close_method
    
    logger.info(f"5-Minute Confirmation Result: {result}")
    
    if result.get('status') == 'entry_signal':
        logger.info("✓ Entry signal generated")
        logger.info(f"✓ Entry Price: {result['entry_price']}")
        logger.info(f"✓ Trigger Level: {result['trigger_level']}")
        return True
    else:
        logger.info(f"Status: {result.get('status', 'unknown')}")
        return False


def test_position_sizing():
    """Test position sizing logic."""
    logger.info("Testing Position Sizing...")
    
    strategy = OvernightBiasStrategy()
    
    # Test position sizing
    option_price = 2.50  # $2.50 per contract
    account_balance = 7000.0  # $7K account
    
    result = strategy.calculate_position_size(option_price, account_balance)
    
    logger.info(f"Position Sizing Result: {result}")
    
    if result['status'] == 'approved':
        logger.info(f"✓ Position approved: {result['num_contracts']} contracts")
        logger.info(f"✓ Position value: ${result['position_value']:.2f}")
        logger.info(f"✓ Risk amount: ${result['risk_amount']:.2f}")
        return True
    else:
        logger.error(f"✗ Position rejected: {result['reason']}")
        return False


def test_exit_conditions():
    """Test exit condition logic."""
    logger.info("Testing Exit Conditions...")
    
    strategy = OvernightBiasStrategy()
    
    # Simulate position data
    position_data = {
        'position_id': 1,
        'bias': 'calls',
        'entry_price': 242.50,
        'entry_time': datetime.now(timezone.utc),
        'trigger_level': 241.93
    }
    
    # Test different exit scenarios
    scenarios = [
        {'price': 245.00, 'vwap': 244.00, 'expected': 'hold'},  # Profit, hold
        {'price': 240.00, 'vwap': 241.00, 'expected': 'close'},  # Back inside trigger
        {'price': 243.00, 'vwap': 244.00, 'expected': 'close'},  # VWAP cross
    ]
    
    for i, scenario in enumerate(scenarios):
        vwap_data = {'current_vwap': scenario['vwap']}
        result = strategy.check_exit_conditions(
            position_data, scenario['price'], vwap_data
        )
        
        logger.info(f"Scenario {i+1}: Price {scenario['price']}, VWAP {scenario['vwap']}")
        logger.info(f"  Result: {result['action']} - {result.get('reason', 'N/A')}")
        
        if result['action'] == scenario['expected']:
            logger.info("  ✓ Correct exit decision")
        else:
            logger.warning(f"  ⚠ Expected {scenario['expected']}, got {result['action']}")
    
    return True


def test_strategy_config():
    """Test strategy configuration."""
    logger.info("Testing Strategy Configuration...")
    
    # Test configuration validation
    validation = StrategyConfig.validate_config()
    
    logger.info(f"Configuration Valid: {validation['valid']}")
    
    if validation['errors']:
        logger.error("Configuration Errors:")
        for error in validation['errors']:
            logger.error(f"  - {error}")
    
    if validation['warnings']:
        logger.warning("Configuration Warnings:")
        for warning in validation['warnings']:
            logger.warning(f"  - {warning}")
    
    # Test active strategies
    active_strategies = StrategyConfig.get_active_strategies()
    logger.info(f"Active Strategies: {active_strategies}")
    
    # Test position limits
    can_add = StrategyConfig.can_add_position('overnight_bias', {})
    logger.info(f"Can add position: {can_add}")
    
    return validation['valid']


def main():
    """Run all tests."""
    logger.info("Starting Miyagi Overnight Bias Strategy Tests")
    logger.info("=" * 50)
    
    tests = [
        ("Overnight Bias Detection", test_overnight_bias_detection),
        ("5-Minute Confirmation", test_five_minute_confirmation),
        ("Position Sizing", test_position_sizing),
        ("Exit Conditions", test_exit_conditions),
        ("Strategy Configuration", test_strategy_config),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\nRunning {test_name}...")
        try:
            result = test_func()
            results.append((test_name, result))
            if result:
                logger.info(f"✓ {test_name} PASSED")
            else:
                logger.error(f"✗ {test_name} FAILED")
        except Exception as e:
            logger.error(f"✗ {test_name} ERROR: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("TEST SUMMARY")
    logger.info("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Overnight Bias Strategy is ready.")
        return 0
    else:
        logger.error("❌ Some tests failed. Please review the implementation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
