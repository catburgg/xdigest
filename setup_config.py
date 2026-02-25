#!/usr/bin/env python3
"""One-time configuration setup for XDigest.

Run this script once to configure all settings:
- Environment variables
- API keys (stored securely in macOS Keychain)
- Email settings
- Follow accounts

Usage:
    python setup_config.py
"""

import os
import sys
import keyring
import asyncio
from pathlib import Path


def get_input(prompt: str, default: str = None, required: bool = True) -> str:
    """Get user input with optional default value."""
    if default:
        prompt = f"{prompt} [{default}]"
    prompt += ": "

    while True:
        value = input(prompt).strip()
        if not value and default:
            return default
        if value or not required:
            return value
        print("This field is required. Please enter a value.")


def get_multiline_input(prompt: str) -> str:
    """Get multiline input (for follow accounts)."""
    print(f"\n{prompt}")
    print("Enter account usernames (one per line, without @).")
    print("Press Enter twice when done:")

    accounts = []
    while True:
        line = input().strip()
        if not line:
            if accounts:
                break
            print("Please enter at least one account.")
            continue
        # Remove @ if user included it
        account = line.lstrip('@')
        accounts.append(account)

    return ','.join(accounts)


async def fetch_following_accounts() -> list:
    """Fetch all following accounts from X using CDP mode."""
    print("\n--- Fetching Your Following List from X ---")
    print("This will open Chrome and scrape your following list.")
    print("Make sure Chrome is running with debugging port 9222.")
    print("\nIf Chrome is not running, open a new terminal and run:")
    print('/Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \\')
    print('  --remote-debugging-port=9222 \\')
    print('  --user-data-dir="$HOME/chrome-xdigest"')

    proceed = input("\nIs Chrome running with debugging? (y/n): ").strip().lower()
    if proceed != 'y':
        print("Please start Chrome first, then run this script again.")
        return []

    try:
        # Import here to avoid dependency issues
        from scraper.x_scraper import XScraper
        from storage.db import Database

        # Create temporary database
        db = Database(':memory:')

        # Create scraper with CDP mode
        scraper = XScraper(
            db=db,
            headless=False,
            browser_data_path=str(Path.home() / 'chrome-xdigest'),
            use_cdp=True,
        )

        print("\nFetching following list... This may take a minute.")
        following = await scraper.get_following_accounts()

        if following:
            print(f"\n✓ Found {len(following)} accounts you're following:")
            for i, account in enumerate(following[:10], 1):
                print(f"  {i}. @{account}")
            if len(following) > 10:
                print(f"  ... and {len(following) - 10} more")
        else:
            print("\n✗ Could not fetch following list. You may need to log in first.")

        return following

    except Exception as e:
        print(f"\n✗ Error fetching following list: {e}")
        print("You can manually enter accounts instead.")
        return []


def main():
    print("=" * 60)
    print("XDigest Configuration Setup")
    print("=" * 60)
    print("\nThis script will help you configure XDigest.")
    print("All sensitive data (API keys, passwords) will be stored")
    print("securely in macOS Keychain.\n")

    # Create .env file path
    env_file = Path(__file__).parent / '.env'

    # Collect configuration
    config = {}

    print("\n--- Email Settings ---")
    config['EMAIL_FROM'] = get_input("Your email address (sender)")
    config['EMAIL_TO'] = get_input("Recipient email address", default=config['EMAIL_FROM'])
    config['SMTP_HOST'] = get_input("SMTP server", default="smtp.gmail.com")
    config['SMTP_PORT'] = get_input("SMTP port", default="587")

    print("\n--- SMTP Password ---")
    print("For Gmail, use an App Password (not your regular password):")
    print("  https://support.google.com/accounts/answer/185833")
    print("For QQ Mail, use Authorization Code:")
    print("  Settings → Account → Generate Authorization Code")
    smtp_password = get_input("SMTP password (will be stored in Keychain)")

    print("\n--- Gemini API Key ---")
    print("Get your API key from: https://aistudio.google.com/app/apikey")
    gemini_api_key = get_input("Gemini API key (will be stored in Keychain)")

    print("\n--- X (Twitter) Accounts to Follow ---")
    print("Choose how to add accounts:")
    print("  1. Automatically load from your X following list (recommended)")
    print("  2. Manually enter account names")

    choice = get_input("Enter choice (1 or 2)", default="1")

    if choice == "1":
        # Try to fetch following accounts
        following = asyncio.run(fetch_following_accounts())
        if following:
            print(f"\nLoaded {len(following)} accounts from your following list.")
            use_all = get_input("Use all these accounts? (y/n)", default="y")
            if use_all.lower() == 'y':
                follow_accounts = ','.join(following)
            else:
                print("\nYou can manually select which accounts to include.")
                follow_accounts = get_multiline_input("Enter accounts to follow")
        else:
            print("\nFalling back to manual entry.")
            follow_accounts = get_multiline_input("Enter accounts to follow")
    else:
        follow_accounts = get_multiline_input("Enter accounts to follow")

    config['FOLLOW_ACCOUNTS'] = follow_accounts

    print("\n--- Optional Settings ---")
    config['HEADLESS'] = get_input("Run browser in headless mode? (true/false)", default="true", required=False)
    config['DB_PATH'] = get_input("Database path", default="~/.xdigest/xdigest.db", required=False)
    config['LOG_PATH'] = get_input("Log directory", default="~/.xdigest/logs/", required=False)
    config['BROWSER_DATA_PATH'] = get_input("Browser data path", default="~/.xdigest/browser/", required=False)

    # Write .env file
    print("\n--- Saving Configuration ---")
    with open(env_file, 'w') as f:
        f.write("# XDigest Configuration\n")
        f.write("# Generated by setup_config.py\n\n")
        for key, value in config.items():
            if value:  # Only write non-empty values
                f.write(f"{key}={value}\n")

    print(f"✓ Configuration saved to: {env_file}")

    # Store secrets in Keychain
    print("\n--- Storing Secrets in Keychain ---")
    try:
        keyring.set_password('xdigest', 'smtp_password', smtp_password)
        print("✓ SMTP password stored in Keychain")

        keyring.set_password('xdigest', 'gemini_api_key', gemini_api_key)
        print("✓ Gemini API key stored in Keychain")
    except Exception as e:
        print(f"✗ Error storing secrets: {e}")
        sys.exit(1)

    # Create directories
    print("\n--- Creating Directories ---")
    db_path = Path(config.get('DB_PATH', '~/.xdigest/xdigest.db')).expanduser()
    log_path = Path(config.get('LOG_PATH', '~/.xdigest/logs/')).expanduser()
    browser_path = Path(config.get('BROWSER_DATA_PATH', '~/.xdigest/browser/')).expanduser()

    db_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.mkdir(parents=True, exist_ok=True)
    browser_path.mkdir(parents=True, exist_ok=True)

    print(f"✓ Created: {db_path.parent}")
    print(f"✓ Created: {log_path}")
    print(f"✓ Created: {browser_path}")

    print("\n" + "=" * 60)
    print("✓ Configuration Complete!")
    print("=" * 60)
    print("\nYou can now run XDigest:")
    print("  python main.py --use-chrome")
    print("\nTo reconfigure, run this script again:")
    print("  python setup_config.py")
    print()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nConfiguration cancelled.")
        sys.exit(1)
