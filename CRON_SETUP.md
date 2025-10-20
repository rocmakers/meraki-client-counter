# Cron Job Setup for Automated Collection

## Overview

Run the Meraki client counter daily to build up historical data in the SQLite database. Over time, you'll accumulate enough data for true 52-week and 12-month trend analysis.

## Recommended Cron Schedule

### Daily Data Collection (12:01 AM)

```bash
1 0 * * * /Users/eric/Projects/RMS/avgdevs/run_collection.sh >> /var/log/meraki_collection.log 2>&1
```

This will:
- Run every day at 12:01 AM
- Collect last 30 days from Meraki API
- Store new client records in database (duplicates automatically skipped)
- Log output to `/var/log/meraki_collection.log`

### Optional: Weekly Chart Generation (Sundays at 12:10 AM)

```bash
10 0 * * 0 /Users/eric/Projects/RMS/avgdevs/run_charts.sh >> /var/log/meraki_charts.log 2>&1
```

This will:
- Run every Sunday at 12:10 AM
- Generate charts from ALL historical data in database
- Create weekly_clients_chart.png and monthly_clients_chart.png
- As database grows, charts will show more history (up to 52 weeks / 12 months)

## Setup Instructions

### 1. Edit your crontab

```bash
crontab -e
```

### 2. Add the cron entries

Paste one or both of the cron lines above (adjust log paths if needed).

### 3. Save and exit

The cron daemon will automatically pick up the changes.

## Verify Cron Jobs

```bash
# List your cron jobs
crontab -l

# Check if cron ran (on macOS)
grep CRON /var/log/system.log

# View collection log
tail -f /var/log/meraki_collection.log
```

## Database Growth Over Time

| Time Period | Database Records | Historical Analysis Available |
|-------------|------------------|-------------------------------|
| Week 1      | ~600 records     | 1 month of data               |
| Month 1     | ~600 records     | 1 month of data               |
| Month 3     | ~1,800 records   | 3 months of data              |
| Month 6     | ~3,600 records   | 6 months of data              |
| Year 1      | ~7,200 records   | Full 52 weeks + 12 months!    |

**Note**: Actual record count depends on your client turnover rate.

## Manual Operations

### Run Collection Manually

```bash
cd /Users/eric/Projects/RMS/avgdevs
./run_collection.sh
```

### Generate Charts Manually

```bash
cd /Users/eric/Projects/RMS/avgdevs
./run_charts.sh
```

### View Database Stats

```bash
cd /Users/eric/Projects/RMS/avgdevs
source venv/bin/activate
python main.py --db-stats
```

### View Results with Historical Data

```bash
cd /Users/eric/Projects/RMS/avgdevs
source venv/bin/activate
python main.py --use-historical --show-mac-analysis
```

## Troubleshooting

### Cron Job Not Running?

1. **Check cron is enabled** (macOS):
   ```bash
   sudo launchctl list | grep cron
   ```

2. **Grant Full Disk Access** (macOS Catalina+):
   - System Preferences → Security & Privacy → Privacy
   - Select "Full Disk Access"
   - Add `/usr/sbin/cron`

3. **Check permissions**:
   ```bash
   ls -la /Users/eric/Projects/RMS/avgdevs/run_collection.sh
   # Should show: -rwxr-xr-x (executable)
   ```

### Database Issues?

```bash
# Check database exists and has data
ls -lh /Users/eric/Projects/RMS/avgdevs/client_history.db

# View database stats
cd /Users/eric/Projects/RMS/avgdevs
source venv/bin/activate
python main.py --db-stats
```

### Log Files Not Created?

Make sure the log directory is writable:

```bash
# Option 1: Use a directory you own
1 0 * * * /Users/eric/Projects/RMS/avgdevs/run_collection.sh >> /Users/eric/meraki_collection.log 2>&1

# Option 2: Use the project directory
1 0 * * * /Users/eric/Projects/RMS/avgdevs/run_collection.sh >> /Users/eric/Projects/RMS/avgdevs/collection.log 2>&1
```

## Alternative: Using launchd (macOS Preferred)

On macOS, `launchd` is more reliable than cron. If you want to use launchd instead, let me know and I can create a `.plist` file for you.

## Database Backup

Consider backing up your database regularly:

```bash
# Add to weekly cron (Sundays at 1 AM)
0 1 * * 0 cp /Users/eric/Projects/RMS/avgdevs/client_history.db /Users/eric/Projects/RMS/avgdevs/backups/client_history_$(date +\%Y\%m\%d).db
```

Create the backups directory first:
```bash
mkdir -p /Users/eric/Projects/RMS/avgdevs/backups
```
