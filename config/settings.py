"""Settings loader for XDigest.

Loads configuration from .env file and secrets from macOS Keychain.
"""

import os
from pathlib import Path
from typing import List
import keyring
from dotenv import load_dotenv


class Settings:
    """Application settings."""

    def __init__(self):
        # Load .env file
        env_path = Path(__file__).parent.parent / '.env'
        load_dotenv(env_path)

        # X Configuration
        self.follow_accounts: List[str] = os.getenv('FOLLOW_ACCOUNTS', '').split(',')
        self.follow_accounts = [acc.strip() for acc in self.follow_accounts if acc.strip()]

        # Email Configuration
        self.email_to = os.getenv('EMAIL_TO')
        self.email_from = os.getenv('EMAIL_FROM')
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))

        # Storage Paths
        self.db_path = Path(os.getenv('DB_PATH', '~/.xdigest/xdigest.db')).expanduser()
        self.log_path = Path(os.getenv('LOG_PATH', '~/.xdigest/logs/')).expanduser()
        self.browser_data_path = Path(os.getenv('BROWSER_DATA_PATH', '~/.xdigest/browser/')).expanduser()

        # Scraping Configuration
        self.headless = os.getenv('HEADLESS', 'true').lower() == 'true'
        self.max_posts_per_account = int(os.getenv('MAX_POSTS_PER_ACCOUNT', '50'))

        # Create directories if they don't exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path.mkdir(parents=True, exist_ok=True)
        self.browser_data_path.mkdir(parents=True, exist_ok=True)

        # Load secrets from Keychain
        self._load_secrets()

        # Validate required settings
        self._validate()

    def _load_secrets(self):
        """Load sensitive credentials from macOS Keychain."""
        self.x_username = keyring.get_password('xdigest', 'x_username')
        self.x_password = keyring.get_password('xdigest', 'x_password')
        self.gemini_api_key = keyring.get_password('xdigest', 'gemini_api_key')
        self.smtp_password = keyring.get_password('xdigest', 'smtp_password')

    def _validate(self):
        """Validate that all required settings are present."""
        errors = []

        if not self.follow_accounts:
            errors.append("FOLLOW_ACCOUNTS not set in .env")

        if not self.email_to:
            errors.append("EMAIL_TO not set in .env")

        if not self.email_from:
            errors.append("EMAIL_FROM not set in .env")

        if not self.x_username:
            errors.append("X username not found in Keychain (run setup_credentials.py)")

        if not self.x_password:
            errors.append("X password not found in Keychain (run setup_credentials.py)")

        if not self.gemini_api_key:
            errors.append("Gemini API key not found in Keychain (run setup_credentials.py)")

        if not self.smtp_password:
            errors.append("SMTP password not found in Keychain (run setup_credentials.py)")

        if errors:
            raise ValueError("Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))


# Lazy-loaded global settings instance
_settings = None


def get_settings() -> Settings:
    """Get or create the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
