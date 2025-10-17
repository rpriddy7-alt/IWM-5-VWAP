# IWM Momentum System - Deployment Guide

## Pre-Deployment Checklist

### 1. API Credentials

- [ ] **Polygon.io API Key**
  - Sign up at [polygon.io](https://polygon.io)
  - Requires **Starter plan or higher** for real-time options + stocks feeds
  - Verify WebSocket access is enabled

- [ ] **Pushover Account**
  - Create account at [pushover.net](https://pushover.net)
  - Create an application: [Create App](https://pushover.net/apps/build)
  - Note your **User Key** (from dashboard)
  - Note your **Token** (from app settings)

### 2. Local Testing (Recommended)

Before deploying to production, test locally:

```bash
# 1. Clone repository
git clone <your-repo-url>
cd IWMcallsONLY

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your credentials

# 5. Verify configuration
python config.py

# 6. Run system (during market hours for full test)
python main.py
```

**Expected startup output:**
```
✓ Configuration valid
Initializing IWM 0DTE Momentum System...
✓ System initialized
Connecting to Polygon WebSockets...
✓ WebSocket connections established
✓ Background tasks started
🚀 IWM Momentum System ONLINE
```

---

## Render Deployment

### Option 1: One-Click Deploy (Recommended)

1. Fork/push this repository to GitHub
2. Connect to Render: [dashboard.render.com](https://dashboard.render.com)
3. Click **New** → **Background Worker**
4. Select your repository
5. Render will auto-detect `render.yaml` configuration
6. Add environment variables (see below)
7. Click **Create Worker**

### Option 2: Manual Setup

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **New** → **Background Worker**
3. Connect your GitHub repository
4. Configure:

| Setting | Value |
|---------|-------|
| **Name** | `iwm-momentum-system` |
| **Environment** | Python 3 |
| **Branch** | `IWM-MAIN` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `python main.py` |
| **Plan** | Starter or higher (recommended: Standard for reliability) |

### Environment Variables (Required)

Add these in **Environment** tab:

```bash
# Required
POLYGON_API_KEY=<your_polygon_key>
PUSHOVER_TOKEN=<your_pushover_app_token>
PUSHOVER_USER_KEY=<your_pushover_user_key>

# Optional (defaults shown)
LOG_LEVEL=INFO
UNDERLYING_SYMBOL=IWM
NO_ENTRY_AFTER=15:30
HARD_TIME_STOP=15:55
TIMEZONE=America/New_York
```

### Auto-Deploy Setup

Enable auto-deploy in Render dashboard:
- **Settings** → **Deploy** → Enable "Auto-Deploy"
- Pushes to `IWM-MAIN` branch will automatically redeploy
- System handles `SIGTERM` gracefully (closes positions, disconnects WebSockets)

---

## Post-Deployment Verification

### 1. Check Logs

In Render dashboard, go to **Logs** tab. Look for:

```
✓ Configuration valid
✓ System initialized
✓ WebSocket connections established
🚀 IWM Momentum System ONLINE
```

### 2. Test Alert Delivery

You should receive a Pushover notification:
```
🤖 IWM System Alert
System started at HH:MM:SS ET
```

If no alert received:
- Verify Pushover credentials
- Check Pushover app is installed on your device
- Verify device is enabled in Pushover dashboard

### 3. Monitor During Market Hours

During market hours (9:30-16:00 ET):
- System should connect to WebSocket feeds
- Chain snapshot polling should start (every 10s)
- No errors in logs related to authentication or rate limits

### 4. Verify Signal Detection

Watch logs for signal activity:
```
✓ SPOT SIGNAL: Price 215.34 > VWAP 215.12, VWAP rising, Vol Z-score 2.1
✓ FLOW SIGNAL: Net notional $45,000, Z-score 2.3, Ask-side 68.0%
✓ SKEW SIGNAL: Current 1.4 vol pts, Median 0.2, Diff +1.2
```

When all three align:
```
🔥 BUY SIGNAL CONFIRMED - All three conditions aligned!
```

---

## Monitoring & Maintenance

### Daily Checks

1. **Render Dashboard**: Verify worker is running (green status)
2. **Logs**: Check for errors or warnings
3. **Pushover**: Ensure alerts are being received
4. **Polygon Usage**: Monitor API usage in Polygon dashboard

### Common Issues

#### ❌ "POLYGON_API_KEY is required"
- Environment variable not set in Render
- Go to **Environment** tab, add `POLYGON_API_KEY`

#### ❌ "Failed to authenticate WebSocket"
- Invalid API key
- Polygon subscription doesn't include real-time feeds
- Verify plan at [polygon.io/dashboard](https://polygon.io/dashboard)

#### ❌ "DATA STALL WARNING"
- WebSocket connection dropped
- System will auto-recover when feed resumes
- If persistent, check Polygon service status

#### ❌ "Pushover HTTP 400"
- Invalid token or user key
- Verify credentials in Pushover dashboard

#### ⚠️ "Chain snapshot returned no data"
- Not during market hours, OR
- 0DTE options not available today (weekends, holidays)
- Normal outside 9:30-16:00 ET

### Health Monitoring

**Expected behavior:**
- System runs 24/7 (sleeps outside market hours)
- Active 9:30-16:00 ET Monday-Friday
- Sends system start/stop alerts
- Zero downtime during market hours
- Graceful restarts on deploys

**Anomaly indicators:**
- Frequent restarts (check logs for crashes)
- No signal activity during volatile market hours
- Repeated data stall alerts
- Failed Pushover deliveries

---

## Upgrading & Redeployment

### Manual Redeploy

1. Push changes to `IWM-MAIN` branch
2. Render auto-deploys (if enabled)
3. System receives `SIGTERM`, closes positions gracefully
4. New version starts automatically

### Rollback

If deployment fails:
1. Go to Render dashboard → **Deploys** tab
2. Click **Rollback** on last successful deploy
3. System will revert to previous version

### Zero-Downtime Updates

For critical market hours:
- Schedule deploys outside 9:30-16:00 ET
- Test changes in a separate Render service first
- Monitor logs closely after deploy

---

## Scaling & Performance

### Resource Requirements

| Plan | CPU | RAM | Use Case |
|------|-----|-----|----------|
| **Free** | Shared | 512 MB | Testing only (sleeps after 15 min) |
| **Starter** | Shared | 512 MB | Light production (low trade frequency) |
| **Standard** | 0.5 CPU | 512 MB | **Recommended** for real-time reliability |
| **Pro** | 1 CPU | 1 GB | High-frequency or multi-symbol expansion |

### Performance Tuning

If experiencing lag or missed signals:

1. **Upgrade Render plan** (more CPU/RAM)
2. **Reduce tracked contracts**: Set `MAX_CONTRACTS_TO_TRACK=2` in env vars
3. **Increase chain poll interval**: Edit `config.py` → `CHAIN_SNAPSHOT_INTERVAL_SECONDS=15`
4. **Check Polygon latency**: Ping `socket.polygon.io` from Render shell

### Multi-Instance (Future)

To monitor multiple symbols:
- Deploy separate Render workers per symbol
- Set `UNDERLYING_SYMBOL` env var per worker
- Each worker gets its own Pushover alerts

---

## Cost Estimate

### Monthly Costs

| Service | Plan | Cost |
|---------|------|------|
| **Polygon.io** | Starter | $200/mo |
| **Render** | Standard Worker | $7/mo |
| **Pushover** | One-time | $5 |
| **Total** | | ~$207/mo |

### Free Tier Testing

For paper trading / testing:
- Polygon: 14-day free trial
- Render: Free tier (with sleep limitations)
- Pushover: 7-day free trial

---

## Security Best Practices

1. **Never commit `.env`** to git (already in `.gitignore`)
2. **Use Render env vars** for secrets (not hardcoded)
3. **Rotate API keys** periodically
4. **Monitor Polygon usage** to detect unauthorized access
5. **Enable Render IP restrictions** if needed

---

## Support & Troubleshooting

### Logs

**Local:**
```bash
tail -f logs/iwm_momentum.log
```

**Render:**
- Dashboard → Logs tab
- Download logs via Render CLI: `render logs <service-id>`

### Debug Mode

Enable verbose logging:
```bash
# In .env or Render env vars
LOG_LEVEL=DEBUG
```

### Contact Points

- **Polygon Support**: [support.polygon.io](mailto:support@polygon.io)
- **Render Support**: [render.com/support](https://render.com/support)
- **Pushover Support**: [pushover.net/support](https://pushover.net/support)

---

## Emergency Shutdown

If you need to stop the system immediately:

### Render Dashboard
1. Go to service page
2. Click **Suspend** (stops without deleting)
3. System sends shutdown alert to Pushover
4. Positions closed gracefully if during market hours

### Via Git
```bash
# Delete render.yaml to prevent auto-deploy
git rm render.yaml
git commit -m "Emergency shutdown"
git push origin IWM-MAIN
```

### Via Render Settings
- Settings → Danger Zone → Delete Service

---

## Next Steps After Deployment

1. ✅ Verify system started (check logs)
2. ✅ Confirm Pushover alerts received
3. ✅ Monitor first market session (9:30-16:00 ET)
4. ✅ Review end-of-day logs for signal quality
5. ✅ Adjust thresholds in env vars if needed
6. ✅ Set up daily log review routine

---

**Deployment complete! System is now monitoring IWM 0DTE momentum signals 24/7.**


