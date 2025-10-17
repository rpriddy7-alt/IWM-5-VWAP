# IWM-5-VWAP — Advanced VWAP Strategy System

Real-time trading system for IWM using advanced VWAP-based signals. Designed for deployment on Render as a Background Worker with Polygon.io market data and Pushover alerts.

## 🎯 Mission

Fire BUY alerts **only** when advanced VWAP conditions are met:
- **5-Minute VWAP Analysis** (primary signal)
- **Volume confirmation** (secondary validation)
- **Price momentum** (tertiary confirmation)

All trades use **advanced VWAP strategy** with intelligent exits that protect profits while maximizing gains.

---

## 🏗️ Architecture

### Core Components

```
main.py              ← Main orchestrator (entry point)
├── config.py        ← Configuration management
├── polygon_client.py ← WebSocket + REST API for Polygon.io
├── contract_selector.py ← 0DTE contract filtering & ranking
├── signals.py       ← Momentum signal + simple exit monitor
├── risk_manager.py  ← Position tracking & exit logic
├── alerts.py        ← Pushover notifications
├── logger.py        ← Structured logging
└── utils.py         ← Helper functions
```

### Data Feeds

| Feed | Type | Purpose |
|------|------|---------|
| **IWM Stocks Aggregates** | WebSocket | Per-second VWAP, volume, price |
| **Options Chain Snapshot** | REST (polled) | Contract liquidity for selection |

---

## 🚀 Setup

### 1. Clone & Install

```bash
git clone <your-repo-url>
cd IWMcallsONLY
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

**Required credentials:**
- **Polygon API Key**: [Get one here](https://polygon.io) (requires real-time options + stocks feeds)
- **Pushover Token**: [Create app here](https://pushover.net/apps/build)
- **Pushover User Key**: From your Pushover dashboard

### 3. Verify Setup

Before running, verify your configuration:

```bash
python diagnose.py
```

This checks:
- Environment variables are set correctly
- Required packages are installed
- System modules load properly
- Configuration is valid
- Current market hours status

### 4. Run Locally (Testing)

```bash
python main.py
```

The system will:
- Connect to Polygon WebSockets
- Monitor market hours (9:30-16:00 ET)
- Send alerts to Pushover when signals align
- Log all activity with diagnostic messages

**Monitor the logs** for these key indicators:
- `📊 Data feed active` - WebSocket receiving data (every 60s)
- `📈 Signal conditions` - Status of entry conditions (every 60s)
- `🚀 MOMENTUM SIGNAL` - Signal detected
- `🔥 ENTRY` - Buy alert sent

See **[DIAGNOSTIC_LOGGING.md](./DIAGNOSTIC_LOGGING.md)** for complete troubleshooting guide.

---

## ☁️ Deploy to Render

This system is designed to run as a **Background Worker** on Render.

### Step 1: Create Background Worker

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **New** → **Background Worker**
3. Connect your GitHub repo
4. Configure:
   - **Name**: `iwm-momentum-system`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
   - **Plan**: Choose appropriate tier (Starter or higher for real-time reliability)

### Step 2: Set Environment Variables

In Render dashboard, add:
```
POLYGON_API_KEY=<your_key>
PUSHOVER_TOKEN=<your_token>
PUSHOVER_USER_KEY=<your_user_key>
```

### Step 3: Deploy

- Render will deploy automatically on push to `IWM-MAIN` branch
- System handles `SIGTERM` gracefully on redeploys
- Logs viewable in Render dashboard

---

## 📊 Signal Logic

### Entry Conditions (all true)

#### 1️⃣ Spot Momentum
- IWM price > 1-min VWAP
- VWAP rising for ≥ 30 seconds
- Per-second volume > 95th percentile (20-min window)
- Price momentum (linear slope) positive

### Exit Triggers

| Trigger | Description |
|---------|-------------|
| **Hard Giveback** | 30% drop from peak mark |
| **VWAP Giveback** | 20% drop while price below VWAP |
| **VWAP Persistence** | 2×30s blocks below VWAP |
| **Stop Loss** | -15% P&L |
| **Time Stop** | 15:55 ET (mandatory flat) |

---

## 🎛️ Configuration

Adjustable via environment variables in `.env`:

### Entry Filters
- `DELTA_MIN` / `DELTA_MAX`: Contract delta range (default 0.30-0.45)
- `NO_ENTRY_AFTER`: Entry cutoff time ET (default 15:30)

### Risk Management
- `MAX_GIVEBACK_PERCENT`: Hard profit cap (default 30%)
- `TIGHTEN_GIVEBACK_PERCENT`: Adaptive cap when flow weakens (default 20%)
- `HARD_TIME_STOP`: Force close time ET (default 15:55)

### Anti-Chop
- `RELATIVE_VOLUME_MIN`: Min volume multiplier vs baseline (default 1.5×)
- `SPY_IWM_LAG_THRESHOLD`: Max ROC lag vs SPY on 5-min (default 0.20%)

---

## 📱 Alert Examples

### BUY Alert
```
🔥 IWM 0DTE CALL — BUY

