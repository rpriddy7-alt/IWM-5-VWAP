#!/usr/bin/env python3
"""
Test script for Miyagi Multi-Symbol Multi-Strategy System
Tests the configuration and initialization of multiple symbols.
"""
import sys
import os
from datetime import datetime
from logger import setup_logger
from config import Config
from multi_strategy_orchestrator import MultiStrategyOrchestrator

logger = setup_logger("TestMultiSymbol")


def test_configuration():
    """Test multi-symbol configuration."""
    logger.info("Testing Multi-Symbol Configuration...")
    
    # Test configuration loading
    logger.info(f"Overnight Bias Symbols: {Config.OVERNIGHT_BIAS_SYMBOLS}")
    logger.info(f"VWAP Strategy Symbols: {Config.VWAP_STRATEGY_SYMBOLS}")
    logger.info(f"Enable VWAP Strategy: {Config.ENABLE_VWAP_STRATEGY}")
    logger.info(f"Enable Overnight Bias Strategy: {Config.ENABLE_OVERNIGHT_BIAS_STRATEGY}")
    
    # Validate configuration
    if not Config.OVERNIGHT_BIAS_SYMBOLS:
        logger.error("✗ No Overnight Bias symbols configured")
        return False
    
    if not Config.VWAP_STRATEGY_SYMBOLS:
        logger.error("✗ No VWAP Strategy symbols configured")
        return False
    
    logger.info("✓ Multi-symbol configuration valid")
    return True


def test_orchestrator_initialization():
    """Test multi-strategy orchestrator initialization."""
    logger.info("Testing Multi-Strategy Orchestrator Initialization...")
    
    try:
        # Initialize orchestrator
        orchestrator = MultiStrategyOrchestrator()
        
        # Check strategy instances
        logger.info(f"Overnight Bias Instances: {list(orchestrator.overnight_bias_instances.keys())}")
        logger.info(f"VWAP Instances: {list(orchestrator.vwap_instances.keys())}")
        
        # Check active strategies
        logger.info(f"Active Strategies: {orchestrator.active_strategies}")
        
        # Get status
        status = orchestrator.get_strategy_status()
        logger.info(f"Strategy Status: {status}")
        
        logger.info("✓ Multi-strategy orchestrator initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"✗ Orchestrator initialization failed: {e}")
        return False


def test_symbol_data_handling():
    """Test symbol-specific data handling."""
    logger.info("Testing Symbol-Specific Data Handling...")
    
    try:
        orchestrator = MultiStrategyOrchestrator()
        
        # Test data for each symbol
        test_symbols = ['IWM', 'SPY', 'QQQ']
        
        for symbol in test_symbols:
            data = orchestrator._get_current_market_data_for_symbol(symbol)
            logger.info(f"{symbol} Data: {data}")
            
            if not data or 'symbol' not in data:
                logger.error(f"✗ Invalid data for {symbol}")
                return False
        
        logger.info("✓ Symbol-specific data handling working")
        return True
        
    except Exception as e:
        logger.error(f"✗ Symbol data handling failed: {e}")
        return False


def test_strategy_instances():
    """Test strategy instances for each symbol."""
    logger.info("Testing Strategy Instances...")
    
    try:
        orchestrator = MultiStrategyOrchestrator()
        
        # Test Overnight Bias instances
        for symbol in orchestrator.overnight_bias_symbols:
            if symbol not in orchestrator.overnight_bias_instances:
                logger.error(f"✗ No Overnight Bias instance for {symbol}")
                return False
            
            strategy = orchestrator.overnight_bias_instances[symbol]
            status = strategy.get_strategy_status()
            logger.info(f"{symbol} Overnight Bias Status: {status['strategy_name']}")
        
        # Test VWAP instances
        for symbol in orchestrator.vwap_strategy_symbols:
            if symbol not in orchestrator.vwap_instances:
                logger.error(f"✗ No VWAP instance for {symbol}")
                return False
            
            vwap_components = orchestrator.vwap_instances[symbol]
            logger.info(f"{symbol} VWAP Components: {list(vwap_components.keys())}")
        
        logger.info("✓ Strategy instances working for all symbols")
        return True
        
    except Exception as e:
        logger.error(f"✗ Strategy instances test failed: {e}")
        return False


def test_overnight_analysis_simulation():
    """Test overnight analysis for multiple symbols."""
    logger.info("Testing Overnight Analysis Simulation...")
    
    try:
        orchestrator = MultiStrategyOrchestrator()
        
        # Simulate overnight analysis for each symbol
        for symbol in orchestrator.overnight_bias_symbols:
            logger.info(f"Simulating overnight analysis for {symbol}")
            
            # This would normally be called at 3:00 AM ET
            orchestrator._process_overnight_analysis_for_symbol(symbol)
        
        logger.info("✓ Overnight analysis simulation completed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Overnight analysis simulation failed: {e}")
        return False


def test_position_tracking():
    """Test position tracking across multiple symbols."""
    logger.info("Testing Position Tracking...")
    
    try:
        orchestrator = MultiStrategyOrchestrator()
        
        # Simulate positions for different symbols
        test_positions = [
            {'strategy': 'overnight_bias', 'symbol': 'IWM', 'bias': 'calls'},
            {'strategy': 'overnight_bias', 'symbol': 'SPY', 'bias': 'puts'},
            {'strategy': 'vwap', 'symbol': 'IWM', 'bias': 'calls'}
        ]
        
        for i, position in enumerate(test_positions):
            position_id = i + 1
            orchestrator.active_positions[position_id] = position
            logger.info(f"Added position {position_id}: {position}")
        
        # Check position tracking
        logger.info(f"Total positions: {len(orchestrator.active_positions)}")
        
        # Get status
        status = orchestrator.get_strategy_status()
        logger.info(f"Active positions in status: {status['active_positions']}")
        
        logger.info("✓ Position tracking working across symbols")
        return True
        
    except Exception as e:
        logger.error(f"✗ Position tracking test failed: {e}")
        return False


def main():
    """Run all multi-symbol tests."""
    logger.info("Starting Miyagi Multi-Symbol Multi-Strategy Tests")
    logger.info("=" * 60)
    
    tests = [
        ("Configuration", test_configuration),
        ("Orchestrator Initialization", test_orchestrator_initialization),
        ("Symbol Data Handling", test_symbol_data_handling),
        ("Strategy Instances", test_strategy_instances),
        ("Overnight Analysis Simulation", test_overnight_analysis_simulation),
        ("Position Tracking", test_position_tracking),
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
    logger.info("\n" + "=" * 60)
    logger.info("MIYAGI MULTI-SYMBOL TEST SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All Miyagi multi-symbol tests passed! System is ready for multi-symbol trading.")
        return 0
    else:
        logger.error("❌ Some tests failed. Please review the configuration.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
