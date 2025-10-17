# Vellum AI Integration Setup

## 🔑 GitHub Secret Configuration

**IMPORTANT:** Add this secret to your GitHub repository NOW:

### Quick Setup Link:
**[CLICK HERE TO ADD SECRET](https://github.com/rpriddy7-alt/IWMcallsONLY/settings/secrets/actions/new)**

### Secret Details:
- **Name:** `GIT`  
- **Value:** `pr_C61vs7YHkRTi`

## ✅ One-Click Setup Instructions

1. **Click the link above** or go to:
   ```
   https://github.com/rpriddy7-alt/IWMcallsONLY/settings/secrets/actions/new
   ```

2. **Fill in the fields:**
   - Name: `GIT`
   - Value: `pr_C61vs7YHkRTi`

3. **Click "Add secret"**

## 🚀 That's It!

Once you add this secret, Vellum will be able to:
- Connect to your repository
- Access your IWM momentum trading system code
- Integrate with your workflow

## 📝 Verification

After adding the secret, you can verify it at:
```
https://github.com/rpriddy7-alt/IWMcallsONLY/settings/secrets/actions
```

You should see `GIT` listed under "Repository secrets".

## 🔧 Alternative: Command Line Setup

If you have GitHub CLI installed:
```bash
gh secret set GIT --body "pr_C61vs7YHkRTi" --repo rpriddy7-alt/IWMcallsONLY
```

Or use the provided script with a GitHub token:
```bash
GITHUB_TOKEN=<your-token> python3 vellum_secret.py
```

---

**Status:** ⏳ Waiting for secret to be added to repository
