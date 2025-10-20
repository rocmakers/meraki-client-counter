"""
Data processor module for calculating client averages.
Handles deduplication, time period aggregation, and MAC randomization detection.
"""

import logging
from datetime import datetime, timedelta
from collections import defaultdict


class DataProcessor:
    """Processes client data to calculate averages and detect MAC randomization."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def is_randomized_mac(self, mac_address):
        """
        Check if a MAC address appears to be randomized.
        Randomized MACs have the locally administered bit set (2nd hex char = 2, 6, A, or E).

        Args:
            mac_address: MAC address string (e.g., "AA:BB:CC:DD:EE:FF")

        Returns:
            bool: True if MAC appears randomized
        """
        if not mac_address or len(mac_address) < 2:
            return False

        # Get the second character (first octet, second hex digit)
        second_char = mac_address[1].upper()
        return second_char in ['2', '6', 'A', 'E']

    def get_week_boundaries(self, date):
        """
        Get the Sunday-Saturday boundaries for the week containing the given date.

        Args:
            date: datetime object

        Returns:
            tuple: (week_start, week_end) as datetime objects
        """
        # Get the day of week (0=Monday, 6=Sunday)
        day_of_week = date.weekday()

        # Calculate days to Sunday (start of week)
        # If Monday (0), go back 1 day; if Sunday (6), go back 6 days
        days_to_sunday = (day_of_week + 1) % 7

        week_start = date - timedelta(days=days_to_sunday)
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

        week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)

        return week_start, week_end

    def get_month_boundaries(self, date):
        """
        Get the first and last day of the month containing the given date.

        Args:
            date: datetime object

        Returns:
            tuple: (month_start, month_end) as datetime objects
        """
        month_start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Get last day of month
        if month_start.month == 12:
            next_month = month_start.replace(year=month_start.year + 1, month=1)
        else:
            next_month = month_start.replace(month=month_start.month + 1)

        month_end = next_month - timedelta(seconds=1)

        return month_start, month_end

    def group_clients_by_day(self, clients):
        """
        Group clients by calendar day.

        Args:
            clients: List of client records

        Returns:
            dict: {date_string: [clients]}
        """
        grouped = defaultdict(list)

        for client in clients:
            # Get the last seen timestamp
            if 'lastSeen' in client:
                try:
                    # Parse ISO 8601 timestamp
                    last_seen = datetime.fromisoformat(client['lastSeen'].replace('Z', '+00:00'))
                    day_key = last_seen.strftime('%Y-%m-%d')
                    grouped[day_key].append(client)
                except (ValueError, AttributeError) as e:
                    self.logger.warning(f"Could not parse timestamp for client: {e}")
                    continue

        return grouped

    def group_clients_by_week(self, clients):
        """
        Group clients by calendar week (Sunday-Saturday).

        Args:
            clients: List of client records

        Returns:
            dict: {week_key: [clients]}
        """
        grouped = defaultdict(list)

        for client in clients:
            if 'lastSeen' in client:
                try:
                    last_seen = datetime.fromisoformat(client['lastSeen'].replace('Z', '+00:00'))
                    week_start, _ = self.get_week_boundaries(last_seen)
                    week_key = week_start.strftime('%Y-W%U')  # Year-Week format
                    grouped[week_key].append(client)
                except (ValueError, AttributeError) as e:
                    self.logger.warning(f"Could not parse timestamp for client: {e}")
                    continue

        return grouped

    def group_clients_by_month(self, clients):
        """
        Group clients by calendar month.

        Args:
            clients: List of client records

        Returns:
            dict: {month_key: [clients]}
        """
        grouped = defaultdict(list)

        for client in clients:
            if 'lastSeen' in client:
                try:
                    last_seen = datetime.fromisoformat(client['lastSeen'].replace('Z', '+00:00'))
                    month_key = last_seen.strftime('%Y-%m')  # Year-Month format
                    grouped[month_key].append(client)
                except (ValueError, AttributeError) as e:
                    self.logger.warning(f"Could not parse timestamp for client: {e}")
                    continue

        return grouped

    def count_unique_clients(self, clients):
        """
        Count unique MAC addresses, IP addresses, and detect randomized MACs.

        Args:
            clients: List of client records

        Returns:
            dict: Statistics including unique counts and randomization info
        """
        unique_macs = set()
        unique_ips = set()
        randomized_macs = set()
        wireless_macs = set()
        wired_macs = set()

        for client in clients:
            mac = client.get('mac')
            ip = client.get('ip')
            connection_type = client.get('recentDeviceConnection', 'Unknown')

            if mac:
                unique_macs.add(mac)

                # Check if randomized
                if self.is_randomized_mac(mac):
                    randomized_macs.add(mac)

                # Track connection type
                if connection_type == 'Wireless':
                    wireless_macs.add(mac)
                elif connection_type == 'Wired':
                    wired_macs.add(mac)

            if ip:
                unique_ips.add(ip)

        return {
            'unique_macs': len(unique_macs),
            'unique_ips': len(unique_ips),
            'randomized_macs': len(randomized_macs),
            'wireless_clients': len(wireless_macs),
            'wired_clients': len(wired_macs),
            'mac_ip_ratio': len(unique_macs) / len(unique_ips) if len(unique_ips) > 0 else 1.0
        }

    def calculate_daily_averages(self, clients, num_days=7):
        """
        Calculate daily averages for unique clients.

        Args:
            clients: List of all client records
            num_days: Number of days to analyze

        Returns:
            dict: Daily average statistics
        """
        grouped = self.group_clients_by_day(clients)

        daily_stats = []
        for day_key in sorted(grouped.keys())[-num_days:]:
            stats = self.count_unique_clients(grouped[day_key])
            stats['date'] = day_key
            daily_stats.append(stats)

        if not daily_stats:
            return None

        # Calculate averages
        avg_macs = sum(s['unique_macs'] for s in daily_stats) / len(daily_stats)
        avg_ips = sum(s['unique_ips'] for s in daily_stats) / len(daily_stats)
        avg_randomized = sum(s['randomized_macs'] for s in daily_stats) / len(daily_stats)
        avg_wireless = sum(s['wireless_clients'] for s in daily_stats) / len(daily_stats)
        avg_wired = sum(s['wired_clients'] for s in daily_stats) / len(daily_stats)

        return {
            'avg_unique_mac_addresses': round(avg_macs, 2),
            'avg_unique_ip_addresses': round(avg_ips, 2),
            'avg_randomized_macs': round(avg_randomized, 2),
            'avg_wireless_clients': round(avg_wireless, 2),
            'avg_wired_clients': round(avg_wired, 2),
            'days_sampled': len(daily_stats),
            'daily_details': daily_stats
        }

    def calculate_weekly_averages(self, clients, num_weeks=4):
        """
        Calculate weekly averages for unique clients.

        Args:
            clients: List of all client records
            num_weeks: Number of weeks to analyze

        Returns:
            dict: Weekly average statistics
        """
        grouped = self.group_clients_by_week(clients)

        weekly_stats = []
        for week_key in sorted(grouped.keys())[-num_weeks:]:
            stats = self.count_unique_clients(grouped[week_key])
            stats['week'] = week_key
            weekly_stats.append(stats)

        if not weekly_stats:
            return None

        avg_macs = sum(s['unique_macs'] for s in weekly_stats) / len(weekly_stats)
        avg_ips = sum(s['unique_ips'] for s in weekly_stats) / len(weekly_stats)
        avg_randomized = sum(s['randomized_macs'] for s in weekly_stats) / len(weekly_stats)
        avg_wireless = sum(s['wireless_clients'] for s in weekly_stats) / len(weekly_stats)
        avg_wired = sum(s['wired_clients'] for s in weekly_stats) / len(weekly_stats)

        return {
            'avg_unique_mac_addresses': round(avg_macs, 2),
            'avg_unique_ip_addresses': round(avg_ips, 2),
            'avg_randomized_macs': round(avg_randomized, 2),
            'avg_wireless_clients': round(avg_wireless, 2),
            'avg_wired_clients': round(avg_wired, 2),
            'weeks_sampled': len(weekly_stats),
            'weekly_details': weekly_stats
        }

    def calculate_monthly_averages(self, clients, num_months=3):
        """
        Calculate monthly averages for unique clients.

        Args:
            clients: List of all client records
            num_months: Number of months to analyze

        Returns:
            dict: Monthly average statistics
        """
        grouped = self.group_clients_by_month(clients)

        monthly_stats = []
        for month_key in sorted(grouped.keys())[-num_months:]:
            stats = self.count_unique_clients(grouped[month_key])
            stats['month'] = month_key
            monthly_stats.append(stats)

        if not monthly_stats:
            return None

        avg_macs = sum(s['unique_macs'] for s in monthly_stats) / len(monthly_stats)
        avg_ips = sum(s['unique_ips'] for s in monthly_stats) / len(monthly_stats)
        avg_randomized = sum(s['randomized_macs'] for s in monthly_stats) / len(monthly_stats)
        avg_wireless = sum(s['wireless_clients'] for s in monthly_stats) / len(monthly_stats)
        avg_wired = sum(s['wired_clients'] for s in monthly_stats) / len(monthly_stats)

        return {
            'avg_unique_mac_addresses': round(avg_macs, 2),
            'avg_unique_ip_addresses': round(avg_ips, 2),
            'avg_randomized_macs': round(avg_randomized, 2),
            'avg_wireless_clients': round(avg_wireless, 2),
            'avg_wired_clients': round(avg_wired, 2),
            'months_sampled': len(monthly_stats),
            'monthly_details': monthly_stats
        }

    def analyze_mac_randomization(self, clients):
        """
        Analyze MAC randomization across all clients.

        Args:
            clients: List of all client records

        Returns:
            dict: MAC randomization analysis
        """
        total_stats = self.count_unique_clients(clients)

        total_macs = total_stats['unique_macs']
        randomized_count = total_stats['randomized_macs']
        total_ips = total_stats['unique_ips']

        randomized_percentage = (randomized_count / total_macs * 100) if total_macs > 0 else 0
        mac_ip_ratio = total_stats['mac_ip_ratio']

        return {
            'total_macs_seen': total_macs,
            'total_ips_seen': total_ips,
            'randomized_macs_detected': randomized_count,
            'randomized_percentage': round(randomized_percentage, 2),
            'mac_ip_ratio': round(mac_ip_ratio, 2)
        }
