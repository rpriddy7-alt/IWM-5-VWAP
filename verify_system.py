#!/usr/bin/env python3
"""
Comprehensive System Verification Script
Verifies all components, symbols, and configurations are working correctly.
"""
import sys
import os
from datetime import datetime
from logger import setup_logger
from config import Config
from multi_strategy_orchestrator import MultiStrategyOrchestrator
from overnight_bias_strategy import OvernightBiasStrategy
from strategy_config import StrategyConfig

logger = setup_logger("SystemVerification")


def verify_configuration():
    """Verify all configuration settings."""
    logger.info("🔍 Verifying Configuration...")
    
    # Check symbol tiers
    logger.info(f"Tier 1 Symbols: {Config.OVERNIGHT_BIAS_SYMBOLS_TIER1}")
    logger.info(f"Tier 2 Symbols: {Config.OVERNIGHT_BIAS_SYMBOLS_TIER2}")
    logger.info(f"Tier 3 Symbols: {Config.OVERNIGHT_BIAS_SYMBOLS_TIER3}")
    
    # Check active symbols
    logger.info(f"Active Overnight Bias Symbols: {Config.OVERNIGHT_BIAS_SYMBOLS}")
    logger.info(f"Active VWAP Symbols: {Config.VWAP_STRATEGY_SYMBOLS}")
    
    # Check tier controls
    logger.info(f"Tier Risk Controls: {Config.TIER_RISK_CONTROLS}")
    
    # Verify no duplicate symbols
    all_symbols = []
    for tier_symbols in [Config.OVERNIGHT_BIAS_SYMBOLS_TIER1, 
                        Config.OVERNIGHT_BIAS_SYMBOLS_TIER2, 
                        Config.OVERNIGHT_BIAS_SYMBOLS_TIER3]:
        for symbol in tier_symbols:
            if symbol.strip() in all_symbols:
                logger.error(f"❌ Duplicate symbol found: {symbol}")
                return False
            all_symbols.append(symbol.strip())
    
    logger.info(f"✅ Total unique symbols: {len(all_symbols)}")
    logger.info("✅ Configuration verification passed")
    return True


def verify_symbol_tiers():
    """Verify symbol tier assignments."""
    logger.info("🔍 Verifying Symbol Tier Assignments...")
    
    orchestrator = MultiStrategyOrchestrator()
    
    # Check tier mappings
    logger.info("Symbol Tier Mappings:")
    for symbol, tier in orchestrator.symbol_tiers.items():
        logger.info(f"  {symbol}: {tier}")
    
    # Verify all active symbols have tier assignments
    for symbol in orchestrator.overnight_bias_symbols:
        if symbol not in orchestrator.symbol_tiers:
            logger.error(f"❌ Symbol {symbol} not found in tier mappings")
            return False
        tier = orchestrator.symbol_tiers[symbol]
        logger.info(f"✅ {symbol} assigned to {tier}")
    
    logger.info("✅ Symbol tier assignments verified")
    return True


def verify_strategy_instances():
    """Verify all strategy instances are properly initialized."""
    logger.info("🔍 Verifying Strategy Instances...")
    
    orchestrator = MultiStrategyOrchestrator()
    
    # Check Overnight Bias instances
    logger.info(f"Overnight Bias Instances: {list(orchestrator.overnight_bias_instances.keys())}")
    for symbol, strategy in orchestrator.overnight_bias_instances.items():
        tier = orchestrator.symbol_tiers.get(symbol, 'tier1')
        tier_controls = orchestrator.tier_risk_controls.get(tier, {})
        
        logger.info(f"  {symbol}: tier={tier}, controls={tier_controls}")
        
        # Verify tier controls are set
        if strategy.symbol_tier != tier:
            logger.error(f"❌ {symbol} tier mismatch: expected {tier}, got {strategy.symbol_tier}")
            return False
        
        if strategy.tier_controls != tier_controls:
            logger.error(f"❌ {symbol} tier controls mismatch")
            return False
    
    # Check VWAP instances
    logger.info(f"VWAP Instances: {list(orchestrator.vwap_instances.keys())}")
    for symbol, components in orchestrator.vwap_instances.items():
        logger.info(f"  {symbol}: {list(components.keys())}")
    
    logger.info("✅ Strategy instances verified")
    return True


