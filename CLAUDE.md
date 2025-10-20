# Meraki Average Client Device Counter

## Project Overview

A Python application that queries the Cisco Meraki Dashboard API to calculate and report average client counts per day, week, and month for a specified organization.

## Purpose

Track **unique** client device trends across a Meraki organization to understand:
- Average number of unique clients per day (unique MAC addresses seen each day)
- Average number of unique clients per week (unique MAC addresses seen each week)
- Average number of unique clients per month (unique MAC addresses seen each month)

**Important**: Clients are counted as unique per time period. A client that connects multiple times within a day is counted only once for that day's average.

This helps with capacity planning, trend analysis, and understanding network utilization patterns.

## Architecture & Design

### API Strategy

The application will use the Meraki Dashboard API v1 with the following endpoints:

1. **Primary Client Data Collection**:
   - `GET /organizations/{organizationId}/clients/search` - Search all clients across organization
   - `GET /networks/{networkId}/clients` - Get clients per network with connection type details

2. **Historical Client Counts** (if available):
   - `GET /networks/{networkId}/wireless/clientCountHistory` - Historical wireless client counts

### Client Counting Logic

**Important Note on Wireless vs Wired Clients:**

Clients are identified by their MAC address in the Meraki system. A single client device will NOT appear as both a wireless client and a wired client simultaneously. The API provides a `recentDeviceConnection` field (enum: "Wired" or "Wireless") that indicates the client's most recent connection type.

**Implications:**
- No deduplication needed between wireless and wired clients
- A client switching from wireless to wired will update its `recentDeviceConnection` field
- Total client count = unique MAC addresses seen in the time period
- Can optionally break down counts by connection type using `recentDeviceConnection`

### CRITICAL: MAC Address Randomization Impact

**The Challenge:**

Modern iOS (iOS 14+) and Android (Android 10+) devices implement MAC address randomization, which significantly impacts client counting:

