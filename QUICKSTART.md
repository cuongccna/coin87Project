# Coin87 Data Ingestion - Quick Start Guide

## 🚀 Setup & Installation

### Prerequisites
- Python 3.10+
- PostgreSQL 14+
- Redis 7+
- Reddit API credentials (free)

---

## Step 1: Install Dependencies

```bash
cd backend

# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Windows CMD:
.\venv\Scripts\activate.bat
# Linux/Mac:
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

**New dependencies added:**
- `praw==7.7.1` - Reddit API wrapper

---

## Step 2: Configure Environment Variables

Edit `.env` file in project root:

```bash
# Database (existing)
DATABASE_URL=postgresql+psycopg2://coin87_user:Cuongnv123456@localhost:5432/coin87_db

# Reddit API (NEW - Required for Reddit ingestion)
REDDIT_CLIENT_ID=your_client_id_here
REDDIT_CLIENT_SECRET=your_client_secret_here
REDDIT_USER_AGENT=coin87:v1.0 (by /u/coin87bot)

# Proxy (OPTIONAL - Only if you need proxy rotation)
# C87_PROXY_URL=http://proxy1.example.com:8080,http://proxy2.example.com:8080
```

### How to Get Reddit API Credentials (Free) 🆓

1. Go to https://www.reddit.com/prefs/apps
2. Click "Create App" or "Create Another App"
3. Fill in:
   - **Name:** Coin87
   - **Type:** Select "script"
   - **Description:** Crypto news aggregator
   - **About URL:** (leave blank)
   - **Redirect URI:** http://localhost:8080 (required but not used)
4. Click "Create app"
5. Copy credentials:
   - **REDDIT_CLIENT_ID:** The string under "personal use script"
   - **REDDIT_CLIENT_SECRET:** The "secret" field

**Rate limits (free tier):**
- 60 requests per minute
- No cost, no credit card required

---

## Step 3: Configure Data Sources

Review and customize `backend/ingestion/config/sources.yaml`:

```yaml
# Currently enabled sources (11 total):
# RSS Feeds:
#   - CoinDesk, Cointelegraph, The Block, Decrypt, Bitcoin Magazine
#   - CryptoPanic, CoinGape, NewsBTC
# Reddit:
#   - r/cryptocurrency, r/bitcoin, r/ethereum
# GitHub:
#   - Bitcoin Core releases, Ethereum releases

# To enable more sources, change enabled: false → true
```

**Recommended for MVP:**
- Keep all `enabled: true` sources active
- Start with `rate_limit_seconds` as configured (20-120s)
- Enable proxy only if you get 403/429 errors

---

## Step 4: Test Database Connection

```bash
cd backend

# Test PostgreSQL connection
python -c "from app.core.db import SessionLocal; db = SessionLocal(); print('✅ Database connected'); db.close()"

# Expected output: "✅ Database connected"
```

---

## Step 5: Run Ingestion (First Time)

```bash
cd backend

# Run ingestion job
python ingestion/jobs/run_ingestion.py
```

**Expected output:**
```json
{
  "started_at": "2026-01-29T...",
  "finished_at": "2026-01-29T...",
  "duration_seconds": 45.2,
  "sources_processed": 11,
  "items_fetched": 287,
  "items_inserted": 245,
  "items_deduped": 42,
  "errors": 0
}
```

**First run typically takes 45-90 seconds** (fetches all enabled sources)

---

## Step 6: Verify Data

```bash
# Connect to PostgreSQL
psql $DATABASE_URL

# Check ingested data
SELECT 
    source_ref,
    COUNT(*) as count,
    MAX(observed_at) as last_updated
FROM information_events
GROUP BY source_ref
ORDER BY count DESC;
```

**Expected results:**
```
      source_ref      | count |       last_updated
----------------------+-------+------------------------
 CoinDesk             |    42 | 2026-01-29 10:30:15+00
 r/cryptocurrency     |    25 | 2026-01-29 10:30:22+00
 Cointelegraph        |    38 | 2026-01-29 10:30:18+00
 r/bitcoin            |    20 | 2026-01-29 10:30:25+00
 ...
```

---

## Step 7: Schedule Periodic Ingestion

### Option A: Windows Task Scheduler

```powershell
# Run every 30 minutes
$action = New-ScheduledTaskAction -Execute "python" -Argument "D:\projects\coin87\coin87Project\backend\ingestion\jobs\run_ingestion.py" -WorkingDirectory "D:\projects\coin87\coin87Project\backend"

$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 30) -RepetitionDuration ([TimeSpan]::MaxValue)

Register-ScheduledTask -TaskName "Coin87Ingestion" -Action $action -Trigger $trigger -Description "Coin87 data ingestion job"
```

### Option B: Linux/Mac Cron

```bash
# Edit crontab
crontab -e

# Add this line (runs every 30 minutes)
*/30 * * * * cd /path/to/coin87Project/backend && /path/to/venv/bin/python ingestion/jobs/run_ingestion.py >> /var/log/coin87_ingestion.log 2>&1
```

### Option C: Docker Compose (Recommended for Production)

See `docker-compose.yml` example in [DATA_INGESTION_REVIEW.md](DATA_INGESTION_REVIEW.md#8-deployment--devops)

---

## 🔍 Troubleshooting

### Issue: "praw not found"
```bash
# Solution: Install PRAW
pip install praw==7.7.1
```

### Issue: "REDDIT_CLIENT_ID not set"
```bash
# Solution: Check .env file has Reddit credentials
# Make sure .env is in project root (same level as backend/)
# Verify credentials are not commented out with #
```

### Issue: "403 Forbidden" errors
```bash
# Solution 1: Increase rate_limit_seconds in sources.yaml
# Change from 20 → 60 or higher

