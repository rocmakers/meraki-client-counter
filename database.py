"""
Database module for storing historical client data.
Uses SQLite3 to persist client records over time.
"""

import sqlite3
import logging
from datetime import datetime
from pathlib import Path


class ClientDatabase:
    """Manages SQLite database for historical client data."""

    def __init__(self, db_path='client_history.db'):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.logger = logging.getLogger(__name__)
        self.conn = None
        self._init_database()

    def _init_database(self):
        """Create database and tables if they don't exist."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Access columns by name
        cursor = self.conn.cursor()

        # Create clients table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mac_address TEXT NOT NULL,
                ip_address TEXT,
                last_seen TEXT NOT NULL,
                first_seen TEXT,
                connection_type TEXT,
                network_id TEXT,
                network_name TEXT,
                description TEXT,
                vlan INTEGER,
                ssid TEXT,
                manufacturer TEXT,
                collected_at TEXT NOT NULL,
                UNIQUE(mac_address, last_seen, network_id)
            )
        ''')

        # Create index for faster queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_last_seen
            ON clients(last_seen)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_mac_address
            ON clients(mac_address)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_collected_at
            ON clients(collected_at)
        ''')

        # Create collection runs table to track when we collected data
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS collection_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_timestamp TEXT NOT NULL,
                organization_id TEXT NOT NULL,
                organization_name TEXT,
                clients_collected INTEGER,
                timespan_days INTEGER
            )
        ''')

        self.conn.commit()
        self.logger.info(f"Database initialized at {self.db_path}")

    def store_clients(self, clients, org_id, org_name, timespan_days=30):
        """
        Store client records in database, avoiding duplicates.

        Args:
            clients: List of client records from API
            org_id: Organization ID
            org_name: Organization name
            timespan_days: Number of days of data collected

        Returns:
            tuple: (new_records, duplicate_records)
        """
        cursor = self.conn.cursor()
        collected_at = datetime.utcnow().isoformat()

        new_records = 0
        duplicate_records = 0

        for client in clients:
            mac = client.get('mac')
            ip = client.get('ip')
            last_seen = client.get('lastSeen')
            first_seen = client.get('firstSeen')
            connection_type = client.get('recentDeviceConnection')
            network_id = client.get('network', {}).get('id') if isinstance(client.get('network'), dict) else None
            network_name = client.get('network', {}).get('name') if isinstance(client.get('network'), dict) else None
            description = client.get('description')
            vlan = client.get('vlan')
            ssid = client.get('ssid')
            manufacturer = client.get('manufacturer')

            try:
                cursor.execute('''
                    INSERT INTO clients (
                        mac_address, ip_address, last_seen, first_seen,
                        connection_type, network_id, network_name,
                        description, vlan, ssid, manufacturer, collected_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    mac, ip, last_seen, first_seen, connection_type,
                    network_id, network_name, description, vlan, ssid,
                    manufacturer, collected_at
                ))
                new_records += 1
            except sqlite3.IntegrityError:
                # Duplicate record (same MAC, last_seen, network_id)
                duplicate_records += 1

        # Record this collection run
        cursor.execute('''
            INSERT INTO collection_runs (
                run_timestamp, organization_id, organization_name,
                clients_collected, timespan_days
            ) VALUES (?, ?, ?, ?, ?)
        ''', (collected_at, org_id, org_name, len(clients), timespan_days))

        self.conn.commit()

        self.logger.info(f"Stored {new_records} new client records, {duplicate_records} duplicates skipped")
        return new_records, duplicate_records

    def get_clients_in_date_range(self, start_date, end_date):
        """
        Retrieve all unique clients seen between start and end dates.

        Args:
            start_date: Start date (ISO format string or datetime)
            end_date: End date (ISO format string or datetime)

        Returns:
            list: List of client records
        """
        if isinstance(start_date, datetime):
            start_date = start_date.isoformat()
        if isinstance(end_date, datetime):
            end_date = end_date.isoformat()

        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT DISTINCT
                mac_address, ip_address, last_seen, first_seen,
                connection_type, network_id, network_name,
                description, vlan, ssid, manufacturer
            FROM clients
            WHERE last_seen >= ? AND last_seen <= ?
            ORDER BY last_seen
        ''', (start_date, end_date))

        rows = cursor.fetchall()

        # Convert to dict list similar to API format
        clients = []
        for row in rows:
            clients.append({
                'mac': row['mac_address'],
                'ip': row['ip_address'],
                'lastSeen': row['last_seen'],
                'firstSeen': row['first_seen'],
                'recentDeviceConnection': row['connection_type'],
                'network': {'id': row['network_id'], 'name': row['network_name']},
                'description': row['description'],
                'vlan': row['vlan'],
                'ssid': row['ssid'],
                'manufacturer': row['manufacturer']
            })

        return clients

    def get_latest_client_timestamp(self):
        """
        Get the most recent last_seen timestamp from the database.

        Returns:
            str: ISO format timestamp of most recent client, or None if no data
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT MAX(last_seen) as latest_timestamp
            FROM clients
        ''')
        row = cursor.fetchone()
        return row['latest_timestamp'] if row else None

    def get_all_clients(self):
        """
        Retrieve all clients from database.

        Returns:
            list: All client records
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT DISTINCT
                mac_address, ip_address, last_seen, first_seen,
                connection_type, network_id, network_name,
                description, vlan, ssid, manufacturer
            FROM clients
            ORDER BY last_seen DESC
        ''')

        rows = cursor.fetchall()

        clients = []
        for row in rows:
            clients.append({
                'mac': row['mac_address'],
                'ip': row['ip_address'],
                'lastSeen': row['last_seen'],
                'firstSeen': row['first_seen'],
                'recentDeviceConnection': row['connection_type'],
                'network': {'id': row['network_id'], 'name': row['network_name']},
                'description': row['description'],
                'vlan': row['vlan'],
                'ssid': row['ssid'],
                'manufacturer': row['manufacturer']
            })

        return clients

    def get_date_range(self):
        """
        Get the earliest and latest dates in the database.

        Returns:
            tuple: (earliest_date, latest_date) as ISO strings
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT MIN(last_seen) as earliest, MAX(last_seen) as latest
            FROM clients
        ''')
        row = cursor.fetchone()
        return row['earliest'], row['latest']

    def get_collection_runs(self):
        """
        Get information about all collection runs.

        Returns:
            list: Collection run records
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM collection_runs
            ORDER BY run_timestamp DESC
        ''')

        runs = []
        for row in cursor.fetchall():
            runs.append({
                'id': row['id'],
                'run_timestamp': row['run_timestamp'],
                'organization_id': row['organization_id'],
                'organization_name': row['organization_name'],
                'clients_collected': row['clients_collected'],
                'timespan_days': row['timespan_days']
            })

        return runs

    def get_stats(self):
        """
        Get database statistics.

        Returns:
            dict: Database statistics
        """
        cursor = self.conn.cursor()

        cursor.execute('SELECT COUNT(*) as total FROM clients')
        total_records = cursor.fetchone()['total']

        cursor.execute('SELECT COUNT(DISTINCT mac_address) as unique_macs FROM clients')
        unique_macs = cursor.fetchone()['unique_macs']

        cursor.execute('SELECT COUNT(*) as runs FROM collection_runs')
        collection_runs = cursor.fetchone()['runs']

        earliest, latest = self.get_date_range()

        return {
            'total_records': total_records,
            'unique_mac_addresses': unique_macs,
            'collection_runs': collection_runs,
            'earliest_date': earliest,
            'latest_date': latest
        }

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.logger.info("Database connection closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
