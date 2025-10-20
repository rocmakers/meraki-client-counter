"""
Configuration management module for Meraki Average Client Device Counter.
Handles loading, saving, and prompting for API credentials.
"""

import json
import os
import sys
from pathlib import Path


class Config:
    """Manages application configuration including API credentials."""

    CONFIG_FILE = ".meraki_config.json"
    GITIGNORE_FILE = ".gitignore"

    def __init__(self):
        self.api_key = None
        self.organization_id = None
        self.log_level = "INFO"
        self.config_path = Path(__file__).parent / self.CONFIG_FILE

    def load(self, reconfigure=False):
        """
        Load configuration from file or prompt user if not found.

        Args:
            reconfigure: If True, prompt for new credentials even if config exists

        Returns:
            bool: True if configuration loaded successfully
        """
        if reconfigure or not self.config_path.exists():
            return self._prompt_and_save()

        try:
            with open(self.config_path, 'r') as f:
                config_data = json.load(f)

            self.api_key = config_data.get('api_key')
            self.organization_id = config_data.get('organization_id')
            self.log_level = config_data.get('log_level', 'INFO')

            if not self.api_key or not self.organization_id:
                print("Configuration file is incomplete.")
                return self._prompt_and_save()

            return True

        except (json.JSONDecodeError, IOError) as e:
            print(f"Error reading configuration file: {e}")
            return self._prompt_and_save()

    def _prompt_and_save(self):
        """
        Prompt user for configuration details and save to file.

        Returns:
            bool: True if configuration saved successfully
        """
        print("\nMeraki configuration not found or incomplete.")
        print("Please enter your Meraki credentials:\n")

        # Prompt for API key
        self.api_key = input("Meraki API key: ").strip()
        if not self.api_key:
            print("Error: API key cannot be empty.")
            return False

        # Prompt for Organization ID
        self.organization_id = input("Organization ID: ").strip()
        if not self.organization_id:
            print("Error: Organization ID cannot be empty.")
            return False

        # Optional: log level
        log_input = input("Log level (INFO/DEBUG/WARNING/ERROR) [INFO]: ").strip().upper()
        if log_input in ['DEBUG', 'WARNING', 'ERROR']:
            self.log_level = log_input
        else:
            self.log_level = 'INFO'

        # Save configuration
        return self._save()

    def _save(self):
        """
        Save current configuration to file.

        Returns:
            bool: True if saved successfully
        """
        config_data = {
            'api_key': self.api_key,
            'organization_id': self.organization_id,
            'log_level': self.log_level
        }

        try:
            with open(self.config_path, 'w') as f:
                json.dump(config_data, f, indent=4)

            # Ensure config file is in .gitignore
            self._ensure_gitignore()

            print(f"\nConfiguration saved to {self.config_path}")
            return True

        except IOError as e:
            print(f"Error saving configuration: {e}")
            return False

    def _ensure_gitignore(self):
        """
        Ensure the config file is listed in .gitignore.
        """
        gitignore_path = Path(__file__).parent / self.GITIGNORE_FILE
        config_entry = self.CONFIG_FILE

        # Check if .gitignore exists and contains our config file
        content = ""
        if gitignore_path.exists():
            with open(gitignore_path, 'r') as f:
                content = f.read()
                if config_entry in content:
                    return  # Already in .gitignore

        # Add to .gitignore
        try:
            with open(gitignore_path, 'a') as f:
                if content and not content.endswith('\n'):
                    f.write('\n')
                f.write(f"# Meraki configuration with credentials\n")
                f.write(f"{config_entry}\n")
        except IOError as e:
            print(f"Warning: Could not update .gitignore: {e}")

    def get_api_key(self):
        """Get the API key."""
        return self.api_key

    def get_organization_id(self):
        """Get the organization ID."""
        return self.organization_id

    def get_log_level(self):
        """Get the log level."""
        return self.log_level
