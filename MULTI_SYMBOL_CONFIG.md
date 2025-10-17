# Miyagi Multi-Symbol Tiered Configuration Guide

## Overview

The Miyagi trading system now supports a **tiered approach** to symbol selection for both the VWAP strategy and the new Overnight Bias strategy. This ensures optimal performance by matching risk controls to symbol characteristics and market conditions.

## Configuration

### Environment Variables

Set these environment variables to configure tiered multi-symbol support:

```bash
# Tier 1 Symbols (Best structure, clean flow, daily liquidity)
export OVERNIGHT_BIAS_SYMBOLS="SPY,IWM,QQQ"

# Tier 2 Symbols (Works well but needs tighter risk control)
export OVERNIGHT_BIAS_SYMBOLS_TIER2="META,AMD,NVDA,TSLA,AMZN"

# Tier 3 Symbols (Only in strong trend environments)
export OVERNIGHT_BIAS_SYMBOLS_TIER3="GOOGL,NFLX,BA,INTC,COIN,XLF,XLK,XLE"

# VWAP Strategy Symbols (Tier 1 only)
export VWAP_STRATEGY_SYMBOLS="SPY,IWM"

# Strategy Toggles
export ENABLE_VWAP_STRATEGY=true
export ENABLE_OVERNIGHT_BIAS_STRATEGY=true

# Position Limits
export MAX_TOTAL_POSITIONS=3
export MAX_DAILY_LOSS=-700.0
```

### Default Configuration

If no environment variables are set, the system defaults to:

- **Overnight Bias Strategy**: IWM, SPY, QQQ
- **VWAP Strategy**: IWM only
- **Both strategies enabled**

## Supported Symbols

### Overnight Bias Strategy
The Overnight Bias strategy works well with these symbols:

- **IWM** (iShares Russell 2000) - Primary, optimized for small-cap characteristics
- **SPY** (SPDR S&P 500) - Large-cap index, tighter ranges
- **QQQ** (Invesco QQQ) - Tech-heavy, more volatile

### VWAP Strategy
The VWAP strategy is currently optimized for:

- **IWM** - Primary symbol with established parameters

## Symbol Characteristics

### IWM (iShares Russell 2000)
- **Best for**: Overnight Bias strategy
- **Characteristics**: Balanced volatility, clean volume rhythm
- **Option pricing**: Forgiving for 0DTE trades
- **Volume**: Structured overnight ranges

### SPY (SPDR S&P 500)
- **Best for**: Overnight Bias strategy
- **Characteristics**: Tighter ranges, faster reactions
- **Option pricing**: More liquid, tighter spreads
- **Volume**: High institutional activity

### QQQ (Invesco QQQ)
- **Best for**: Overnight Bias strategy
- **Characteristics**: More volatile, tech-focused
- **Option pricing**: Higher volatility premiums
- **Volume**: Tech sector driven

## Configuration Examples

### Conservative Setup (IWM Only)
```bash
export OVERNIGHT_BIAS_SYMBOLS="IWM"
export VWAP_STRATEGY_SYMBOLS="IWM"
export MAX_TOTAL_POSITIONS=1
```

### Aggressive Multi-Symbol Setup
```bash
export OVERNIGHT_BIAS_SYMBOLS="IWM,SPY,QQQ"
export VWAP_STRATEGY_SYMBOLS="IWM"
export MAX_TOTAL_POSITIONS=3
```

### VWAP Only Setup
```bash
export ENABLE_OVERNIGHT_BIAS_STRATEGY=false
export ENABLE_VWAP_STRATEGY=true
export VWAP_STRATEGY_SYMBOLS="IWM"
```

### Overnight Bias Only Setup
```bash
export ENABLE_VWAP_STRATEGY=false
export ENABLE_OVERNIGHT_BIAS_STRATEGY=true
export OVERNIGHT_BIAS_SYMBOLS="IWM,SPY,QQQ"
```

## Position Management

### Per-Symbol Limits
- Each symbol can have its own strategy instance
- Position limits are enforced globally across all symbols
- Risk management applies to the total portfolio

### Risk Allocation
- **Conservative**: 1 position per symbol, max 2 total
- **Moderate**: 1 position per symbol, max 3 total  
- **Aggressive**: 2 positions per symbol, max 6 total

## Monitoring

### Strategy Status
The system provides detailed status for each symbol:

```python
# Get status for all symbols
status = orchestrator.get_strategy_status()

# Check specific symbol
iwm_status = status['overnight_bias_statuses']['IWM']
spy_status = status['overnight_bias_statuses']['SPY']
```

### Alerts
Alerts include symbol information:

- **Bias Alerts**: `"IWM Overnight Bias: CALLS (confidence: 0.85)"`
- **Entry Alerts**: `"SPY Overnight Bias Entry: 443C - 2 contracts"`
- **Exit Alerts**: `"QQQ Position Closed: PUTS - Reason: VWAP cross"`

## Performance Considerations

### Data Feeds
- Each symbol requires its own data subscription
- More symbols = more data bandwidth
- Polygon API limits apply per symbol

### Processing Load
- Each symbol runs its own strategy instance
- Overnight analysis runs for each symbol at 3:00 AM ET
- 5-minute confirmations process for each symbol

### Memory Usage
- Strategy instances per symbol
- Historical data storage per symbol
- Position tracking per symbol

## Best Practices

### Symbol Selection
1. **Start with IWM**: Most optimized for the strategies
2. **Add SPY**: Good complement with different characteristics
3. **Add QQQ**: Higher volatility, more opportunities

### Position Sizing
1. **Equal allocation**: Same position size per symbol
2. **Volatility adjustment**: Smaller sizes for more volatile symbols
3. **Correlation awareness**: Avoid highly correlated positions

### Risk Management
1. **Global limits**: Total portfolio risk across all symbols
2. **Symbol limits**: Individual symbol position limits
3. **Correlation limits**: Avoid over-concentration in similar assets

## Troubleshooting

### Common Issues

1. **No data for symbol**: Check Polygon API subscription
2. **Strategy not running**: Verify symbol in configuration
3. **Position rejected**: Check global position limits
4. **Alert not received**: Verify symbol in alert configuration

### Debug Commands

```bash
# Check configuration
python3 -c "from config import Config; print(Config.OVERNIGHT_BIAS_SYMBOLS)"

# Test strategy status
python3 -c "from multi_strategy_orchestrator import MultiStrategyOrchestrator; o = MultiStrategyOrchestrator(); print(o.get_strategy_status())"

# Run tests
python3 test_overnight_bias.py
```

## Advanced Configuration

### Custom Symbol Lists
```bash
# Add custom symbols
export OVERNIGHT_BIAS_SYMBOLS="IWM,SPY,QQQ,TQQQ,UPRO"

# Remove symbols
export OVERNIGHT_BIAS_SYMBOLS="IWM,SPY"
```

### Symbol-Specific Settings
```python
# In strategy_config.py, you can add symbol-specific settings
SYMBOL_SPECIFIC_SETTINGS = {
    'IWM': {'position_size_multiplier': 1.0},
    'SPY': {'position_size_multiplier': 0.8},
    'QQQ': {'position_size_multiplier': 0.6}
}
```

## Conclusion

The multi-symbol configuration allows you to diversify your trading across different ETFs while maintaining the same sophisticated strategy logic. Start with IWM and gradually add more symbols as you become comfortable with the system.

Remember to monitor your total portfolio risk and adjust position sizes based on symbol volatility and correlation.
