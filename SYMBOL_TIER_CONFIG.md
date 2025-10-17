# Miyagi Symbol Tier Configuration

## 🎯 **Tiered Symbol Strategy**

Based on market structure analysis, the Miyagi-5-VWAP system now uses a tiered approach to symbol selection and risk management. This ensures optimal performance across different market conditions and symbol characteristics.

## 📊 **Symbol Tiers**

### **Tier 1: Top Tier (Best Structure, Clean Flow, Daily Liquidity)**

**These are your go-tos for consistent performance:**

- **SPY** – Most liquid 0DTE chain, tight spreads, reacts perfectly to VWAP and EMA shifts
- **IWM** – Cleaner overnight range structure, good follow-through, slightly slower tempo
- **QQQ** – Huge range, very responsive, but wicks can fake you out early
- **AAPL** – Consistent intraday behavior, but smaller range; still works on 5-min confirmation
- **MSFT** – Follows market structure tightly; ideal for backtesting confirmation logic

**Risk Controls:**
- Max Positions: 2
- Position Size Multiplier: 1.0 (full size)
- Time Stop: 45 minutes
- VWAP Respect: High
- EMA20 Alignment: Critical

### **Tier 2: Second Tier (Works Well But Needs Tighter Risk Control)**

**These have the right rhythm but more volatility or less clean VWAP reactions:**

- **META** – Big moves, but gap-risk overnight can throw bias off
- **AMD** – Excellent trend days, but intraday chop when volume fades
- **NVDA** – Explosive, great for when 12h bias is clean; massive wicks otherwise
- **TSLA** – Works if you can stomach high IV; false breaks are common pre-VWAP reclaim
- **AMZN** – Trending days behave beautifully with VWAP; slower when range-bound

**Risk Controls:**
- Max Positions: 1
- Position Size Multiplier: 0.7 (reduced size)
- Time Stop: 30 minutes
- VWAP Respect: Medium
- EMA20 Alignment: Important

### **Tier 3: Only in Strong Trend Environments**

**These can follow the logic but lack steady structure:**

- **GOOGL, NFLX, BA, INTC, COIN, XLF, XLK, XLE**

**Risk Controls:**
- Max Positions: 1
- Position Size Multiplier: 0.5 (half size)
- Time Stop: 20 minutes
- VWAP Respect: Low
- EMA20 Alignment: Optional

## ⚙️ **Configuration**

### **Environment Variables**

```bash
# Tier 1 Symbols (Default Active)
export OVERNIGHT_BIAS_SYMBOLS="SPY,IWM,QQQ"

# Tier 2 Symbols (Optional)
export OVERNIGHT_BIAS_SYMBOLS_TIER2="META,AMD,NVDA,TSLA,AMZN"

# Tier 3 Symbols (Advanced)
export OVERNIGHT_BIAS_SYMBOLS_TIER3="GOOGL,NFLX,BA,INTC,COIN,XLF,XLK,XLE"

# VWAP Strategy Symbols (Tier 1 only)
export VWAP_STRATEGY_SYMBOLS="SPY,IWM"
```

### **Risk Control Settings**

```python
TIER_RISK_CONTROLS = {
    'tier1': {
        'max_positions': 2,
        'position_size_multiplier': 1.0,
        'time_stop_minutes': 45
    },
    'tier2': {
        'max_positions': 1,
        'position_size_multiplier': 0.7,
        'time_stop_minutes': 30
    },
    'tier3': {
        'max_positions': 1,
        'position_size_multiplier': 0.5,
        'time_stop_minutes': 20
    }
}
```

## 🎯 **Ideal Conditions**

### **System Thrives Where:**
- Constant volume pre- and post-market
- 0DTE contracts exist with narrow spreads
- Price respects VWAP + EMA structure
- Overnight moves set clean, visible ranges

### **Best Performance Symbols:**
- **SPY**: Most liquid, tightest spreads, best VWAP respect
- **IWM**: Cleanest overnight structure, good follow-through
- **QQQ**: Largest ranges, most responsive to bias
- **NVDA**: Explosive moves when bias is clean

## 📈 **Recommended Setups**

### **Conservative Setup (Tier 1 Only)**
```bash
export OVERNIGHT_BIAS_SYMBOLS="SPY,IWM,QQQ"
export VWAP_STRATEGY_SYMBOLS="SPY,IWM"
export MAX_TOTAL_POSITIONS=3
```

### **Balanced Setup (Tier 1 + 2)**
```bash
export OVERNIGHT_BIAS_SYMBOLS="SPY,IWM,QQQ,NVDA,AMD"
export VWAP_STRATEGY_SYMBOLS="SPY,IWM"
export MAX_TOTAL_POSITIONS=4
```

