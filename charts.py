"""
Charting module for visualizing client trends.
Creates line graphs for weekly and monthly averages.
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import logging


class ChartGenerator:
    """Generates charts for client trend visualization."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Use a non-GUI backend
        plt.switch_backend('Agg')

    def create_weekly_chart(self, weekly_details, output_file='weekly_chart.png'):
        """
        Create a line chart showing weekly client averages.

        Args:
            weekly_details: List of weekly statistics with 'week' and count data
            output_file: Output filename for the chart

        Returns:
            str: Path to saved chart file
        """
        if not weekly_details:
            self.logger.warning("No weekly data to chart")
            return None

        # Sort by week
        sorted_data = sorted(weekly_details, key=lambda x: x['week'])

        weeks = [d['week'] for d in sorted_data]
        mac_counts = [d['unique_macs'] for d in sorted_data]
        ip_counts = [d['unique_ips'] for d in sorted_data]
        wireless_counts = [d['wireless_clients'] for d in sorted_data]
        wired_counts = [d['wired_clients'] for d in sorted_data]

        # Create figure
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
        fig.suptitle('Weekly Client Averages (Sunday-Saturday)', fontsize=16, fontweight='bold')

        # Top chart: MAC vs IP
        ax1.plot(weeks, mac_counts, marker='o', linewidth=2, markersize=6,
                 label='Unique MAC Addresses', color='#1f77b4')
        ax1.plot(weeks, ip_counts, marker='s', linewidth=2, markersize=6,
                 label='Unique IP Addresses', color='#ff7f0e')
        ax1.set_ylabel('Unique Clients', fontsize=12, fontweight='bold')
        ax1.set_title('MAC vs IP Address Counts', fontsize=13)
        ax1.legend(loc='best', fontsize=10)
        ax1.grid(True, alpha=0.3)
        ax1.set_xlabel('Week', fontsize=12)

        # Bottom chart: Wireless vs Wired
        ax2.plot(weeks, wireless_counts, marker='o', linewidth=2, markersize=6,
                 label='Wireless Clients', color='#2ca02c')
        ax2.plot(weeks, wired_counts, marker='s', linewidth=2, markersize=6,
                 label='Wired Clients', color='#d62728')
        ax2.set_ylabel('Clients by Type', fontsize=12, fontweight='bold')
        ax2.set_xlabel('Week', fontsize=12)
        ax2.set_title('Wireless vs Wired Clients', fontsize=13)
        ax2.legend(loc='best', fontsize=10)
        ax2.grid(True, alpha=0.3)

        # Rotate x-axis labels for better readability
        for ax in [ax1, ax2]:
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        plt.close()

        self.logger.info(f"Weekly chart saved to {output_file}")
        return output_file

    def create_monthly_chart(self, monthly_details, output_file='monthly_chart.png'):
        """
        Create a line chart showing monthly client averages.

        Args:
            monthly_details: List of monthly statistics with 'month' and count data
            output_file: Output filename for the chart

        Returns:
            str: Path to saved chart file
        """
        if not monthly_details:
            self.logger.warning("No monthly data to chart")
            return None

        # Sort by month
        sorted_data = sorted(monthly_details, key=lambda x: x['month'])

        months = [d['month'] for d in sorted_data]
        mac_counts = [d['unique_macs'] for d in sorted_data]
        ip_counts = [d['unique_ips'] for d in sorted_data]
        wireless_counts = [d['wireless_clients'] for d in sorted_data]
        wired_counts = [d['wired_clients'] for d in sorted_data]

        # Create figure
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
        fig.suptitle('Monthly Client Averages', fontsize=16, fontweight='bold')

        # Top chart: MAC vs IP
        ax1.plot(months, mac_counts, marker='o', linewidth=2, markersize=6,
                 label='Unique MAC Addresses', color='#1f77b4')
        ax1.plot(months, ip_counts, marker='s', linewidth=2, markersize=6,
                 label='Unique IP Addresses', color='#ff7f0e')
        ax1.set_ylabel('Unique Clients', fontsize=12, fontweight='bold')
        ax1.set_title('MAC vs IP Address Counts', fontsize=13)
        ax1.legend(loc='best', fontsize=10)
        ax1.grid(True, alpha=0.3)
        ax1.set_xlabel('Month', fontsize=12)

        # Bottom chart: Wireless vs Wired
        ax2.plot(months, wireless_counts, marker='o', linewidth=2, markersize=6,
                 label='Wireless Clients', color='#2ca02c')
        ax2.plot(months, wired_counts, marker='s', linewidth=2, markersize=6,
                 label='Wired Clients', color='#d62728')
        ax2.set_ylabel('Clients by Type', fontsize=12, fontweight='bold')
        ax2.set_xlabel('Month', fontsize=12)
        ax2.set_title('Wireless vs Wired Clients', fontsize=13)
        ax2.legend(loc='best', fontsize=10)
        ax2.grid(True, alpha=0.3)

        # Rotate x-axis labels for better readability
        for ax in [ax1, ax2]:
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        plt.close()

        self.logger.info(f"Monthly chart saved to {output_file}")
        return output_file

    def create_combined_chart(self, weekly_details, monthly_details,
                            weekly_file='weekly_trend.png',
                            monthly_file='monthly_trend.png'):
        """
        Create both weekly and monthly charts.

        Args:
            weekly_details: List of weekly statistics
            monthly_details: List of monthly statistics
            weekly_file: Output filename for weekly chart
            monthly_file: Output filename for monthly chart

        Returns:
            tuple: (weekly_file_path, monthly_file_path)
        """
        weekly_path = self.create_weekly_chart(weekly_details, weekly_file)
        monthly_path = self.create_monthly_chart(monthly_details, monthly_file)

        return weekly_path, monthly_path
