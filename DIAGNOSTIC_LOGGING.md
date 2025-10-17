# Diagnostic Logging Guide

## Problem: Why are buy alerts not being sent?

This guide explains how to use the new diagnostic logging to identify why buy alerts aren't being sent.

## New Log Messages

### 1. Data Feed Status (Every 60 seconds)
```
📊 Data feed active: IWM $220.50, VWAP $220.30, Vol 1,250,000
```
**What it means:** The WebSocket is receiving live market data for IWM.

**If you DON'T see this:**
- Check that your `POLYGON_API_KEY` is valid
- Check that the WebSocket connection succeeded
- Look for connection errors earlier in the logs

### 2. Signal Conditions (Every 60 seconds)
```
📈 Signal conditions: Price>$220.30=True, VWAP↑=False, Vol surge=False (Z1.2), Momentum=+0.023
```
**What it means:** Shows the status of all 4 entry conditions:
- `Price>$220.30=True` - IWM price is above 1-min VWAP ✓
- `VWAP↑=False` - VWAP is NOT rising for 30+ seconds ✗
- `Vol surge=False` - Volume is NOT at 95th percentile ✗
- `Momentum=+0.023` - Price momentum (needs to be > 0) ✓

**For a buy signal, ALL must be True.**

### 3. Signal Monitoring (Every 5 minutes)
```
🔍 Monitoring for signals (180 data points collected)
```
**What it means:** The system is actively checking for signals and has collected N seconds of data.

**If you see low numbers (< 60):**
- System just started and needs more data
- WebSocket connection may have recently reconnected

### 4. Time Restrictions (Every 5 minutes after cutoff)
```
⏰ No entries allowed after 15:30 ET
```
**What it means:** The current time is past the `NO_ENTRY_AFTER` cutoff (default 15:30 ET).

**Solution:** Wait until the next trading day, or adjust `NO_ENTRY_AFTER` in `.env` if testing.

### 5. Entry Cooldown (Every 60 seconds during cooldown)
```
Entry cooldown: 180s remaining before next entry allowed
```
**What it means:** The system recently entered a trade and must wait 5 minutes before the next entry.

**This is normal behavior** to prevent over-trading.

### 6. Chain Data Issues (Debug level)
```
No chain data available for entry check
```
or
```
Chain data too old (75s > 60s)
```
**What it means:** The options chain snapshot is missing or stale.

**Check for earlier errors** in the chain update loop.

### 7. Signal Cooldown (Debug level)
```
Signal cooldown active: 45s remaining
```
**What it means:** A signal was detected less than 60 seconds ago. The system waits 60s between signals.

### 8. Insufficient Data (Debug level)
```
Insufficient data: 30 < 60 seconds
```
**What it means:** Not enough market data collected yet. Wait for more data.

## How to Diagnose Issues

### Issue: "I never see any buy alerts"

1. **Check data feed is active:**
   - Look for `📊 Data feed active` messages every 60 seconds
   - If missing, check WebSocket connection and API key

2. **Check signal conditions:**
   - Look for `📈 Signal conditions` messages every 60 seconds
   - Identify which conditions are `False`
   - ALL conditions must be `True` for a signal

3. **Check time restrictions:**
   - Look for `⏰ No entries allowed` messages
   - Entries are only allowed 09:30 - 15:30 ET by default

4. **Check for contract selection issues:**
   - Look for `Momentum signal but no viable contract` warnings
   - This means a signal triggered but no suitable options contract was found

### Issue: "I see momentum signals but no alerts"

1. **Check contract selector:**
   - Look for `Momentum signal but no viable contract` 
   - Check that options chain is updating (look for "Chain snapshot: N contracts")

2. **Check alert sending:**
   - Look for `✓ Alert sent` or `Failed to send buy alert` messages
   - Check `PUSHOVER_TOKEN` and `PUSHOVER_USER_KEY` are valid

3. **Check Pushover errors:**
   - Look for `Pushover API error` or `Pushover HTTP` error messages
   - These indicate issues with Pushover credentials or service

### Issue: "Signals are detected but very infrequently"

This is **expected behavior**. The momentum conditions are designed to be strict:

- Price must be above VWAP (bullish)
- VWAP must be rising for 30+ seconds (sustained momentum)
- Volume must exceed 95th percentile (significant activity)
- Price momentum must be positive (upward trend)

All 4 conditions occurring simultaneously is relatively rare, which is by design to ensure high-quality signals.

## Setting Log Levels

To see more detailed logs, set in your `.env`:
```
LOG_LEVEL=DEBUG
```

To see only important messages:
```
LOG_LEVEL=WARNING
```

## Common Patterns

### Normal Operation (No Signal)
```
📊 Data feed active: IWM $220.50, VWAP $220.30, Vol 1,250,000
📈 Signal conditions: Price>$220.30=True, VWAP↑=False, Vol surge=False (Z1.2), Momentum=+0.023
🔍 Monitoring for signals (180 data points collected)
Chain snapshot: 245 contracts
```

### Signal Detected and Alert Sent
```
📊 Data feed active: IWM $220.50, VWAP $220.30, Vol 1,250,000
📈 Signal conditions: Price>$220.30=True, VWAP↑=True, Vol surge=True (Z2.8), Momentum=+0.087
🚀 MOMENTUM SIGNAL: IWM $220.50 > VWAP $220.30 (+0.09%), Vol Z=2.8, Momentum=+0.087
🔥 ENTRY: O:IWM251003C00220500 @ $1.45
✓ Alert sent: 🔥 IWM 0DTE CALL — BUY
```

### Time Restrictions Active
```
📊 Data feed active: IWM $220.50, VWAP $220.30, Vol 1,250,000
📈 Signal conditions: Price>$220.30=True, VWAP↑=True, Vol surge=True (Z2.8), Momentum=+0.087
⏰ No entries allowed after 15:30 ET
```

## Next Steps

If you've reviewed the logs and still can't identify why alerts aren't being sent:

1. Share the last 100 lines of log output
2. Note what time of day the system is running (ET)
3. Verify your Polygon subscription includes real-time stocks + options data
4. Verify your Pushover credentials are correct
