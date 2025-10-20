"""
Meraki Dashboard API client module.
Handles all API interactions with rate limiting and error handling.
"""

import requests
import time
import logging
from datetime import datetime, timedelta


class MerakiClient:
    """Client for interacting with Meraki Dashboard API."""

    BASE_URL = "https://api.meraki.com/api/v1"
    RATE_LIMIT_DELAY = 0.1  # 10 calls per second = 0.1s between calls

    def __init__(self, api_key):
        """
        Initialize the Meraki API client.

        Args:
            api_key: Meraki Dashboard API key
        """
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'X-Cisco-Meraki-API-Key': self.api_key,
            'Content-Type': 'application/json'
        })
        self.last_request_time = 0
        self.logger = logging.getLogger(__name__)

    def _rate_limit(self):
        """Ensure we don't exceed rate limits (10 calls/second)."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.RATE_LIMIT_DELAY:
            time.sleep(self.RATE_LIMIT_DELAY - elapsed)
        self.last_request_time = time.time()

    def _make_request(self, method, endpoint, params=None, max_retries=3):
        """
        Make an API request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            max_retries: Maximum number of retry attempts

        Returns:
            Response data as dict or list

        Raises:
            Exception: If request fails after all retries
        """
        url = f"{self.BASE_URL}{endpoint}"

        for attempt in range(max_retries):
            self._rate_limit()

            try:
                response = self.session.request(method, url, params=params)

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:  # Rate limited
                    retry_after = int(response.headers.get('Retry-After', 2))
                    self.logger.warning(f"Rate limited. Retrying after {retry_after}s")
                    time.sleep(retry_after)
                    continue
                elif response.status_code == 404:
                    self.logger.error(f"Resource not found: {endpoint}")
                    return None
                else:
                    self.logger.error(f"API error {response.status_code}: {response.text}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    response.raise_for_status()

            except requests.exceptions.RequestException as e:
                self.logger.error(f"Request failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise

        raise Exception(f"Failed to complete request after {max_retries} attempts")

    def get_organization(self, org_id):
        """
        Get organization details.

        Args:
            org_id: Organization ID

        Returns:
            dict: Organization details
        """
        endpoint = f"/organizations/{org_id}"
        return self._make_request('GET', endpoint)

    def get_organization_networks(self, org_id):
        """
        Get all networks in an organization.

        Args:
            org_id: Organization ID

        Returns:
            list: List of networks
        """
        endpoint = f"/organizations/{org_id}/networks"
        return self._make_request('GET', endpoint)

    def get_clients_in_timespan(self, org_id, timespan):
        """
        Get all clients seen in organization during timespan.
        Note: This queries each network individually as there's no org-level endpoint
        for listing all clients.

        Args:
            org_id: Organization ID
            timespan: Timespan in seconds (max 2592000 = 30 days)

        Returns:
            list: List of client records
        """
        # First, get all networks in the organization
        self.logger.info("Fetching networks...")
        networks = self.get_organization_networks(org_id)

        if not networks:
            self.logger.warning("No networks found in organization")
            return []

        self.logger.info(f"Found {len(networks)} networks")

        # Query clients from each network
        all_clients = []
        for network in networks:
            network_id = network['id']
            network_name = network.get('name', 'Unknown')

            self.logger.debug(f"Fetching clients for network: {network_name}")

            endpoint = f"/networks/{network_id}/clients"
            params = {'timespan': timespan, 'perPage': 1000}

            page = 1
            while True:
                clients = self._make_request('GET', endpoint, params=params)

                if not clients:
                    break

                all_clients.extend(clients)

                # Check if there are more pages
                if len(clients) < 1000:
                    break

                # Update params for next page
                params['startingAfter'] = clients[-1]['mac']
                page += 1

        self.logger.info(f"Retrieved {len(all_clients)} total client records across all networks")
        return all_clients

    def get_clients_with_timestamps(self, org_id, t0, t1):
        """
        Get all clients seen in organization between t0 and t1.

        Args:
            org_id: Organization ID
            t0: Start time (ISO 8601 or Unix timestamp)
            t1: End time (ISO 8601 or Unix timestamp)

        Returns:
            list: List of client records
        """
        endpoint = f"/organizations/{org_id}/clients/search"
        params = {'t0': t0, 't1': t1, 'perPage': 1000}

        all_clients = []
        page = 1

        while True:
            self.logger.debug(f"Fetching clients page {page} for period {t0} to {t1}...")
            clients = self._make_request('GET', endpoint, params=params)

            if not clients:
                break

            all_clients.extend(clients)

            if len(clients) < 1000:
                break

            params['startingAfter'] = clients[-1]['mac']
            page += 1

        return all_clients

    def get_network_client_tracking(self, network_id):
        """
        Get client tracking method for a network (if available).

        Args:
            network_id: Network ID

        Returns:
            dict: Client tracking settings or None if not available
        """
        # Try MX client tracking settings
        endpoint = f"/networks/{network_id}/clients/trackingSettings"
        result = self._make_request('GET', endpoint)

        if result:
            return result

        # Try wireless settings as fallback
        endpoint = f"/networks/{network_id}/wireless/settings"
        return self._make_request('GET', endpoint)

    def get_organization_clients_overview(self, org_id, timespan):
        """
        Get overview of client data usage.

        Args:
            org_id: Organization ID
            timespan: Timespan in seconds

        Returns:
            dict: Client overview data
        """
        endpoint = f"/organizations/{org_id}/clients/overview"
        params = {'timespan': timespan}
        return self._make_request('GET', endpoint, params=params)
