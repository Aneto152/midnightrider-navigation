# SECURITY & TOKEN MANAGEMENT

**Created:** 2026-04-26 20:57 EDT  
**Status:** Production-ready authentication strategy

---

## 🔐 TOKEN ARCHITECTURE

All sensitive credentials are stored **locally only** and **never committed to Git**.

```
.env.local (LOCAL ONLY, NOT IN GIT)
├── INFLUX_TOKEN
└── GRAFANA_TOKEN

.gitignore (PREVENTS ACCIDENTAL COMMITS)
├── .env
├── .env.local
└── *.key
```

---

## 📋 TOKENS IN USE

### 1. InfluxDB Token
- **Created:** 2026-04-26
- **Location:** `.env.local` → `INFLUX_TOKEN`
- **Scope:** Read/Write access to `midnight_rider` bucket
- **Used by:**
  - Grafana (read dashboards)
  - Signal K plugin (write sensor data)
  - Scripts and tools

**Token:** (stored in .env.local, not shown here)

### 2. Grafana Service Account Token
- **Created:** 2026-04-26
- **Type:** Service Account (API token, not password-based)
- **Location:** `.env.local` → `GRAFANA_TOKEN`
- **Scope:** Full API access (datasources, dashboards, alerts)
- **Used by:**
  - Automation scripts (configure datasources, import dashboards)
  - CI/CD pipelines (if automated)

**Token:** (stored in .env.local, not shown here)

---

## 🔑 HOW TO LOAD TOKENS IN SCRIPTS

All Python scripts should load tokens from `.env.local` like this:

```python
import os
from pathlib import Path

# Load from .env.local
def load_env_local():
    env_local = Path("/home/aneto/.openclaw/workspace/.env.local")
    config = {}
    with open(env_local, 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                config[key.strip()] = value.strip().strip('"')
    return config

config = load_env_local()
INFLUX_TOKEN = config.get("INFLUX_TOKEN")
GRAFANA_TOKEN = config.get("GRAFANA_TOKEN")
```

**Do NOT:**
- ❌ Hardcode tokens in scripts
- ❌ Store in environment variables (easily leaked)
- ❌ Commit to Git (even private repos)
- ❌ Put in Docker environment (visible in `docker inspect`)

**Do:**
- ✅ Load from `.env.local` at runtime
- ✅ Use API tokens (not passwords)
- ✅ Rotate tokens periodically
- ✅ Keep `.env.local` on local machine only

---

## 🚀 SETUP SCRIPTS

### `setup-grafana-influxdb.py`
**Purpose:** Configure Grafana InfluxDB datasource using tokens

**What it does:**
1. Loads tokens from `.env.local`
2. Authenticates with Grafana using `GRAFANA_TOKEN`
3. Creates/updates InfluxDB datasource
4. Tests connection
5. Reports status

**Run:**
```bash
cd /home/aneto/.openclaw/workspace
python3 setup-grafana-influxdb.py
```

**Output:**
```
✅ SETUP COMPLETE
📋 CONFIGURATION SUMMARY:
  • Grafana: http://localhost:3001
  • InfluxDB: http://localhost:8086/MidnightRider/midnight_rider
  • Datasource ID: 1
  • Status: Ready for dashboards
```

---

## 📊 DASHBOARD IMPORT WORKFLOW

### Option A: Automatic (via script)
```bash
python3 setup-grafana-influxdb.py  # Configure datasource
python3 import-dashboards.py        # Import 9 dashboards
```

### Option B: Manual (via Web UI)
1. Open http://localhost:3001
2. Login (password-based, different from token)
3. Admin → Data Sources
4. Create/Update InfluxDB datasource:
   - URL: `http://localhost:8086`
   - Organization: `MidnightRider`
   - Bucket: `midnight_rider`
   - Token: (paste from `.env.local`)
5. Dashboards → Import → Upload JSON
6. Select all 9 dashboard files

---

## 🔄 TOKEN ROTATION

### When to rotate:
- Every 90 days (recommended)
- After security incident
- If token is exposed
- After staff changes

### How to rotate:

**InfluxDB Token:**
1. Go to InfluxDB web UI (usually http://localhost:8086)
2. Admin → Tokens
3. Create new token (same permissions)
4. Update `.env.local` with new token
5. Test: `curl -H "Authorization: Token NEWTOKEN" http://localhost:8086/api/v2/orgs`
6. Delete old token

**Grafana Token:**
1. Go to Grafana → Admin → Service Accounts
2. Create new Service Account token
3. Update `.env.local` with new token
4. Test: `python3 setup-grafana-influxdb.py`
5. Delete old token

---

## 🛡️ SECURITY BEST PRACTICES

### 1. File Permissions
```bash
chmod 600 .env.local  # Owner read/write only
```

### 2. .gitignore Configuration
```
# Prevent accidental commits
.env
.env.local
.env.*.local
*.key
*.pem
secrets/
```

### 3. Never log tokens
```python
# BAD:
print(f"Token: {GRAFANA_TOKEN}")  # Visible in logs!

# GOOD:
print(f"Token: {GRAFANA_TOKEN[:20]}...***")  # Masked
```

### 4. Use short-lived tokens when possible
- InfluxDB: Use API tokens (expiring)
- Grafana: Use Service Account tokens (expiring)
- Don't use permanent password-based auth

### 5. Monitor token usage
- Check Grafana logs for API errors
- Watch InfluxDB query logs
- Set alerts on unusual activity

---

## 🚨 TROUBLESHOOTING

### "Token might be invalid or expired"

**Check:**
```bash
# 1. Token is in .env.local
grep GRAFANA_TOKEN .env.local
grep INFLUX_TOKEN .env.local

# 2. Token format is correct (no spaces)
cat .env.local | grep TOKEN | od -c | head

# 3. Service is running
curl http://localhost:3001/api/health
curl http://localhost:8086/health

# 4. Token permissions
# - For Grafana: Must have "org" scope at minimum
# - For InfluxDB: Must have read/write on bucket
```

### "Connection refused"
```bash
# Services not running?
docker ps | grep -E "grafana|influx"
docker compose up -d grafana influxdb
```

### "Unauthorized" but token looks correct
- Token might have been revoked on server
- Token permissions changed
- Create a new token and test

---

## 📚 REFERENCE

**Files involved:**
- `.env.local` — Token storage (gitignored)
- `.gitignore` — Prevents accidental commits
- `setup-grafana-influxdb.py` — Configuration script
- `import-dashboards.py` — Dashboard import script
- `configure-grafana-influx.py` — Legacy (use setup-*.py instead)

**Locations:**
- InfluxDB: http://localhost:8086
- Grafana: http://localhost:3001
- Workspace: `/home/aneto/.openclaw/workspace`

---

## ✅ DEPLOYMENT CHECKLIST

- [ ] `.env.local` created with both tokens
- [ ] `.env.local` has correct file permissions (600)
- [ ] `.gitignore` includes `.env.local`
- [ ] Verified `.env.local` is not in Git
- [ ] Tested token authentication
- [ ] Ran `setup-grafana-influxdb.py` successfully
- [ ] Datasource configured in Grafana
- [ ] Dashboards imported
- [ ] Field test (May 19) — verify live data
- [ ] Race day (May 22) — production deployment

---

**Status:** ✅ Security infrastructure ready  
**Last Updated:** 2026-04-26 20:57 EDT  
**Token Rotation:** Every 90 days
