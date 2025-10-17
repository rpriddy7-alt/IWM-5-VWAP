# Overnight Bias / 0DTE Execution Strategy for Miyagi

## Overview

The Overnight Bias / 0DTE Execution Strategy is a sophisticated trading system designed specifically for Miyagi (iShares Russell 2000 ETF) that uses 12-hour overnight candles to set daily directional bias, then trades 0DTE options intraday based on 5-minute confirmation and structural filters.

## Core Concept

- **12-Hour Overnight Analysis**: Uses the 12-hour candle (3 AM ET close) to determine the day's directional bias
- **5-Minute Confirmation**: Executes trades based on 5-minute candle confirmation with VWAP + EMA20 filters
- **Precision Entries**: Rides institutional direction while avoiding market chop
- **Risk Management**: Implements comprehensive exit rules and position sizing

## Strategy Components

### 1. Overnight Bias Detection (`overnight_bias_strategy.py`)

**Purpose**: Analyzes 12-hour overnight bars to determine daily directional bias

**Key Features**:
- 12-hour candle analysis (15:00-03:00 ET)
- Bar type classification (1, 2-up, 2-down, 3)
- Bias determination based on breakouts
- Confidence scoring

**Bias Rules**:
- **2-up**: Closed above previous inside-bar high → Bullish (Calls only)
- **2-down**: Closed below previous inside-bar low → Bearish (Puts only)  
- **1**: Still inside bar → Neutral (Wait for breakout)

### 2. 5-Minute Confirmation System

**Purpose**: Confirms entry signals with 5-minute candle analysis

**Entry Logic**:
1. Day's bias is defined
2. Price is on your side of VWAP and EMA20
3. 5-minute candle closes beyond overnight high/low in bias direction

**Entry Windows**:
- Primary: 09:45-11:00 ET
- Secondary: 13:30-14:15 ET

### 3. Risk Management

**Position Sizing**:
- 1st entry: 1/3 of capital
- Add 1/3 on clean retest + VWAP hold
- Keep 1/3 reserve
- Per-trade risk: 1.5-3% of account

**Exit Rules**:
- Hard exit: Two consecutive 5-minute closes back inside trigger range or across VWAP
- Profit scales: +30-50% → partial, +70-100% → second scale
- Time stop: No new high/low within 45 minutes

## Integration with Existing System

### Multi-Strategy Orchestrator (`multi_strategy_orchestrator.py`)

The new strategy integrates seamlessly with the existing VWAP strategy through a multi-strategy orchestrator that:

- Runs both strategies simultaneously
- Manages position limits per strategy
- Coordinates data feeds and alerts
- Handles strategy-specific risk management

### Configuration (`strategy_config.py`)

Easy configuration and toggling of strategies:

```python
# Environment variables
ENABLE_VWAP_STRATEGY=true
ENABLE_OVERNIGHT_BIAS_STRATEGY=true
MAX_TOTAL_POSITIONS=2
MAX_DAILY_LOSS=-700.0
```

## File Structure

```
Miyagi-5-VWAP/
├── overnight_bias_strategy.py          # Main strategy implementation
├── multi_strategy_orchestrator.py      # Multi-strategy coordinator
├── strategy_config.py                  # Strategy configuration
├── test_overnight_bias.py              # Test suite
├── main.py                            # Updated to use multi-strategy
└── OVERNIGHT_BIAS_STRATEGY.md          # This documentation
```

## Key Features

### 1. 12-Hour Candle Analysis
- Captures overnight sentiment and institutional positioning
- Identifies breakout patterns and coil formations
- Sets precise trigger levels for intraday execution

### 2. VWAP + EMA20 Filters
- VWAP: Trend control and fairness line
- EMA20: Momentum filter and trend confirmation
- Both must align with bias for entry

### 3. 5-Minute Confirmation
- Waits for 5-minute candle close beyond trigger levels
- Confirms with VWAP and EMA20 alignment
- Reduces false signals and improves entry timing

### 4. Advanced Risk Management
- Position sizing based on account balance
- Profit scaling at 30% and 70% levels
- Time stops to prevent theta decay
- Hard exits on VWAP crosses

