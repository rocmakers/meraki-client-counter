"""
Output formatting module.
Handles displaying results in console, JSON, and CSV formats.
"""

import json
import csv
import logging
from datetime import datetime


class OutputFormatter:
    """Formats and displays client average data."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def generate_warnings(self, mac_analysis):
        """
        Generate warning messages based on MAC randomization analysis.

        Args:
            mac_analysis: MAC randomization analysis dict

        Returns:
            list: Warning messages
        """
        warnings = []

        randomized_pct = mac_analysis.get('randomized_percentage', 0)
        mac_ip_ratio = mac_analysis.get('mac_ip_ratio', 1.0)

        if randomized_pct > 10:
            warnings.append(
                f"MAC randomization detected: {randomized_pct:.1f}% of MAC addresses appear randomized"
            )

        if mac_ip_ratio > 1.2:
            warnings.append(
                f"MAC/IP ratio is {mac_ip_ratio:.2f}:1, suggesting MAC randomization is inflating counts"
            )

        if mac_ip_ratio > 1.5:
            warnings.append(
                "Unique IP count may be more accurate for estimating physical device count"
            )

        if not warnings:
            warnings.append(
                "Counts represent unique MAC addresses, not necessarily unique physical devices"
            )

        return warnings

    def format_console(self, results, show_details=False, show_mac_analysis=False):
        """
        Format results for console output.

        Args:
            results: Results dictionary
            show_details: Show detailed breakdown
            show_mac_analysis: Show MAC randomization analysis

        Returns:
            str: Formatted output string
        """
        lines = []
        lines.append("=" * 80)
        lines.append("Meraki Average Client Device Counter - Results")
        lines.append("=" * 80)
        lines.append("")

        # Organization info
        lines.append(f"Organization: {results.get('organization_name', 'N/A')}")
        lines.append(f"Organization ID: {results.get('organization_id', 'N/A')}")
        lines.append(f"Timestamp: {results.get('timestamp', 'N/A')}")
        lines.append(f"Client Tracking Method: {results.get('client_tracking_method', 'Unknown')}")
        lines.append("")

        # Daily averages
        if 'daily' in results.get('averages', {}):
            daily = results['averages']['daily']
            lines.append("Daily Averages:")
            lines.append("-" * 40)
            lines.append(f"  Average Unique MAC Addresses:  {daily.get('avg_unique_mac_addresses', 0):.2f}")
            lines.append(f"  Average Unique IP Addresses:   {daily.get('avg_unique_ip_addresses', 0):.2f}")
            lines.append(f"  Average Wireless Clients:      {daily.get('avg_wireless_clients', 0):.2f}")
            lines.append(f"  Average Wired Clients:         {daily.get('avg_wired_clients', 0):.2f}")
            lines.append(f"  Days Sampled:                  {daily.get('days_sampled', 0)}")
            lines.append("")

        # Weekly averages
        if 'weekly' in results.get('averages', {}):
            weekly = results['averages']['weekly']
            lines.append("Weekly Averages (Sunday-Saturday):")
            lines.append("-" * 40)
            lines.append(f"  Average Unique MAC Addresses:  {weekly.get('avg_unique_mac_addresses', 0):.2f}")
            lines.append(f"  Average Unique IP Addresses:   {weekly.get('avg_unique_ip_addresses', 0):.2f}")
            lines.append(f"  Average Wireless Clients:      {weekly.get('avg_wireless_clients', 0):.2f}")
            lines.append(f"  Average Wired Clients:         {weekly.get('avg_wired_clients', 0):.2f}")
            lines.append(f"  Weeks Sampled:                 {weekly.get('weeks_sampled', 0)}")
            lines.append("")

        # Monthly averages
        if 'monthly' in results.get('averages', {}):
            monthly = results['averages']['monthly']
            lines.append("Monthly Averages:")
            lines.append("-" * 40)
            lines.append(f"  Average Unique MAC Addresses:  {monthly.get('avg_unique_mac_addresses', 0):.2f}")
            lines.append(f"  Average Unique IP Addresses:   {monthly.get('avg_unique_ip_addresses', 0):.2f}")
            lines.append(f"  Average Wireless Clients:      {monthly.get('avg_wireless_clients', 0):.2f}")
            lines.append(f"  Average Wired Clients:         {monthly.get('avg_wired_clients', 0):.2f}")
            lines.append(f"  Months Sampled:                {monthly.get('months_sampled', 0)}")
            lines.append("")

        # MAC Randomization Analysis
        if show_mac_analysis and 'mac_randomization_analysis' in results:
            analysis = results['mac_randomization_analysis']
            lines.append("MAC Randomization Analysis:")
            lines.append("-" * 40)
            lines.append(f"  Total MACs Seen:               {analysis.get('total_macs_seen', 0)}")
            lines.append(f"  Total IPs Seen:                {analysis.get('total_ips_seen', 0)}")
            lines.append(f"  Randomized MACs Detected:      {analysis.get('randomized_macs_detected', 0)}")
            lines.append(f"  Randomized Percentage:         {analysis.get('randomized_percentage', 0):.2f}%")
            lines.append(f"  MAC/IP Ratio:                  {analysis.get('mac_ip_ratio', 1.0):.2f}:1")
            lines.append("")

            # Interpretation
            ratio = analysis.get('mac_ip_ratio', 1.0)
            if ratio > 1.5:
                lines.append("  Interpretation: SIGNIFICANT MAC randomization detected")
                lines.append("                  IP count is likely more accurate for unique device estimation")
            elif ratio > 1.2:
                lines.append("  Interpretation: MODERATE MAC randomization detected")
            else:
                lines.append("  Interpretation: MINIMAL MAC randomization detected")
            lines.append("")

        # Warnings
        if 'warnings' in results and results['warnings']:
            lines.append("Warnings:")
            lines.append("-" * 40)
            for warning in results['warnings']:
                lines.append(f"  ⚠ {warning}")
            lines.append("")

        lines.append("=" * 80)

        return "\n".join(lines)

    def save_json(self, results, filepath):
        """
        Save results as JSON file.

        Args:
            results: Results dictionary
            filepath: Output file path

        Returns:
            bool: True if successful
        """
        try:
            with open(filepath, 'w') as f:
                json.dump(results, f, indent=2)
            self.logger.info(f"Results saved to {filepath}")
            return True
        except IOError as e:
            self.logger.error(f"Error saving JSON file: {e}")
            return False

    def save_csv(self, results, filepath):
        """
        Save results as CSV file.

        Args:
            results: Results dictionary
            filepath: Output file path

        Returns:
            bool: True if successful
        """
        try:
            with open(filepath, 'w', newline='') as f:
                writer = csv.writer(f)

                # Header
                writer.writerow(['Metric', 'Daily', 'Weekly', 'Monthly'])

                # Data rows
                averages = results.get('averages', {})
                daily = averages.get('daily', {})
                weekly = averages.get('weekly', {})
                monthly = averages.get('monthly', {})

                writer.writerow([
                    'Average Unique MAC Addresses',
                    daily.get('avg_unique_mac_addresses', 0),
                    weekly.get('avg_unique_mac_addresses', 0),
                    monthly.get('avg_unique_mac_addresses', 0)
                ])

                writer.writerow([
                    'Average Unique IP Addresses',
                    daily.get('avg_unique_ip_addresses', 0),
                    weekly.get('avg_unique_ip_addresses', 0),
                    monthly.get('avg_unique_ip_addresses', 0)
                ])

                writer.writerow([
                    'Average Wireless Clients',
                    daily.get('avg_wireless_clients', 0),
                    weekly.get('avg_wireless_clients', 0),
                    monthly.get('avg_wireless_clients', 0)
                ])

                writer.writerow([
                    'Average Wired Clients',
                    daily.get('avg_wired_clients', 0),
                    weekly.get('avg_wired_clients', 0),
                    monthly.get('avg_wired_clients', 0)
                ])

                writer.writerow([
                    'Periods Sampled',
                    daily.get('days_sampled', 0),
                    weekly.get('weeks_sampled', 0),
                    monthly.get('months_sampled', 0)
                ])

                # MAC Randomization section
                writer.writerow([])
                writer.writerow(['MAC Randomization Analysis'])

                if 'mac_randomization_analysis' in results:
                    analysis = results['mac_randomization_analysis']
                    writer.writerow(['Total MACs Seen', analysis.get('total_macs_seen', 0)])
                    writer.writerow(['Total IPs Seen', analysis.get('total_ips_seen', 0)])
                    writer.writerow(['Randomized MACs', analysis.get('randomized_macs_detected', 0)])
                    writer.writerow(['Randomized %', f"{analysis.get('randomized_percentage', 0):.2f}%"])
                    writer.writerow(['MAC/IP Ratio', f"{analysis.get('mac_ip_ratio', 1.0):.2f}"])

            self.logger.info(f"Results saved to {filepath}")
            return True

        except IOError as e:
            self.logger.error(f"Error saving CSV file: {e}")
            return False
