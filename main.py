#!/usr/bin/env python3
"""
Meraki Average Client Device Counter

Main entry point for the application.
Queries Meraki Dashboard API and calculates average client counts per day, week, and month.
"""

import argparse
import logging
import sys
from datetime import datetime

from config import Config
from meraki_client import MerakiClient
from data_processor import DataProcessor
from output import OutputFormatter
from charts import ChartGenerator
from database import ClientDatabase


def setup_logging(verbose=False):
    """
    Configure logging for the application.

    Args:
        verbose: Enable verbose (DEBUG) logging
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def parse_arguments():
    """
    Parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description='Calculate average client counts from Meraki Dashboard API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Run with default settings
  %(prog)s --reconfigure            # Reconfigure API credentials
  %(prog)s --period daily           # Show only daily averages
  %(prog)s --output json -f out.json  # Save results as JSON
  %(prog)s --show-mac-analysis      # Show detailed MAC randomization analysis
  %(prog)s --verbose                # Enable verbose logging
        """
    )

    parser.add_argument(
        '--reconfigure',
        action='store_true',
        help='Reconfigure API credentials'
    )

    parser.add_argument(
        '--period',
        choices=['daily', 'weekly', 'monthly', 'all'],
        default='all',
        help='Time period to calculate (default: all)'
    )

    parser.add_argument(
        '--output',
        choices=['console', 'json', 'csv'],
        default='console',
        help='Output format (default: console)'
    )

    parser.add_argument(
        '-f', '--file',
        help='Output file path (required for json/csv output)'
    )

    parser.add_argument(
        '--show-mac-analysis',
        action='store_true',
        help='Show detailed MAC randomization analysis'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='Number of days to sample for daily average (default: 7)'
    )

    parser.add_argument(
        '--weeks',
        type=int,
        default=4,
        help='Number of weeks to sample for weekly average (default: 4)'
    )

    parser.add_argument(
        '--months',
        type=int,
        default=3,
        help='Number of months to sample for monthly average (default: 3)'
    )

    parser.add_argument(
        '--generate-charts',
        action='store_true',
        help='Generate chart visualizations (PNG files)'
    )

    parser.add_argument(
        '--chart-weeks',
        type=int,
        default=52,
        help='Number of weeks to include in weekly chart (default: 52)'
    )

    parser.add_argument(
        '--chart-months',
        type=int,
        default=12,
        help='Number of months to include in monthly chart (default: 12)'
    )

    parser.add_argument(
        '--use-historical',
        action='store_true',
        help='Use historical data from database instead of just API data'
    )

    parser.add_argument(
        '--db-stats',
        action='store_true',
        help='Show database statistics and exit'
    )

    return parser.parse_args()


def collect_client_data(client, org_id, days_to_fetch=7):
    """
    Collect client data from Meraki API.

    Args:
        client: MerakiClient instance
        org_id: Organization ID
        days_to_fetch: Number of days of data to fetch (default: 7 for daily cron)

    Returns:
        list: Client records
    """
    logger = logging.getLogger(__name__)

    # Calculate timespan in seconds (max 30 days = 2592000 seconds per API call)
    max_days_per_call = 30
    timespan_seconds = min(days_to_fetch, max_days_per_call) * 86400

    logger.info(f"Fetching client data for last {min(days_to_fetch, max_days_per_call)} days...")

    # Collect client data from API
    clients = client.get_clients_in_timespan(org_id, timespan_seconds)

    logger.info(f"Retrieved {len(clients)} total client records")
    return clients


def main():
    """Main application logic."""
    args = parse_arguments()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    logger.info("Starting Meraki Average Client Device Counter")

    # Initialize database
    db = ClientDatabase()

    # Show database stats if requested
    if args.db_stats:
        stats = db.get_stats()
        print("\n" + "=" * 80)
        print("Database Statistics")
        print("=" * 80)
        print(f"Total Records:           {stats['total_records']}")
        print(f"Unique MAC Addresses:    {stats['unique_mac_addresses']}")
        print(f"Collection Runs:         {stats['collection_runs']}")
        print(f"Earliest Record:         {stats['earliest_date']}")
        print(f"Latest Record:           {stats['latest_date']}")
        print("=" * 80)

        # Show recent collection runs
        runs = db.get_collection_runs()
        if runs:
            print("\nRecent Collection Runs:")
            print("-" * 80)
            for run in runs[:5]:
                print(f"  {run['run_timestamp']}: {run['clients_collected']} clients ({run['timespan_days']} days)")

        db.close()
        return

    # Validate output arguments
    if args.output in ['json', 'csv'] and not args.file:
        logger.error(f"--file is required when using --output {args.output}")
        db.close()
        sys.exit(1)

    # Load configuration
    config = Config()
    if not config.load(reconfigure=args.reconfigure):
        logger.error("Failed to load configuration")
        sys.exit(1)

    # Initialize API client
    logger.info("Initializing Meraki API client...")
    meraki_client = MerakiClient(config.get_api_key())

    # Get organization info
    org_id = config.get_organization_id()
    logger.info(f"Fetching organization details for {org_id}...")

    org_info = meraki_client.get_organization(org_id)
    if not org_info:
        logger.error("Failed to retrieve organization information")
        sys.exit(1)

    org_name = org_info.get('name', 'Unknown')
    logger.info(f"Organization: {org_name}")

    # Determine how many days of data to fetch
    # Default to 7 days for regular collection (optimal for daily cron)
    # If specific analysis periods requested or generating charts, use those parameters
    if args.generate_charts:
        days_to_fetch = max(
            args.chart_weeks * 7,
            args.chart_months * 31
        )
    elif args.period != 'all':
        # Specific period requested, fetch enough for that analysis
        days_to_fetch = max(
            args.days if args.period == 'daily' else 0,
            args.weeks * 7 if args.period == 'weekly' else 0,
            args.months * 31 if args.period == 'monthly' else 0
        )
    else:
        # Default: fetch 7 days for efficient daily collection
        # This is optimal for cron jobs running daily
        days_to_fetch = 7

    # Limit to API maximum
    days_to_fetch = min(days_to_fetch, 30)

    # Warn if requested data exceeds API limit
    if args.generate_charts and (args.chart_weeks * 7 > 30 or args.chart_months * 31 > 30):
        logger.warning(f"Note: Meraki API limits data to 30 days. Charts will show available data only.")
        logger.warning(f"For {args.chart_weeks} weeks or {args.chart_months} months, you would need historical data collection.")

    # Collect client data from API and store in database
    clients_from_api = collect_client_data(meraki_client, org_id, days_to_fetch)

    if not clients_from_api:
        logger.warning("No client data retrieved from API")
        # Check if we have historical data
        if not args.use_historical:
            db.close()
            sys.exit(1)

    # Store API data in database
    if clients_from_api:
        logger.info("Storing client data in database...")
        new_records, duplicates = db.store_clients(clients_from_api, org_id, org_name, days_to_fetch)
        logger.info(f"Database updated: {new_records} new records, {duplicates} duplicates")

    # Determine which data to use for analysis
    if args.use_historical:
        logger.info("Using historical data from database...")
        clients = db.get_all_clients()
        logger.info(f"Loaded {len(clients)} client records from database")

        # Show database date range
        earliest, latest = db.get_date_range()
        if earliest and latest:
            logger.info(f"Database date range: {earliest} to {latest}")
    else:
        clients = clients_from_api

    if not clients:
        logger.warning("No client data available for analysis")
        db.close()
        sys.exit(1)

    # Process data
    logger.info("Processing client data...")
    processor = DataProcessor()

    results = {
        'organization_id': org_id,
        'organization_name': org_name,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'client_tracking_method': 'MAC address',  # Default assumption
        'averages': {}
    }

    # Calculate averages based on period selection
    if args.period in ['daily', 'all']:
        logger.info(f"Calculating daily averages ({args.days} days)...")
        daily = processor.calculate_daily_averages(clients, args.days)
        if daily:
            results['averages']['daily'] = daily
        else:
            logger.warning("Could not calculate daily averages")

    if args.period in ['weekly', 'all']:
        logger.info(f"Calculating weekly averages ({args.weeks} weeks)...")
        weekly = processor.calculate_weekly_averages(clients, args.weeks)
        if weekly:
            results['averages']['weekly'] = weekly
        else:
            logger.warning("Could not calculate weekly averages")

    if args.period in ['monthly', 'all']:
        logger.info(f"Calculating monthly averages ({args.months} months)...")
        monthly = processor.calculate_monthly_averages(clients, args.months)
        if monthly:
            results['averages']['monthly'] = monthly
        else:
            logger.warning("Could not calculate monthly averages")

    # MAC randomization analysis
    logger.info("Analyzing MAC randomization...")
    mac_analysis = processor.analyze_mac_randomization(clients)
    results['mac_randomization_analysis'] = mac_analysis

    # Determine if MAC randomization warning should be shown
    results['mac_randomization_warning'] = mac_analysis.get('randomized_percentage', 0) > 10

    # Generate warnings
    formatter = OutputFormatter()
    results['warnings'] = formatter.generate_warnings(mac_analysis)

    # Output results
    if args.output == 'console':
        output = formatter.format_console(
            results,
            show_mac_analysis=args.show_mac_analysis
        )
        print(output)

    elif args.output == 'json':
        if formatter.save_json(results, args.file):
            logger.info(f"Results saved to {args.file}")
        else:
            logger.error("Failed to save JSON output")
            sys.exit(1)

    elif args.output == 'csv':
        if formatter.save_csv(results, args.file):
            logger.info(f"Results saved to {args.file}")
        else:
            logger.error("Failed to save CSV output")
            sys.exit(1)

    # Generate charts if requested
    if args.generate_charts:
        logger.info("Generating charts...")
        chart_gen = ChartGenerator()

        weekly_data = results['averages'].get('weekly', {}).get('weekly_details', [])
        monthly_data = results['averages'].get('monthly', {}).get('monthly_details', [])

        if weekly_data:
            weekly_chart = chart_gen.create_weekly_chart(weekly_data, 'weekly_clients_chart.png')
            if weekly_chart:
                print(f"\n📊 Weekly chart saved to: {weekly_chart}")
        else:
            logger.warning("No weekly data available for charting")

        if monthly_data:
            monthly_chart = chart_gen.create_monthly_chart(monthly_data, 'monthly_clients_chart.png')
            if monthly_chart:
                print(f"📊 Monthly chart saved to: {monthly_chart}")
        else:
            logger.warning("No monthly data available for charting")

    # Close database connection
    db.close()

    logger.info("Complete!")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        logging.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)
