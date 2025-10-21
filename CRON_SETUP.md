# Cron Job Setup for Automated Collection

## Overview

Run the Meraki client counter **hourly** to build up historical data in the SQLite database. Over time, you'll accumulate enough data for true 52-week and 12-month trend analysis, plus hourly graphs and peak hours detection.

## Recommended Cron Schedule

### Hourly Data Collection

```bash
0 * * * * /Users/eric/Projects/RMS/avgdevs/run_collection.sh >> /var/log/meraki_collection.log 2>&1
```

This will:
- Run every hour on the hour
- **Smart Collection**: Only fetches data since last run + 1.5-hour buffer (minimum)
- **First Run**: Collects 30 days of initial historical data
- **Auto-Recovery**: If server/internet down, automatically catches up on next run
- Store new client records in database (duplicates automatically skipped)
- Log output to `/var/log/meraki_collection.log`
- Enables hourly graphs and peak hours analysis

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

### 4. Ensure cron starts on boot

**On macOS:**
Cron is managed by launchd and starts automatically. No additional setup needed.

**On Linux (systemd):**
```bash
# Enable cron to start on boot
sudo systemctl enable cron

# Start cron now
sudo systemctl start cron

# Check status
sudo systemctl status cron
```

**On older Linux (SysV init):**
```bash
# Check if cron is enabled
sudo chkconfig --list crond

# Enable cron to start on boot
sudo chkconfig crond on

# Start cron now
sudo service crond start
```

## Verify Cron Jobs

```bash
# List your cron jobs
crontab -l

# Check if cron ran (on macOS)
grep CRON /var/log/system.log

# View collection log
tail -f /var/log/meraki_collection.log
```

## How Smart Collection Works

The application uses **timestamp-based collection** for maximum efficiency:

1. **First Run**: Fetches 30 days of data to build initial baseline
2. **Subsequent Runs**: Queries database for most recent client timestamp
3. **Calculates Range**: Fetches from (last_timestamp - 1.5 hours) to now
4. **Minimum Window**: Always fetches at least 1.5 hours (even if last run was recent)
5. **Adapts Automatically**:
   - Hourly cron → fetches ~1.5 hours
   - Missed a few hours → automatically catches up
   - Server down for a day → fetches all missing data on recovery

**Result**: Minimal API calls while ensuring no data gaps and enabling hourly analysis!

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