**iOS 14+ Behavior:**
- Each SSID gets a **distinct randomized MAC address per device**
- The randomized MAC is **persistent for that SSID** (doesn't change on reconnect)
- Different SSIDs = different randomized MACs for the same physical device
- "Forgetting" the network and rejoining uses the same randomized MAC

**Android 10+ Behavior:**
- Can enable **non-persistent MAC randomization** globally
- Device may present a different MAC address each time it connects
- More problematic for tracking than iOS (changes over time)

**Impact on Client Counts:**

1. **Inflated Counts**:
   - iOS devices may appear as multiple "different" clients if connecting to multiple SSIDs
   - Android devices with non-persistent randomization will appear as new clients on each connection
   - Historical data may show artificially inflated client counts

2. **Dashboard Filtering Behavior**:
   - **Location Analytics and Scanning API v2**: Meraki filters out randomized MACs for "Passerby" and "Visitor" analytics (requires non-randomized MAC for >1 minute to be classified)
   - **Connected Clients**: Randomized MACs ARE shown in connected client lists (both Dashboard and API)
   - **Important**: When a device connects with MAC randomization, that randomized MAC is what gets tracked - there's no way to retrieve the actual hardware MAC address
   - The filtering primarily affects **Location Analytics/scanning data**, not active client connections

3. **DHCP Pool Exhaustion**:
   - Randomized MACs can cause DHCP pool exhaustion
   - Each "new" MAC gets a new DHCP lease

**Mitigation Strategies:**

1. **Focus on Connected Clients** (NOT scanning/probing data):
   - Query **actively connected** clients only via `/networks/{networkId}/clients` or `/organizations/{organizationId}/clients/search`
   - **Important**: Connected clients WILL include randomized MACs if the device uses MAC randomization
   - The randomized MAC is what gets reported - there's no API field for the actual hardware MAC
   - This approach is still better than Location Analytics data, but won't solve the MAC randomization problem

2. **Network Configuration**:
   - Check if organization uses "Unique Client Identifier" tracking method
   - This Meraki feature correlates MAC + IP across the network stack
   - Available only with MX + MS L3 switches (requires MX 9+, MS 10+)
   - API endpoint: `GET /networks/{networkId}/wireless/settings` (check `clientTracking` field)

3. **Authentication-Based Counting**:
   - If SSIDs use authentication (802.1X, captive portal), consider user-based counting
   - More reliable than MAC-based counting for authenticated networks

4. **Document Limitations**:
   - Clearly state in output that counts may be affected by MAC randomization
   - Note that counts represent "unique MAC addresses seen" not necessarily "unique physical devices"
   - Recommend reviewing SSID configurations and client tracking settings

**Critical Clarification - Dashboard UI vs API:**

Based on research, the statement "Dashboard filters out randomized MAC addresses" applies primarily to:
- **Location Analytics** (Passerby/Visitor tracking)
- **Scanning API v2** output

For **connected clients** (the data this application will use):
- Both Dashboard UI and API show clients with their randomized MAC addresses
- There is **NO filtering or substitution** - you see the randomized MAC
- There is **NO way to retrieve the actual hardware MAC address** via API
- Dashboard and API should show the same MAC addresses for connected clients

**Does Meraki track by IP instead?**
- The "Unique Client Identifier" feature (available with MX + MS switches) correlates MAC + IP addresses across the network
- This helps with identifying clients across L3 boundaries
- However, it does NOT solve the MAC randomization problem for unique device counting
- It's designed for policy application, not for identifying the same physical device with different randomized MACs

**Bottom Line for This Application:**
- Your client counts WILL be affected by MAC randomization
- There is no API workaround to get "true" unique device counts
- The counts represent "unique MAC addresses seen" not "unique physical devices"
- This is a **fundamental limitation** that must be documented in the output

**Recommendations for Implementation:**

1. Query the network's client tracking method via API
2. Always add warning about MAC randomization impact in output
3. Focus on **connected** clients (not Location Analytics data)
4. Document clearly: "Counts represent unique MAC addresses, not unique physical devices"
5. Consider detecting randomized MACs by checking locally administered bit (2nd hex char = 2, 6, A, or E)
6. Optionally report what percentage of MACs appear to be randomized
7. Include this disclaimer in ALL output formats (console, JSON, CSV)

### Time Period Handling

The Meraki API supports time-based queries with:
- `timespan` parameter (in seconds, max 2,678,400 = 31 days)
- `t0` and `t1` parameters (start and end timestamps)

**Calculation Approach for Unique Clients:**

1. **Daily Average**:
   - Query the last 7 complete days (or more for better average)
   - For each calendar day, collect all clients seen that day
   - Count unique **MAC addresses** per day
   - Count unique **IP addresses** per day
   - Detect randomized MACs (check locally administered bit)
   - Calculate averages:
     - `sum(unique_macs_per_day) / number_of_days`
     - `sum(unique_ips_per_day) / number_of_days`

2. **Weekly Average**:
   - **Week Definition**: Sunday through Saturday (week starts on Sunday)
   - Query the last 4 complete weeks
   - Group clients by calendar week (Sunday-Saturday)
   - For each week, count unique MAC addresses and unique IP addresses
   - Calculate averages:
     - `sum(unique_macs_per_week) / number_of_weeks`
     - `sum(unique_ips_per_week) / number_of_weeks`
   - Example: If run on Wednesday, count complete weeks ending on previous Saturday

3. **Monthly Average**:
   - Query the last 3-6 complete months (may require multiple API calls due to 31-day limit)
   - Group clients by calendar month (1st - last day of month)
   - For each month, count unique MAC addresses and unique IP addresses
   - Calculate averages:
     - `sum(unique_macs_per_month) / number_of_months`
     - `sum(unique_ips_per_month) / number_of_months`

**Note**:
- A client that appears multiple times within a single time period (day/week/month) is counted only once for that period
- Time periods are based on **calendar boundaries** (days, Sunday-Saturday weeks, calendar months), not rolling windows
- **Both MAC and IP counts are tracked** to help identify MAC randomization impact
- If MAC count significantly exceeds IP count, MAC randomization is likely inflating the numbers

### Data Structure

```python
{
    "organization_id": "string",
    "organization_name": "string",
    "timestamp": "ISO 8601 timestamp",
    "client_tracking_method": "MAC address" or "Unique client identifier",
    "mac_randomization_warning": bool,  # True if MAC-only tracking detected
    "averages": {
        "daily": {
            "avg_unique_mac_addresses": float,  # Average unique MAC addresses per day
            "avg_unique_ip_addresses": float,   # Average unique IP addresses per day
            "avg_wireless_clients": float,
            "avg_wired_clients": float,
            "avg_randomized_macs": float,       # Average randomized MACs detected per day
            "days_sampled": int
        },
        "weekly": {
            "avg_unique_mac_addresses": float,  # Average unique MAC addresses per week
            "avg_unique_ip_addresses": float,   # Average unique IP addresses per week
            "avg_wireless_clients": float,
            "avg_wired_clients": float,
            "avg_randomized_macs": float,       # Average randomized MACs detected per week
            "weeks_sampled": int
        },
        "monthly": {
            "avg_unique_mac_addresses": float,  # Average unique MAC addresses per month
            "avg_unique_ip_addresses": float,   # Average unique IP addresses per month
            "avg_wireless_clients": float,
            "avg_wired_clients": float,
            "avg_randomized_macs": float,       # Average randomized MACs detected per month
            "months_sampled": int
        }
    },
    "mac_randomization_analysis": {
        "total_macs_seen": int,
        "randomized_macs_detected": int,
        "randomized_percentage": float,
        "mac_ip_ratio": float  # If > 1.0, suggests MAC randomization (more MACs than IPs)
    },
    "networks": [
        {
            "network_id": "string",
            "network_name": "string",
            "client_count": int,
            "client_tracking_method": "string"
        }
    ],
    "warnings": [
        "MAC randomization detected: 45% of MAC addresses appear randomized",
        "MAC/IP ratio is 1.8:1, suggesting MAC randomization is inflating counts",
        "Unique IP count may be more accurate for estimating physical device count"
    ]
}
```

## Components

### 1. Configuration Module (`config.py`)
- Manage local configuration file (`.meraki_config.json` or `config.json`)
- On first run, prompt user for:
  - Meraki API key
  - Organization ID
  - Save credentials to local config file
- On subsequent runs, load from config file
- Provide option to reconfigure/update credentials
- Configure logging level
- Set time periods for averaging
- **Config file should be added to `.gitignore`** to prevent credential exposure

### 2. Meraki API Client (`meraki_client.py`)
- Authenticate with Meraki Dashboard API
- Handle rate limiting (10 calls/second per organization)
- Implement retry logic for failed requests
- Provide methods for:
  - Getting organization details
  - Querying clients across organization
  - Querying clients per network
  - Getting historical client counts (if available)
  - **Checking network client tracking method** (MAC vs Unique Identifier)
  - **Querying wireless settings** to detect MAC randomization impact

### 3. Data Processor (`data_processor.py`)
- Calculate averages from raw client data
- **Deduplicate by both MAC address and IP address within each time period**
- Handle time period aggregation (group by day/week/month)
- Count unique MAC addresses per time period
- Count unique IP addresses per time period
- **Detect randomized MAC addresses** by checking locally administered bit (2nd hex char = 2, 6, A, E)
- Calculate MAC/IP ratio to estimate MAC randomization impact
- Separate clients by connection type (wireless vs wired) based on `recentDeviceConnection`
- Calculate averages across multiple time periods
- Generate summary statistics and MAC randomization analysis

### 4. Output Module (`output.py`)
- Format results for display
- Support multiple output formats:
  - Console/terminal output
  - JSON file
  - CSV file
  - Optional: HTML report
- **Include warnings/disclaimers about MAC randomization**
- Display client tracking method in use
- Show data quality indicators

### 5. Main Application (`main.py`)
- Orchestrate the workflow
- Handle command-line arguments
- Error handling and logging

## Dependencies

### Required Python Packages
- `requests` - HTTP requests to Meraki API
- `click` or `argparse` - Command-line interface
- Standard library modules:
  - `json` - Configuration file handling
  - `datetime` - Time period calculations
  - `getpass` - Secure password/API key input
  - `pathlib` - File path handling

### API Requirements
- Meraki Dashboard API key with read access
- Organization ID for the target Meraki organization
- Rate limit: 10 API calls per second per organization

## Configuration File

The application uses a local configuration file (`.meraki_config.json`) stored in the application directory:

```json
{
    "api_key": "your_meraki_api_key_here",
    "organization_id": "your_organization_id",
    "log_level": "INFO"
}
```

**First-time setup flow:**
1. Application checks for `.meraki_config.json`
2. If not found, prompts user:
   ```
   Meraki configuration not found.
   Please enter your Meraki API key:
   Please enter your Organization ID:
   ```
3. Saves configuration to `.meraki_config.json`
4. Adds `.meraki_config.json` to `.gitignore` if not already present

**Reconfiguration:**
```bash
python main.py --reconfigure
```

## Usage Examples

```bash
# First run - will prompt for API key and Organization ID
python main.py

# Basic usage - get all averages (uses saved config)
python main.py

# Reconfigure credentials
python main.py --reconfigure

# Output to JSON file
python main.py --output json --file results.json

# Verbose logging
python main.py --verbose

# Get only specific time period
python main.py --period daily
python main.py --period weekly
python main.py --period monthly

# Include breakdown by network
python main.py --by-network

# Show unique client counts with connection type breakdown
python main.py --show-connection-types

# Show detailed MAC randomization analysis
python main.py --show-mac-analysis

# Compare MAC vs IP counts
python main.py --compare-mac-ip
```

## API Rate Limiting Considerations

- Meraki API rate limit: 10 calls/second per organization
- Implement exponential backoff for 429 responses
- Cache organization/network metadata
- Batch requests where possible

## Error Handling

- Invalid API key
- Organization not found
- Network errors/timeouts
- Rate limiting (429 responses)
- Missing permissions
- Data gaps in time series
- **MAC randomization detection and warnings**
- Client tracking method incompatibilities

## Future Enhancements

1. **Database Storage**: Store historical data for long-term trend analysis
2. **Visualization**: Generate charts/graphs of client trends
3. **Alerting**: Notify when averages exceed thresholds
4. **Scheduling**: Run automatically on schedule (cron/scheduler)
5. **Multiple Organizations**: Support querying multiple orgs
6. **Client Type Analysis**: Break down by device types (mobile, desktop, IoT)
7. **Peak Detection**: Identify peak usage times

## Research Notes

### API Endpoint Details

From Meraki Dashboard API v1 documentation:

**Get Organization Clients Search**
- Endpoint: `GET /organizations/{organizationId}/clients/search`
- Parameters: `mac`, `perPage`, `startingAfter`, `endingBefore`, `t0`, `t1`, `timespan`
- Returns: List of clients across organization

**Get Network Clients**
- Endpoint: `GET /networks/{networkId}/clients`
- Parameters: `t0`, `t1`, `timespan`, `perPage`, etc.
- Returns: Client list with `recentDeviceConnection` field

**Get Network Wireless Client Count History**
- Endpoint: `GET /networks/{networkId}/wireless/clientCountHistory`
- Parameters: `t0`, `t1`, `timespan`, `resolution`, `autoResolution`, `clientId`, `deviceSerial`, `apTag`, `band`, `ssid`
- Returns: Array of objects with `startTs`, `endTs`, `clientCount`
- Note: Best results with both `timespan` and `autoResolution` parameters

**Get Network Wireless Settings** (for MAC randomization detection)
- Endpoint: `GET /networks/{networkId}/wireless/settings`
- Returns: Wireless settings including client tracking method
- Check `clientTracking` field for tracking method in use

**Get Network Client Tracking** (MX networks)
- Endpoint: `GET /networks/{networkId}/clients/trackingSettings`
- Returns: Client tracking method ("MAC address" or "Unique client identifier")
- Available on networks with MX security appliances

### Client Identification
- Clients identified primarily by MAC address
- On SSIDs using Meraki DHCP, clients may be identified by IP address
- `recentDeviceConnection` field indicates "Wired" or "Wireless"
- No duplicate counting between wired/wireless (same MAC = same client)

## Implementation Details - Unique Client Counting

### Strategy for Counting Unique Clients

The application will collect client data over the desired time periods and deduplicate by MAC address within each period:

1. **Data Collection**:
   - Use `GET /organizations/{organizationId}/clients/search` with appropriate `timespan` or `t0`/`t1` parameters
   - Collect all clients seen during the time period
   - Each client record includes: `mac`, `recentDeviceConnection`, `firstSeen`, `lastSeen`

2. **Deduplication Logic**:
   ```python
   # Pseudocode for daily average
   for each_calendar_day in last_N_days:
       unique_macs = set()
       unique_ips = set()
       randomized_macs = set()

       for client in clients_seen_on_day:
           unique_macs.add(client['mac'])
           unique_ips.add(client['ip'])

           # Check if MAC is randomized (locally administered bit)
           # 2nd hex char is 2, 6, A, or E
           if is_randomized_mac(client['mac']):
               randomized_macs.add(client['mac'])

       daily_mac_counts.append(len(unique_macs))
       daily_ip_counts.append(len(unique_ips))
       daily_randomized_counts.append(len(randomized_macs))

   avg_daily_macs = sum(daily_mac_counts) / len(daily_mac_counts)
   avg_daily_ips = sum(daily_ip_counts) / len(daily_ip_counts)
   avg_daily_randomized = sum(daily_randomized_counts) / len(daily_randomized_counts)

   # Pseudocode for weekly average (weeks start Sunday)
   for each_calendar_week in last_N_weeks:  # Sunday-Saturday
       unique_macs = set()
       unique_ips = set()

       for client in clients_seen_in_week:
           unique_macs.add(client['mac'])
           unique_ips.add(client['ip'])

       weekly_mac_counts.append(len(unique_macs))
       weekly_ip_counts.append(len(unique_ips))

   avg_weekly_macs = sum(weekly_mac_counts) / len(weekly_mac_counts)
   avg_weekly_ips = sum(weekly_ip_counts) / len(weekly_ip_counts)

   # Calculate MAC/IP ratio
   mac_ip_ratio = avg_daily_macs / avg_daily_ips if avg_daily_ips > 0 else 1.0
   ```

3. **Connection Type Breakdown**:
   - Track last known `recentDeviceConnection` for each unique MAC
   - If a client switches from wireless to wired during a period, count based on most recent connection
   - Alternative: track both and report separately if needed

4. **Interpreting MAC/IP Ratio**:
   - **Ratio ~1.0**: Minimal MAC randomization impact (1 MAC per IP)
   - **Ratio 1.2-1.5**: Moderate MAC randomization (some devices using multiple MACs)
   - **Ratio >1.5**: Significant MAC randomization impact
   - **Example**: If avg daily MACs = 180 and avg daily IPs = 100, ratio = 1.8
     - This suggests ~80 "extra" MAC addresses due to randomization
     - The IP count (100) is likely closer to actual unique devices
   - **Caveat**: Some legitimate scenarios cause multiple MACs per IP:
     - Devices with both wired and wireless connections
     - NAT/proxy configurations
     - Multiple devices sharing an IP (NAT)
   - **Recommendation**: Use IP count as a "lower bound" estimate of unique devices

### File Structure

```
avgdevs/
├── .meraki_config.json       # Config file (gitignored)
├── .gitignore                # Git ignore file
├── main.py                   # Entry point
├── config.py                 # Configuration management
├── meraki_client.py          # API client wrapper
├── data_processor.py         # Data aggregation and averaging
├── output.py                 # Output formatting
├── requirements.txt          # Python dependencies
├── README.md                 # User documentation
└── CLAUDE.md                 # This file (architecture docs)
```

## Questions to Resolve During Implementation

1. **Data Collection Strategy**: Use `/clients/search` at organization level or iterate through networks?
   - Recommendation: Start with organization-level search for simplicity

2. **Time Period Sampling**: How many days/weeks/months to sample for each average?
   - Daily average: Sample last 7-14 complete calendar days
   - Weekly average: Sample last 4-8 complete weeks (Sunday-Saturday)
   - Monthly average: Sample last 3-6 complete calendar months

   **Important**: When run mid-period (e.g., on a Wednesday), only include complete periods:
   - For weekly: Include only complete weeks that ended on Saturday
   - For monthly: Include only complete calendar months
   - Current incomplete period should be excluded from averages

3. **Connection Type on Switch**: If a client switches from wireless to wired mid-day, how to categorize?
   - Recommendation: Use `recentDeviceConnection` (most recent connection type)
   - Alternative: Track total connections and categorize by predominant type

4. **Output formats**: JSON, CSV, console, or all three?
   - Recommendation: Start with console output, add JSON/CSV as options

5. **Error handling for partial data**: What if API doesn't return complete history?
   - Report the actual time range sampled in the output
   - Include warnings if data is incomplete

6. **MAC Randomization Handling**: How to detect and report on MAC randomization impact?
   - Recommendation: Track BOTH unique MAC addresses and unique IP addresses
   - Calculate MAC/IP ratio to quantify randomization impact
   - Display both metrics with interpretation:
     - "Average daily unique MACs: 180"
     - "Average daily unique IPs: 100"
     - "MAC/IP ratio: 1.8 (suggests MAC randomization is inflating counts)"
     - "Estimated unique devices: ~100 (based on IP count)"
   - Detect randomized MACs using locally administered bit
   - Report percentage of MACs that appear randomized
   - Consider adding flags:
     - `--show-mac-analysis` for detailed randomization analysis
     - `--compare-mac-ip` to highlight the difference

7. **IP Address Limitations**: Are there scenarios where IP counts are unreliable?
   - **NAT environments**: Multiple devices may share one public IP
   - **DHCP lease changes**: Same device may get different IPs over time (less common within a day)
   - **VPN/Proxy**: Multiple devices may appear with same IP
   - Recommendation: Document these limitations but note that for most enterprise networks, IP count is more reliable than MAC count for estimating unique devices