IWM $215.34 | VWAP $215.12 (+0.10%)
Momentum +0.045%/s | Vol Z1.8

📊 O:IWM251002C00215000 2025-10-02 215c
Δ0.42 IV28.5%

💰 Entry ~$1.45 (mid $1.40 +$0.05)
Spread 2.1% | Size 35×40

⚠️ Hard Giveback 30% | Time Stop 15:55 ET
```

### SELL Alert
```
🚪 IWM 0DTE CALL — SELL

Reason: Giveback 31.2% (Hard cap 30%)

IWM $214.89 | VWAP $214.95
Peak $2.10 → Now $1.45

📊 O:IWM251002C00215000
🟢 P&L: +18.5%

✅ Close at market / best bid
```

---

## 📝 Logging & Diagnostics

The system includes comprehensive diagnostic logging to help troubleshoot issues.

### Key Log Messages

Every 60 seconds during operation:
```
📊 Data feed active: IWM $220.50, VWAP $220.30, Vol 1,250,000
📈 Signal conditions: Price>$220.30=True, VWAP↑=False, Vol surge=False (Z1.2), Momentum=+0.023
```

When a signal is detected:
```
🚀 MOMENTUM SIGNAL: IWM $220.50 > VWAP $220.30 (+0.09%), Vol Z=2.8, Momentum=+0.087
🔥 ENTRY: O:IWM251003C00220500 @ $1.45
✓ Alert sent: 🔥 IWM 0DTE CALL — BUY
```

### Troubleshooting

**If you're not seeing buy alerts:**

1. Run the diagnostic script:
   ```bash
   python diagnose.py
   ```

2. Check the logs for:
   - `📊 Data feed active` - Is WebSocket receiving data?
   - `📈 Signal conditions` - Which conditions are False?
   - `⏰ No entries allowed` - Time restrictions active?

3. See **[DIAGNOSTIC_LOGGING.md](./DIAGNOSTIC_LOGGING.md)** for complete troubleshooting guide

### Setting Log Levels

In `.env`:
```bash
LOG_LEVEL=INFO    # Standard logging
LOG_LEVEL=DEBUG   # Detailed debugging
LOG_LEVEL=WARNING # Only important messages
```

Logs are written to console and `iwm_momentum.log` with full trade history:

- Signal triggers & condition status
- Contract selection reasoning
- Entry/exit prices & P&L
- WebSocket connection status
- Error traces

---

## 🛡️ Resilience Features

| Feature | Behavior |
|---------|----------|
| **Data stall detection** | Alert after 5s silence; pause signals until recovery |
| **Chain snapshot failover** | Reuse last good snapshot up to 60s; skip skew if older |
| **Pushover retry** | 3 attempts with exponential backoff |
| **Idempotency** | Hash-based deduplication (1-min window) |
| **Graceful shutdown** | Close positions on `SIGTERM`/`SIGINT` |

---

## 🔧 Development

### Run Tests (when added)
```bash
pytest tests/
```

### Check Configuration
```bash
python diagnose.py
```

### Tail Logs
```bash
tail -f iwm_momentum.log
```

### Verify Signal Detection
Look for these patterns in logs:
- `📊 Data feed active` - WebSocket working
- `📈 Signal conditions` - Entry condition status  
- `🚀 MOMENTUM SIGNAL` - Signal detected
- See [DIAGNOSTIC_LOGGING.md](./DIAGNOSTIC_LOGGING.md) for details

---

## 📚 References

- [Polygon Options WebSocket](https://polygon.io/docs/options/ws_getting_started)
- [Polygon Options Chain Snapshot](https://polygon.io/docs/options/get_v3_snapshot_options__underlyingasset)
- [Pushover API](https://pushover.net/api)
- [Render Background Workers](https://render.com/docs/background-workers)

---

## ⚠️ Disclaimer

This system generates **alerts only** and does not execute trades. It is provided for educational and research purposes. Trading options involves substantial risk. Always consult a financial advisor before making investment decisions.

---

## 🤝 Support

**Not seeing buy alerts?** Run the diagnostic script:
```bash
python diagnose.py
```

Then check [DIAGNOSTIC_LOGGING.md](./DIAGNOSTIC_LOGGING.md) for troubleshooting steps.

For issues or questions:
1. Run `python diagnose.py` to check your setup
2. Check logs for diagnostic messages (see DIAGNOSTIC_LOGGING.md)
3. Verify API credentials in `.env`
4. Ensure Polygon subscription includes real-time options + stocks feeds
5. Review Render logs if deployed

---

Built with Polygon.io · Pushover · Python 3.11+


