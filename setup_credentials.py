#!/usr/bin/env python3
"""Setup script to store credentials in macOS Keychain.

Run this once to securely store sensitive credentials.
"""

import keyring
import getpass


def main():
    """Prompt user for credentials and store in Keychain."""
    print("XDigest Credential Setup")
    print("=" * 50)
    print("\nThis script will store your credentials securely in macOS Keychain.")
    print("Credentials will never be stored in code or git.\n")

    # X Credentials
    print("X (Twitter) Credentials:")
    x_username = input("  X username: ").strip()
    x_password = getpass.getpass("  X password: ")

    # Gemini API Key
    print("\nGoogle Gemini API:")
    print("  Get your API key from: https://aistudio.google.com/app/apikey")
    gemini_api_key = getpass.getpass("  Gemini API key: ")

    # SMTP Credentials
    print("\nSMTP Email Configuration:")
    print("  For Gmail, create an app password: https://support.google.com/accounts/answer/185833")
    smtp_password = getpass.getpass("  SMTP password: ")

    # Store in Keychain
    print("\nStoring credentials in macOS Keychain...")
    keyring.set_password('xdigest', 'x_username', x_username)
    keyring.set_password('xdigest', 'x_password', x_password)
    keyring.set_password('xdigest', 'gemini_api_key', gemini_api_key)
    keyring.set_password('xdigest', 'smtp_password', smtp_password)

    print("✓ Credentials stored successfully!")
    print("\nNext steps:")
    print("  1. Copy .env.example to .env: cp .env.example .env")
    print("  2. Edit .env with your email and account settings")
    print("  3. Run the app: python main.py")


if __name__ == '__main__':
    main()
