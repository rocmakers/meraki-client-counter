# Meraki Average Client Device Counter

A Python application that queries the Cisco Meraki Dashboard API to calculate and report average unique client counts per day, week, and month for a specified organization.

## Features

- **Dual Tracking**: Counts both unique MAC addresses and unique IP addresses
- **MAC Randomization Detection**: Identifies and quantifies the impact of MAC randomization on client counts
- **Time Period Averages**: Calculates averages for daily, weekly (Sunday-Saturday), and monthly periods
- **Historical Data Storage**: SQLite database stores all client data for long-term trend analysis
- **Automated Collection**: Run daily via cron to build up 52 weeks / 12 months of historical data
- **Chart Generation**: Creates beautiful PNG charts showing trends over time
- **Multiple Output Formats**: Console, JSON, and CSV output options
- **Simple Configuration**: Interactive setup on first run with credential storage
- **Connection Type Breakdown**: Separate counts for wireless and wired clients

## Installation

1. Clone or download this repository
2. Create a virtual environment (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

### First-Time Setup

On first run, the application will prompt you for:
- **Meraki API Key**: Your Dashboard API key (get it from Meraki Dashboard → Organization → Settings → Dashboard API access)
- **Organization ID**: Your Meraki organization ID

Credentials are saved to `.meraki_config.json` (automatically added to `.gitignore`).

### Reconfiguration

To update your credentials:
```bash
python main.py --reconfigure
```

## Usage

### Basic Usage

Run with default settings (all time periods):
```bash
python main.py
```

### Command-Line Options

```bash
# Show only daily averages
python main.py --period daily

# Show only weekly averages
python main.py --period weekly

# Show only monthly averages
python main.py --period monthly

# Save results as JSON
python main.py --output json --file results.json

# Save results as CSV
python main.py --output csv --file results.csv

# Show detailed MAC randomization analysis
python main.py --show-mac-analysis

# Enable verbose logging
python main.py --verbose

# Customize sampling periods
python main.py --days 14 --weeks 8 --months 6
```

### Full Command-Line Reference

```
options:
  -h, --help            Show this help message and exit
  --reconfigure         Reconfigure API credentials
  --period {daily,weekly,monthly,all}
                        Time period to calculate (default: all)
  --output {console,json,csv}
                        Output format (default: console)
  -f FILE, --file FILE  Output file path (required for json/csv output)
  --show-mac-analysis   Show detailed MAC randomization analysis
  --verbose             Enable verbose logging
  --days DAYS           Number of days to sample for daily average (default: 7)
  --weeks WEEKS         Number of weeks to sample for weekly average (default: 4)
  --months MONTHS       Number of months to sample for monthly average (default: 3)
  --generate-charts     Generate chart visualizations (PNG files)
  --chart-weeks WEEKS   Number of weeks to include in weekly chart (default: 52)
  --chart-months MONTHS Number of months to include in monthly chart (default: 12)
  --use-historical      Use historical data from database instead of just API data
  --db-stats            Show database statistics and exit
```

### Database and Historical Data

The application automatically stores all collected client data in a SQLite database (`client_history.db`). This enables:

1. **Building Historical Trends**: Run daily to accumulate data over time
2. **True 52-Week / 12-Month Analysis**: After a year, you'll have complete historical data
3. **Duplicate Prevention**: Same client records are not stored twice
4. **Fast Queries**: Use `--use-historical` to analyze all stored data

**View Database Stats:**
```bash
python main.py --db-stats
```

**Generate Charts from Historical Data:**
```bash
python main.py --use-historical --generate-charts --weeks 52 --months 12
```

## Understanding the Output

### Client Counts

The application tracks two key metrics:

1. **Unique MAC Addresses**: Total unique MAC addresses seen (may be inflated by MAC randomization)
2. **Unique IP Addresses**: Total unique IP addresses seen (generally more accurate for device count)

### MAC Randomization Analysis

Modern iOS (14+) and Android (10+) devices use MAC randomization, which can inflate client counts:

- **MAC/IP Ratio ~1.0**: Minimal MAC randomization impact
- **MAC/IP Ratio 1.2-1.5**: Moderate MAC randomization
- **MAC/IP Ratio >1.5**: Significant MAC randomization impact

**Example:**
```
Average Unique MAC Addresses: 180
Average Unique IP Addresses: 100
MAC/IP Ratio: 1.8:1
```

This suggests ~80 "extra" MAC addresses due to randomization. The IP count (100) is likely closer to the actual number of unique devices.

### Important Limitations

**MAC Address Counting:**
- iOS devices may appear as multiple clients if connecting to multiple SSIDs
- Android devices with non-persistent randomization may appear as new clients on each connection
- Same physical device = multiple MAC addresses across different SSIDs

**IP Address Counting:**
- Multiple devices may share one IP (NAT environments)
- Same device may get different IPs over time (DHCP lease changes)
- VPN/Proxy configurations may affect IP visibility

**Recommendation**: Use IP count as a "lower bound" estimate of unique physical devices in most enterprise environments.

### Week Definition

Weeks run **Sunday through Saturday**. If you run the application on a Wednesday, it will count complete weeks ending on the previous Saturday.

## Example Output

```
================================================================================
Meraki Average Client Device Counter - Results
================================================================================

Organization: Acme Corporation
Organization ID: 123456
Timestamp: 2025-01-20T15:30:00Z
Client Tracking Method: MAC address

Daily Averages:
----------------------------------------
  Average Unique MAC Addresses:  156.43
  Average Unique IP Addresses:   98.71
  Average Wireless Clients:      142.86
  Average Wired Clients:         13.57
  Days Sampled:                  7

Weekly Averages (Sunday-Saturday):
----------------------------------------
  Average Unique MAC Addresses:  542.50
  Average Unique IP Addresses:   312.25
  Average Wireless Clients:      498.75
  Average Wired Clients:         43.75
  Weeks Sampled:                 4

Monthly Averages:
----------------------------------------
  Average Unique MAC Addresses:  2134.67
  Average Unique IP Addresses:   1245.33
  Average Wireless Clients:      1956.33
  Average Wired Clients:         178.33
  Months Sampled:                3

Warnings:
----------------------------------------
  ⚠ MAC randomization detected: 38.5% of MAC addresses appear randomized
  ⚠ MAC/IP ratio is 1.58:1, suggesting MAC randomization is inflating counts
  ⚠ Unique IP count may be more accurate for estimating physical device count

================================================================================
```

## API Rate Limiting

The Meraki API has a rate limit of **10 calls per second per organization**. This application automatically handles rate limiting with:
- Built-in delays between requests
- Exponential backoff for 429 (rate limited) responses
- Retry logic for failed requests

## Automated Data Collection (Cron Setup)

For long-term trend analysis, run this tool daily to build up historical data:

### Quick Setup

```bash
# Daily collection at 12:01 AM
crontab -e

# Add this line:
1 0 * * * /Users/eric/Projects/RMS/avgdevs/run_collection.sh >> /Users/eric/meraki_collection.log 2>&1
```

### What This Does

- Collects last 30 days from Meraki API every night
- Stores new records in SQLite database
- Automatically skips duplicates
- Over time, builds up **52 weeks** and **12 months** of data
- Charts will show more history as data accumulates

**See [CRON_SETUP.md](CRON_SETUP.md) for detailed instructions and troubleshooting.**

## File Structure

```
avgdevs/
├── .meraki_config.json       # Config file (gitignored, created on first run)
├── .gitignore                # Git ignore file
├── client_history.db         # SQLite database (gitignored)
├── main.py                   # Entry point
├── config.py                 # Configuration management
├── meraki_client.py          # API client wrapper
├── data_processor.py         # Data aggregation and averaging
├── database.py               # SQLite database management
├── charts.py                 # Chart generation
├── output.py                 # Output formatting
├── run_collection.sh         # Shell script for cron (daily collection)
├── run_charts.sh             # Shell script for chart generation
├── requirements.txt          # Python dependencies
├── README.md                 # This file
├── CRON_SETUP.md             # Cron job setup guide
└── CLAUDE.md                 # Architecture documentation
```

## Troubleshooting

### "Failed to retrieve organization information"
- Verify your API key is correct
- Ensure your API key has read access to the organization
- Check that the Organization ID is correct

### "No client data retrieved"
- The organization may not have any clients in the time period
- Check network connectivity
- Verify API permissions

### Rate Limiting Errors
- The application handles this automatically
- If persistent, reduce the number of days/weeks/months sampled

### MAC Randomization Warning
- This is expected behavior for modern iOS/Android devices
- Use IP count as a more accurate estimate
- Consider reviewing SSID configurations to disable MAC randomization if needed

## Requirements

- Python 3.7 or higher
- `requests` library (installed via requirements.txt)
- Meraki Dashboard API key with read access
- Organization ID

## Contributing

This project is documented in `CLAUDE.md` with detailed architecture information, API research, and implementation decisions.

## License

This project is provided as-is for educational and operational purposes.

## Support

For Meraki API documentation, visit:
- [Meraki Dashboard API Documentation](https://developer.cisco.com/meraki/api-v1/)
- [Get Organization Clients Search](https://developer.cisco.com/meraki/api-v1/get-organization-clients-search/)