def verify_symbol_data_handling():
    """Verify symbol-specific data handling."""
    logger.info("🔍 Verifying Symbol Data Handling...")
    
    orchestrator = MultiStrategyOrchestrator()
    
    # Test data for each active symbol
    test_symbols = orchestrator.overnight_bias_symbols + orchestrator.vwap_strategy_symbols
    unique_symbols = list(set(test_symbols))
    
    for symbol in unique_symbols:
        data = orchestrator._get_current_market_data_for_symbol(symbol)
        if not data or 'symbol' not in data:
            logger.error(f"❌ Invalid data for {symbol}")
            return False
        
        logger.info(f"✅ {symbol} data: {data}")
    
    logger.info("✅ Symbol data handling verified")
    return True


def verify_tier_controls():
    """Verify tier-specific controls are working."""
    logger.info("🔍 Verifying Tier Controls...")
    
    orchestrator = MultiStrategyOrchestrator()
    
    # Test tier controls for each symbol
    for symbol in orchestrator.overnight_bias_symbols:
        strategy = orchestrator.overnight_bias_instances[symbol]
        tier = orchestrator.symbol_tiers.get(symbol, 'tier1')
        expected_controls = orchestrator.tier_risk_controls.get(tier, {})
        
        logger.info(f"Testing {symbol} ({tier}):")
        logger.info(f"  Max Positions: {strategy.tier_controls.get('max_positions', 'N/A')}")
        logger.info(f"  Position Multiplier: {strategy.tier_controls.get('position_size_multiplier', 'N/A')}")
        logger.info(f"  Time Stop: {strategy.tier_controls.get('time_stop_minutes', 'N/A')} min")
        
        # Verify controls match expected
        if strategy.tier_controls != expected_controls:
            logger.error(f"❌ {symbol} controls mismatch")
            return False
    
    logger.info("✅ Tier controls verified")
    return True


def verify_position_sizing():
    """Verify tier-specific position sizing."""
    logger.info("🔍 Verifying Position Sizing...")
    
    orchestrator = MultiStrategyOrchestrator()
    
    # Test position sizing for each tier
    test_contracts = [
        {'price': 2.50, 'symbol': 'SPY'},
        {'price': 1.80, 'symbol': 'IWM'},
        {'price': 3.20, 'symbol': 'QQQ'}
    ]
    
    for contract in test_contracts:
        symbol = contract['symbol']
        if symbol in orchestrator.overnight_bias_instances:
            strategy = orchestrator.overnight_bias_instances[symbol]
            tier = orchestrator.symbol_tiers.get(symbol, 'tier1')
            tier_controls = orchestrator.tier_risk_controls.get(tier, {})
            
            # Calculate position size
            base_account = 7000.0
            tier_multiplier = tier_controls.get('position_size_multiplier', 1.0)
            adjusted_account = base_account * tier_multiplier
            
            position_size = strategy.calculate_position_size(contract['price'], adjusted_account)
            
            logger.info(f"{symbol} ({tier}):")
            logger.info(f"  Base Account: ${base_account}")
            logger.info(f"  Tier Multiplier: {tier_multiplier}")
            logger.info(f"  Adjusted Account: ${adjusted_account}")
            logger.info(f"  Position Size: {position_size}")
            
            if position_size['status'] != 'approved':
                logger.error(f"❌ {symbol} position sizing failed: {position_size['reason']}")
                return False
    
    logger.info("✅ Position sizing verified")
    return True


