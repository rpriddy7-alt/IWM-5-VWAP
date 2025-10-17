# 🚨 URGENT - READ THIS FIRST 🚨

## YOU ARE THE NEXT AGENT AFTER CURSOR RESTART

**Previous Agent:** Completed full system skeleton and pushed to GitHub  
**Your Mission:** Deploy to Render using MCP integration  
**User Status:** Waiting to provide Render access after you read this

---

## ✅ WHAT'S DONE (YOU DON'T NEED TO BUILD)

- **COMPLETE SKELETON** - All code written (main.py, signals.py, risk_manager.py, etc.)
- **PUSHED TO GITHUB** - Commit `d8e53bb` on branch `IWM-MAIN`
- **RENDER CONFIG READY** - `render.yaml` configured for one-click deploy
- **DOCUMENTATION COMPLETE** - README.md, DEPLOYMENT.md, QUICKSTART.md, STATUS.md

**Repository:** https://github.com/rpriddy7-alt/IWMcallsONLY.git  
**Branch:** IWM-MAIN

---

## 🎯 YOUR TASK (DO THIS NOW)

### Step 1: Verify GitHub Push
```bash
cd /Users/raypriddy/IWMcallsONLY
git status  # Should say "nothing to commit, working tree clean"
git log --oneline -1  # Should show commit d8e53bb
```

### Step 2: Connect to Render

**User will provide Render access.** When they do:

1. **Check for Render MCP tools**
   - Look for `mcp_render_*` tools in your tool list
   - If available, use those (preferred)
   - If not, guide user through manual dashboard setup

2. **Create Background Worker**
   - Name: `iwm-momentum-system`
   - Type: Background Worker
   - Repo: `https://github.com/rpriddy7-alt/IWMcallsONLY.git`
   - Branch: `IWM-MAIN`
   - Build: `pip install -r requirements.txt`
   - Start: `python main.py`
   - Plan: Standard (recommended) or Starter minimum

3. **Set Environment Variables** (ask user for these)
   ```
   POLYGON_API_KEY=<user provides>
   PUSHOVER_TOKEN=<user provides>
   PUSHOVER_USER_KEY=<user provides>
   ```

4. **Deploy and Monitor**
   - Trigger deploy
   - Watch logs for: "🚀 IWM Momentum System ONLINE"
   - Verify Pushover alert sent to user's phone

---

## 📚 CRITICAL FILES TO UNDERSTAND

### If User Has Questions
1. **STATUS.md** - Complete build status & design philosophy
2. **DEPLOYMENT.md** - Step-by-step Render deployment guide
3. **main.py** - Entry point, shows how everything connects

### If Deployment Fails
1. Check logs for error message
2. Verify environment variables set correctly
3. Confirm Polygon API key is Starter+ plan (not Free)
4. See troubleshooting in DEPLOYMENT.md

---

## 🔑 REQUIRED FROM USER

**3 API Credentials** (ask for these):

1. **POLYGON_API_KEY**
   - Format: `pk_xxxxxxxxxxxxx`
   - Must be Starter plan or higher
   - Must have real-time WebSocket access

2. **PUSHOVER_TOKEN**
   - Format: `axxxxxxxxxxxxx` (app token)
   - From Pushover app dashboard

3. **PUSHOVER_USER_KEY**
   - Format: `uxxxxxxxxxxxxx` (user key)
   - From Pushover user dashboard

---

## ✅ SUCCESS CRITERIA

After deployment, you should see:

**In Render Logs:**
```
✓ Configuration valid
✓ System initialized
✓ WebSocket connections established
🚀 IWM Momentum System ONLINE
```

**On User's Phone (via Pushover):**
```
🤖 IWM System Alert
System started at HH:MM:SS ET
```

**If you see both:** ✅ **DEPLOYMENT SUCCESSFUL**

---

## ⚠️ IF SOMETHING BREAKS

### "Failed to authenticate WebSocket"
- Invalid Polygon API key
- Polygon plan insufficient (needs Starter+)
- **Fix:** Have user verify at polygon.io/dashboard

### "Configuration errors: POLYGON_API_KEY is required"
- Environment variable not set in Render
- **Fix:** Add env var in Render dashboard Environment tab

### "Pushover HTTP 400"
- Invalid Pushover credentials
- **Fix:** Have user verify token/user key

### Build fails
- Dependencies issue (unlikely, requirements.txt is complete)
- **Fix:** Check Render build logs for specific error

---

## 📊 WHAT THIS SYSTEM DOES

**IWM 0DTE CALLS MOMENTUM SYSTEM**

- Monitors IWM same-day expiry CALL options
- Uses a single momentum signal (price > VWAP, rising VWAP, volume surge, positive slope)
- Sends mobile alerts via Pushover when signal triggers and exits when momentum fades
- Tracks position with simple giveback/VWAP-based exits
- **ALERTS ONLY** - does not execute trades

**Active hours:** 9:30-16:00 ET (sleeps outside market hours)  
**Platform:** Render Background Worker (runs 24/7)  
**Cost:** ~$7/mo (Render) + $200/mo (Polygon) + $5 one-time (Pushover)

---

## 🚀 DEPLOYMENT COMMAND REFERENCE

### If Using Render MCP Tools (Preferred)

```
# 1. List workspaces
mcp_render_list_workspaces

# 2. Select workspace (if needed)
mcp_render_select_workspace(ownerID="...")

# 3. Create web service (Background Worker)
mcp_render_create_web_service(
  name="iwm-momentum-system",
  runtime="python",
  repo="https://github.com/rpriddy7-alt/IWMcallsONLY.git",
  branch="IWM-MAIN",
  buildCommand="pip install -r requirements.txt",
  startCommand="python main.py",
  envVars=[
    {"key": "POLYGON_API_KEY", "value": "<from user>"},
    {"key": "PUSHOVER_TOKEN", "value": "<from user>"},
    {"key": "PUSHOVER_USER_KEY", "value": "<from user>"}
  ],
  plan="standard",
  region="oregon"
)

# 4. Monitor deployment
mcp_render_list_deploys(serviceId="...")
mcp_render_list_logs(resource=["..."])
```

### If Guiding User Through Dashboard

1. Go to https://dashboard.render.com
2. Click "New" → "Background Worker"
3. Connect GitHub repository
4. Select repo: `rpriddy7-alt/IWMcallsONLY`
5. Select branch: `IWM-MAIN`
6. Render auto-detects `render.yaml`
7. Add environment variables (Settings → Environment)
8. Click "Create Background Worker"
9. Monitor deploy in Logs tab

---

## 📞 READY TO START?

1. ✅ Read this file
2. ✅ Verify GitHub push complete
3. ✅ Tell user you're ready for Render access
4. ✅ Get API credentials from user
5. ✅ Deploy to Render
6. ✅ Confirm system online

**Everything you need is in STATUS.md and DEPLOYMENT.md.**

**Let's deploy! 🚀**

