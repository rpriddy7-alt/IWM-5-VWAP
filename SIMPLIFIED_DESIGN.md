# IWM 0DTE Momentum System - SIMPLIFIED DESIGN

## 🎯 What It Actually Does

### 1. Monitor IWM Stock (Real-Time WebSocket)
- Watch per-second price action
- Calculate 1-minute VWAP
- Track volume surges
- Detect momentum breaks

### 2. When IWM Shows Momentum Signal:
**Trigger Conditions:**
- Price > 1-min VWAP
- VWAP rising for 30+ seconds  
- Volume > 95th percentile

### 3. Find Best 0DTE Call Contract:
- Query Polygon options chain
- Filter for:
  - Delta 0.30-0.45 (ATM to slightly OTM)
  - Spread ≤ 3%
  - Volume ≥ 500
  - OI ≥ 1000
- Pick highest volume contract

### 4. Send Pushover Alert:
```
🔥 IWM 0DTE CALL — BUY

IWM $215.34 > VWAP $215.12
Volume surge: +2.1σ

📊 O:IWM251002C00215000
Strike: 215 | Delta: 0.42
Entry: ~$1.45

⚠️ Stop: 15:55 ET
```

---

## ❌ What We DON'T Need:
- ~~Options flow monitoring~~ (removed)
- ~~Net call buying detection~~ (removed)
- ~~Skew calculations~~ (removed)
- ~~Options WebSocket subscriptions~~ (removed)
- ~~Trade/quote aggregation~~ (removed)

---

## ✅ What We Keep:
- IWM stock WebSocket (per-sec aggregates)
- VWAP calculation
- Volume percentile tracking
- Polygon REST API (for finding contracts when signal fires)
- Pushover alerts
- Risk management (giveback, time stops)

---

**MUCH SIMPLER = MUCH MORE RELIABLE**