# Solution 2: Enable proxy
# Uncomment and set C87_PROXY_URL in .env
C87_PROXY_URL=http://your-proxy:8080
```

### Issue: "No data fetched"
```bash
# Solution: Check source enabled status
# Edit backend/ingestion/config/sources.yaml
# Ensure enabled: true for desired sources

# Verify network connectivity
curl https://www.coindesk.com/arc/outboundfeeds/rss/
```

### Issue: Reddit "invalid_grant" error
```bash
# Solution: Verify Reddit app type is "script"
# Re-create app at https://www.reddit.com/prefs/apps
# Ensure Type: "script" is selected
```

---

## 📊 Monitoring

### Check Ingestion Logs

```bash
# View recent ingestion runs
tail -f /var/log/coin87_ingestion.log

# Or if running manually
python ingestion/jobs/run_ingestion.py 2>&1 | tee ingestion.log
```

### Monitor Source Health

```sql
-- Check which sources are active
SELECT 
    source_ref,
    COUNT(*) as total_items,
    MAX(observed_at) as last_ingestion,
    AGE(NOW(), MAX(observed_at)) as time_since_last
FROM information_events
GROUP BY source_ref
ORDER BY last_ingestion DESC;
```

### Check Error Rates

```sql
-- Monitor for ingestion errors (check application logs)
-- Future: Add error tracking table for structured monitoring
```

---

## 🎯 Performance Tuning

### Optimize for Speed (Lower Latency)
```yaml
# In sources.yaml, reduce rate_limit_seconds
# WARNING: May increase risk of 403/429 errors
rate_limit_seconds: 10  # Instead of 20-30
```

### Optimize for Reliability (Avoid Bans)
```yaml
# In sources.yaml, increase rate_limit_seconds
rate_limit_seconds: 60  # Or higher
proxy: true             # Enable proxy if available
priority: low           # Lower priority = more conservative
```

### Optimize for Coverage (More Data)
```yaml
# Enable all sources in sources.yaml
# Set enabled: true for disabled sources
blockonomi_rss:
  enabled: true  # Was false
cryptoslate_rss:
  enabled: true  # Was false
```

---

## 🚀 Next Steps After Setup

1. **Run ingestion for 24 hours** to verify stability
2. **Monitor for 403/429 errors** in logs
3. **Adjust rate_limit_seconds** based on results
4. **Enable additional sources** if needed
5. **Implement monitoring** (Prometheus + Grafana)

### Recommended Monitoring Setup (Week 2)

```bash
# Install monitoring dependencies
pip install prometheus-client

# Add metrics to ingestion job
# See DATA_INGESTION_REVIEW.md section 6.3 for examples
```

---

## 📚 Additional Resources

- **Technical Review:** [DATA_INGESTION_REVIEW.md](DATA_INGESTION_REVIEW.md)
- **TimescaleDB Migration:** [TIMESERIES_MIGRATION.md](TIMESERIES_MIGRATION.md)
- **Implementation Summary:** [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
- **Architecture Overview:** [ARCHITECTURE.md](ARCHITECTURE.md)

---

## ❓ FAQ

**Q: How often should I run ingestion?**  
A: For MVP: Every 30-60 minutes. For production: Every 15-30 minutes.

**Q: Do I need proxies?**  
A: Not initially. Only enable if you get 403/429 errors frequently.

**Q: How much data will be collected?**  
A: Approximately 300-500 items per run (varies by source availability).

**Q: Can I add custom sources?**  
A: Yes! Add to `sources.yaml` and create adapter if needed. See `rss_adapter.py` for example.

**Q: Is Reddit API really free?**  
A: Yes, 60 requests/min with no cost. Perfect for our use case (4 subreddits × 1 req/2min = well within limits).

**Q: What if a source goes down?**  
A: Ingestion continues for other sources. Failed source gets exponential backoff (1min → 2min → 4min → ...).

**Q: How do I add more Reddit subreddits?**  
A: Add new entry in `sources.yaml`:
```yaml
reddit_newsubreddit:
  enabled: true
  type: reddit
  name: r/NewSubreddit
  url: reddit://r/newsubreddit?limit=20&sort=hot
  rate_limit_seconds: 120
  proxy: false
  priority: medium
```

---

## ✅ Checklist

- [ ] Python 3.10+ installed
- [ ] PostgreSQL running and accessible
- [ ] Redis running (for future use)
- [ ] Virtual environment created
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file configured with Reddit credentials
- [ ] Database connection tested
- [ ] First ingestion run successful
- [ ] Data verified in `information_events` table
- [ ] Periodic scheduling configured (cron/Task Scheduler)
- [ ] Monitoring plan in place

---

**Ready to run? Execute:**
```bash
cd backend
python ingestion/jobs/run_ingestion.py
```

**Happy ingesting! 🎉**