def verify_time_stops():
    """Verify tier-specific time stops."""
    logger.info("🔍 Verifying Time Stops...")
    
    orchestrator = MultiStrategyOrchestrator()
    
    # Test time stops for each tier
    for symbol in orchestrator.overnight_bias_symbols:
        strategy = orchestrator.overnight_bias_instances[symbol]
        tier = orchestrator.symbol_tiers.get(symbol, 'tier1')
        expected_time_stop = orchestrator.tier_risk_controls.get(tier, {}).get('time_stop_minutes', 45)
        
        actual_time_stop = strategy.tier_controls.get('time_stop_minutes', 45)
        
        logger.info(f"{symbol} ({tier}): Expected {expected_time_stop}min, Got {actual_time_stop}min")
        
        if actual_time_stop != expected_time_stop:
            logger.error(f"❌ {symbol} time stop mismatch")
            return False
    
    logger.info("✅ Time stops verified")
    return True


def verify_strategy_config():
    """Verify strategy configuration."""
    logger.info("🔍 Verifying Strategy Configuration...")
    
    # Check active strategies
    active_strategies = StrategyConfig.get_active_strategies()
    logger.info(f"Active Strategies: {active_strategies}")
    
    # Check configuration validation
    validation = StrategyConfig.validate_config()
    logger.info(f"Configuration Validation: {validation}")
    
    if not validation['valid']:
        logger.error(f"❌ Configuration validation failed: {validation['errors']}")
        return False
    
    logger.info("✅ Strategy configuration verified")
    return True


def verify_system_integration():
    """Verify complete system integration."""
    logger.info("🔍 Verifying System Integration...")
    
    orchestrator = MultiStrategyOrchestrator()
    
    # Check system status
    status = orchestrator.get_strategy_status()
    logger.info(f"System Status: {status}")
    
    # Verify all components are initialized
    if not orchestrator.overnight_bias_instances:
        logger.error("❌ No Overnight Bias instances found")
        return False
    
    if not orchestrator.vwap_instances:
        logger.error("❌ No VWAP instances found")
        return False
    
    # Verify symbol counts
    expected_overnight_bias = len(orchestrator.overnight_bias_symbols)
    actual_overnight_bias = len(orchestrator.overnight_bias_instances)
    
    if actual_overnight_bias != expected_overnight_bias:
        logger.error(f"❌ Overnight Bias instance count mismatch: expected {expected_overnight_bias}, got {actual_overnight_bias}")
        return False
    
    expected_vwap = len(orchestrator.vwap_strategy_symbols)
    actual_vwap = len(orchestrator.vwap_instances)
    
    if actual_vwap != expected_vwap:
        logger.error(f"❌ VWAP instance count mismatch: expected {expected_vwap}, got {actual_vwap}")
        return False
    
    logger.info("✅ System integration verified")
    return True


def main():
    """Run comprehensive system verification."""
    logger.info("🚀 Starting Comprehensive System Verification")
    logger.info("=" * 60)
    
    verification_tests = [
        ("Configuration", verify_configuration),
        ("Symbol Tiers", verify_symbol_tiers),
        ("Strategy Instances", verify_strategy_instances),
        ("Symbol Data Handling", verify_symbol_data_handling),
        ("Tier Controls", verify_tier_controls),
        ("Position Sizing", verify_position_sizing),
        ("Time Stops", verify_time_stops),
        ("Strategy Configuration", verify_strategy_config),
        ("System Integration", verify_system_integration),
    ]
    
    results = []
    
    for test_name, test_func in verification_tests:
        logger.info(f"\n🔍 Running {test_name}...")
        try:
            result = test_func()
            results.append((test_name, result))
            if result:
                logger.info(f"✅ {test_name} PASSED")
            else:
                logger.error(f"❌ {test_name} FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name} ERROR: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("COMPREHENSIVE SYSTEM VERIFICATION SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} verifications passed")
    
    if passed == total:
        logger.info("🎉 ALL VERIFICATIONS PASSED! System is fully operational.")
        return 0
    else:
        logger.error("❌ Some verifications failed. Please review the issues.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
