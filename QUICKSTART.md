# IWM 0DTE Momentum System - Quick Start

## ⚡ 60-Second Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure credentials
cp .env.example .env
# Edit .env with your API keys

# 3. Verify setup
python verify.py

# 4. Start system
./start.sh
# Or: python main.py
```

---

## 📋 What You Need

### Required API Keys

| Service | What For | Get It Here | Cost |
|---------|----------|-------------|------|
| **Polygon.io** | Real-time options + stocks data | [polygon.io](https://polygon.io) | $200/mo (Starter+) |
| **Pushover** | Mobile alerts | [pushover.net](https://pushover.net) | $5 one-time |

### Minimum Requirements

- Python 3.9+
- Internet connection
- API access during US market hours (9:30-16:00 ET)

---

## 🎯 First Run Checklist

### 1. Verify Configuration

```bash
python config.py
```

**Expected output:**
```
✓ Configuration valid

IWM 0DTE Momentum System Configuration:
  Symbol: IWM
  Delta Range: 0.3 - 0.45
  Max Contracts Tracked: 3
  Entry Cutoff: 15:30 ET
  Hard Stop: 15:55 ET
  Max Giveback: 30.0%
  Polygon API: ✓ Configured
  Pushover: ✓ Configured
```

### 2. Test Connectivity

Start the system during market hours (9:30-16:00 ET):

```bash
python main.py
```

**Watch for:**
- ✓ WebSocket connections established
- ✓ Chain snapshot polling started
- ✓ System sends startup alert to Pushover

### 3. Monitor Logs

Open a second terminal:
```bash
tail -f logs/iwm_momentum.log
```

**Look for signal activity:**
```
Momentum signal: price 215.34 > VWAP 215.12 (+0.10%)
Volume Z-score: 2.1 | Slope: +0.045%/s
```

---

## 📱 Expected Alerts

### Startup
```
🤖 IWM System Alert
System started at 09:30:15 ET
```

### Buy Signal
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

### Sell Signal
```
🚪 IWM 0DTE CALL — SELL

Reason: Giveback 30.2% (Hard cap 30%)

IWM $214.89 | VWAP $214.95
Peak $2.10 → Now $1.45

📊 O:IWM251002C00215000
🟢 P&L: +18.5%

✅ Close at market / best bid
```

---

## 🐛 Troubleshooting

### Issue: "POLYGON_API_KEY is required"

**Fix:**
```bash
# Make sure .env exists
ls -la .env

# Check it contains your key
grep POLYGON_API_KEY .env

# Should show: POLYGON_API_KEY=pk_xxxxxxxxxx
```

### Issue: "Failed to authenticate WebSocket"

**Causes:**
1. Invalid API key
2. Polygon plan doesn't include real-time feeds
3. API key permissions issue

**Fix:**
- Log in to [polygon.io/dashboard](https://polygon.io/dashboard)
- Verify subscription is **Starter or higher**
- Check "Real-Time WebSocket" is enabled
- Try regenerating API key

### Issue: No alerts received

**Check:**
1. Pushover app installed on device?
2. Device enabled in Pushover dashboard?
3. Correct user key in .env?
4. System actually generated alerts? (check logs)

**Test Pushover:**
```bash
curl -s \
  -F "token=YOUR_TOKEN" \
  -F "user=YOUR_USER_KEY" \
  -F "message=Test alert" \
  https://api.pushover.net/1/messages.json
```

### Issue: "Chain snapshot returned no data"

**Normal if:**
- Outside market hours (9:30-16:00 ET)
- Weekends or holidays
- 0DTE options not listed yet (check early morning)

**Problem if:**
- During active market hours repeatedly
- Then check Polygon API status

### Issue: "DATA STALL WARNING"

**What it means:**
- No data received for 5+ seconds
- Signal generation paused

**Usually:**
- Temporary network hiccup
- System auto-recovers

**If persistent:**
- Check internet connection
- Restart system
- Check Polygon service status

---

## 🚀 Deploy to Production

Once local testing works:

### Option A: Render (Recommended)

```bash
# 1. Push to GitHub
git add .
git commit -m "Initial IWM system deployment"
git push origin IWM-MAIN

# 2. Go to render.com
# - New → Background Worker
# - Connect GitHub repo
# - Auto-detects render.yaml
# - Add environment variables
# - Deploy!
```

### Option B: Cloud VM

Run as systemd service:
```bash
# Install
sudo cp iwm-momentum.service /etc/systemd/system/
sudo systemctl enable iwm-momentum
sudo systemctl start iwm-momentum

# Monitor
sudo journalctl -u iwm-momentum -f
```

---

## 📊 What to Expect

### Signal Frequency

**Typical day:**
- 0-3 BUY signals (most days)
- 5-10 signal "near-misses" (2/3 conditions met)
- More signals on volatile days

**Low signal days:**
- Choppy/rangebound market
- Low IWM relative volume
- Flat skew (no directional bias)

### Performance Monitoring

**Daily review:**
1. How many signals?
2. What P&L outcomes?
3. Any false positives?
4. Exit quality (too early/late)?

**Weekly review:**
1. Adjust thresholds if needed
2. Review giveback % (30% too tight/loose?)
3. Review VWAP persistence setting (2 blocks?)
4. Confirm time stop remains appropriate

---

## 🎛️ Tuning Parameters

Edit `.env` to adjust:

### More Selective (Fewer Signals)
```bash
VWAP_LOOKBACK_SECONDS=90    # Default 60
VWAP_RISING_SECONDS=45      # Default 30
SPOT_VOLUME_PERCENTILE=97.5 # Default 95.0
```

### More Aggressive (More Signals)
```bash
VWAP_LOOKBACK_SECONDS=45
VWAP_RISING_SECONDS=20
SPOT_VOLUME_PERCENTILE=92.5
```

### Tighter Risk (Earlier Exits)
```bash
MAX_GIVEBACK_PERCENT=25
TIGHTEN_GIVEBACK_PERCENT=15
VWAP_EXIT_BLOCKS=1
```

**Important:** Test any changes during paper trading first!

---

## 📚 Additional Resources

- **Full Documentation**: [README.md](README.md)
- **Deployment Guide**: [DEPLOYMENT.md](DEPLOYMENT.md)
- **System Verification**: Run `python verify.py`

---

## 🆘 Getting Help

1. **Check logs first**: `tail -f logs/iwm_momentum.log`
2. **Run verification**: `python verify.py`
3. **Review configuration**: `python config.py`
4. **Test connectivity**: During market hours, watch for signal activity

---

**System ready? Let's go! 🚀**

```bash
./start.sh
```