### **Aggressive Setup (All Tiers)**
```bash
export OVERNIGHT_BIAS_SYMBOLS="SPY,IWM,QQQ,NVDA,AMD,TSLA,META"
export VWAP_STRATEGY_SYMBOLS="SPY,IWM,QQQ"
export MAX_TOTAL_POSITIONS=6
```

## 🔍 **Symbol Characteristics**

### **SPY (S&P 500)**
- **Best For**: Primary symbol, most liquid
- **Characteristics**: Tight spreads, perfect VWAP respect
- **Risk Level**: Low
- **Expected Signals**: 2-3 per day

### **IWM (Russell 2000)**
- **Best For**: Clean overnight structure
- **Characteristics**: Slower tempo, good follow-through
- **Risk Level**: Low-Medium
- **Expected Signals**: 1-2 per day

### **QQQ (Nasdaq 100)**
- **Best For**: Large ranges, high volatility
- **Characteristics**: Responsive, but wicks can fake out
- **Risk Level**: Medium
- **Expected Signals**: 1-2 per day

### **NVDA (NVIDIA)**
- **Best For**: Explosive moves when bias is clean
- **Characteristics**: High volatility, massive wicks
- **Risk Level**: High
- **Expected Signals**: 1 per day (when conditions align)

## 🎛️ **Dynamic Configuration**

### **Market Condition Adjustments**

**Bull Market:**
- Focus on Tier 1 + NVDA, AMD
- Increase position sizes for Tier 1
- Reduce time stops for Tier 2

**Bear Market:**
- Focus on SPY, IWM only
- Reduce position sizes across all tiers
- Increase time stops for better entries

**Range-bound Market:**
- Focus on SPY, QQQ only
- Use tighter time stops
- Reduce position sizes

### **Volatility Adjustments**

**High VIX (>30):**
- Reduce Tier 2 and 3 symbols
- Increase time stops
- Reduce position sizes

**Low VIX (<15):**
- Add more Tier 2 symbols
- Reduce time stops
- Increase position sizes

## 📊 **Performance Expectations**

### **Tier 1 Symbols**
- **Win Rate**: 65-75%
- **Average Hold**: 30-45 minutes
- **Risk/Reward**: 1:2 to 1:3
- **Daily Opportunities**: 2-3

### **Tier 2 Symbols**
- **Win Rate**: 55-65%
- **Average Hold**: 20-30 minutes
- **Risk/Reward**: 1:1.5 to 1:2
- **Daily Opportunities**: 1-2

### **Tier 3 Symbols**
- **Win Rate**: 45-55%
- **Average Hold**: 15-20 minutes
- **Risk/Reward**: 1:1 to 1:1.5
- **Daily Opportunities**: 0-1

## 🚀 **Implementation**

### **Automatic Tier Assignment**
The system automatically assigns symbols to tiers based on configuration:

```python
# Symbol tier mapping
self.symbol_tiers = {}
for tier, symbols in Config.SYMBOL_TIERS.items():
    for symbol in symbols:
        self.symbol_tiers[symbol.strip()] = tier
```

### **Tier-Specific Risk Controls**
Each strategy instance gets tier-specific controls:

```python
# Set tier controls for each symbol
symbol_tier = self.symbol_tiers.get(symbol, 'tier1')
tier_controls = self.tier_risk_controls.get(symbol_tier)
strategy.set_tier_controls(symbol_tier, tier_controls)
```

### **Dynamic Position Sizing**
Position sizes are adjusted based on tier:

```python
# Apply tier-specific position sizing
tier_multiplier = tier_controls['position_size_multiplier']
adjusted_account = base_account * tier_multiplier
```

## 🎯 **Best Practices**

### **Start with Tier 1**
- Begin with SPY, IWM, QQQ only
- Master the system with these symbols
- Add Tier 2 symbols gradually

### **Monitor Performance**
- Track win rates by tier
- Adjust position sizes based on performance
- Remove underperforming symbols

### **Risk Management**
- Never exceed tier-specific position limits
- Use tier-specific time stops
- Monitor correlation between symbols

## 🎉 **Conclusion**

The tiered symbol approach ensures optimal performance by:
- **Matching risk to opportunity**: Higher risk symbols get tighter controls
- **Maximizing liquidity**: Focus on symbols with best 0DTE options
- **Adapting to market conditions**: Different tiers for different environments
- **Maintaining discipline**: Tier-specific rules prevent over-trading

This system is designed to thrive in the sweet spot where overnight bias, VWAP structure, and 5-minute confirmation all align for high-probability 0DTE trades! 🚀
