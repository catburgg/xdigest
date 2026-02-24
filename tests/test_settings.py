"""Unit tests for config/settings.py — Configuration loader."""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


def _make_settings(env_vars):
    """Helper: reload settings module with mocked keyring and env, return fresh Settings."""
    # Remove cached module so we get a clean import
    for mod_name in list(sys.modules):
        if mod_name.startswith('config'):
            del sys.modules[mod_name]

    with patch.dict(os.environ, env_vars, clear=False):
        with patch('keyring.get_password', return_value='dummy_value'):
            from config.settings import Settings
            return Settings()


def _make_settings_no_keychain(env_vars):
    """Helper: reload settings with keyring returning None."""
    for mod_name in list(sys.modules):
        if mod_name.startswith('config'):
            del sys.modules[mod_name]

    with patch.dict(os.environ, env_vars, clear=False):
        with patch('keyring.get_password', return_value=None):
            from config.settings import Settings
            return Settings


VALID_ENV = {
    'FOLLOW_ACCOUNTS': 'user1,user2,user3',
    'EMAIL_TO': 'test@example.com',
    'EMAIL_FROM': 'digest@example.com',
    'SMTP_HOST': 'smtp.gmail.com',
    'SMTP_PORT': '587',
    'DB_PATH': '/tmp/test_xdigest/test.db',
    'LOG_PATH': '/tmp/test_xdigest/logs/',
    'BROWSER_DATA_PATH': '/tmp/test_xdigest/browser/',
    'HEADLESS': 'true',
    'MAX_POSTS_PER_ACCOUNT': '50',
}


class TestSettingsLoading:
    """Test settings loading from env and keychain."""

    def test_loads_follow_accounts(self):
        """Test that FOLLOW_ACCOUNTS is parsed correctly."""
        s = _make_settings(VALID_ENV)
        assert s.follow_accounts == ['user1', 'user2', 'user3']

    def test_loads_email_config(self):
        """Test email configuration loading."""
        s = _make_settings(VALID_ENV)
        assert s.email_to == 'test@example.com'
        assert s.email_from == 'digest@example.com'
        assert s.smtp_host == 'smtp.gmail.com'
        assert s.smtp_port == 587

    def test_loads_scraping_config(self):
        """Test scraping configuration loading."""
        s = _make_settings(VALID_ENV)
        assert s.headless is True
        assert s.max_posts_per_account == 50

    def test_loads_keychain_secrets(self):
        """Test that secrets are loaded from Keychain."""
        s = _make_settings(VALID_ENV)
        assert s.x_username == 'dummy_value'
        assert s.x_password == 'dummy_value'
        assert s.gemini_api_key == 'dummy_value'
        assert s.smtp_password == 'dummy_value'

    def test_missing_keychain_raises_error(self):
        """Test that missing Keychain credentials raise ValueError."""
        SettingsClass = _make_settings_no_keychain(VALID_ENV)
        with pytest.raises(ValueError, match="Configuration errors"):
            SettingsClass()

    def test_empty_follow_accounts_raises_error(self):
        """Test that empty FOLLOW_ACCOUNTS raises ValueError."""
        env = {**VALID_ENV, 'FOLLOW_ACCOUNTS': ''}

        for mod_name in list(sys.modules):
            if mod_name.startswith('config'):
                del sys.modules[mod_name]

        with patch.dict(os.environ, env, clear=False):
            with patch('keyring.get_password', return_value=None):
                from config.settings import Settings
                with pytest.raises(ValueError, match="FOLLOW_ACCOUNTS"):
                    Settings()