## Usage

### Running the System

```bash
# Start the multi-strategy system
python3 main.py

# Run tests
python3 test_overnight_bias.py

# Check configuration
python3 strategy_config.py
```

### Strategy Toggle

```python
# In multi_strategy_orchestrator.py
orchestrator.toggle_strategy('overnight_bias', True)   # Enable
orchestrator.toggle_strategy('vwap', False)            # Disable
```

### Configuration

```python
# Environment variables
export ENABLE_OVERNIGHT_BIAS_STRATEGY=true
export ENABLE_VWAP_STRATEGY=true
export MAX_TOTAL_POSITIONS=2
export MAX_DAILY_LOSS=-700.0
```

## Strategy Logic Flow

1. **03:00 ET**: Analyze 12-hour overnight bar
2. **Determine Bias**: Based on bar type and breakout direction
3. **Set Trigger Levels**: Overnight high/low for entry confirmation
4. **09:45-11:00 ET**: Primary entry window
5. **5-Minute Confirmation**: Wait for candle close beyond trigger
6. **VWAP/EMA20 Check**: Ensure price alignment with bias
7. **Entry Execution**: Enter position with calculated size
8. **Position Management**: Monitor for exits and scaling
9. **14:30-15:00 ET**: Force close all positions

## Performance Characteristics

### Advantages
- **Precision Entries**: High-probability setups with multiple confirmations
- **Risk Control**: Comprehensive exit rules and position sizing
- **Institutional Alignment**: Follows overnight sentiment and structure
- **Miyagi Optimized**: Designed specifically for small-cap ETF characteristics

### Risk Factors
- **Overnight Gaps**: May miss significant moves if not positioned
- **Theta Decay**: 0DTE options lose value quickly
- **Market Hours**: Limited to regular trading hours
- **Position Limits**: Maximum 2 positions total

## Testing

The strategy includes comprehensive tests:

```bash
python3 test_overnight_bias.py
```

**Test Coverage**:
- Overnight bias detection
- 5-minute confirmation logic
- Position sizing calculations
- Exit condition evaluation
- Strategy configuration validation

## Monitoring and Alerts

The system integrates with the existing alert system:

- **Bias Alerts**: When overnight bias is determined
- **Entry Alerts**: When positions are entered
- **Scaling Alerts**: When positions are scaled out
- **Exit Alerts**: When positions are closed

## Best Practices

1. **Start Small**: Begin with smaller position sizes to test the system
2. **Monitor Closely**: Watch for VWAP crosses and trigger level breaks
3. **Respect Time Stops**: Don't hold positions too long with 0DTE options
4. **Scale Appropriately**: Use the 30%/70% profit scaling rules
5. **Daily Reset**: Ensure overnight analysis runs at 3:00 AM ET

## Troubleshooting

### Common Issues

1. **No Bias Set**: Check if overnight analysis ran at 3:00 AM ET
2. **No Entry Signals**: Verify VWAP and EMA20 alignment
3. **Position Rejected**: Check daily loss limits and position counts
4. **Test Failures**: Ensure all dependencies are installed

### Debug Mode

```python
# Enable debug logging
import logging
logging.getLogger("OvernightBiasStrategy").setLevel(logging.DEBUG)
```

## Future Enhancements

1. **Additional Timeframes**: Support for different entry windows
2. **Dynamic Position Sizing**: Adjust based on volatility
3. **Advanced Filters**: Additional technical indicators
4. **Backtesting**: Historical performance analysis
5. **Machine Learning**: Pattern recognition improvements

## Conclusion

The Overnight Bias / 0DTE Execution Strategy provides a sophisticated approach to Miyagi options trading that combines institutional sentiment analysis with precise entry timing and comprehensive risk management. The strategy is designed to work alongside the existing VWAP strategy, providing multiple approaches to market opportunities while maintaining strict risk controls.

The implementation is production-ready and includes comprehensive testing, configuration management, and monitoring capabilities. The modular design allows for easy customization and future enhancements while maintaining system stability and performance.
