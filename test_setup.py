#!/usr/bin/env python3
"""Diagnostic script to test XDigest setup components.

Run this to identify what's failing during setup.
"""

import sys
import asyncio
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_1_imports():
    """Test 1: Check if all required packages are installed."""
    print("\n" + "="*60)
    print("TEST 1: Checking Python imports")
    print("="*60)

    required_packages = [
        'playwright',
        'keyring',
        'dotenv',
        'sqlite3',
    ]

    failed = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package}")
        except ImportError as e:
            print(f"✗ {package}: {e}")
            failed.append(package)

    if failed:
        print(f"\n❌ Missing packages: {', '.join(failed)}")
        print("Run: pip install -r requirements.txt")
        return False

    print("\n✅ All imports successful")
    return True


def test_2_chrome_cdp():
    """Test 2: Check if Chrome CDP is accessible."""
    print("\n" + "="*60)
    print("TEST 2: Checking Chrome CDP connection")
    print("="*60)

    import socket

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('localhost', 9222))
        sock.close()

        if result == 0:
            print("✓ Chrome debugging port 9222 is open")
            print("\n✅ Chrome CDP is running")
            return True
        else:
            print("✗ Cannot connect to port 9222")
            print("\n❌ Chrome CDP is NOT running")
            print("\nTo fix, run in another terminal:")
            print('/Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \\')
            print('  --remote-debugging-port=9222 \\')
            print('  --user-data-dir="$HOME/chrome-xdigest"')
            return False
    except Exception as e:
        print(f"✗ Error checking port: {e}")
        return False


async def test_3_playwright_cdp():
    """Test 3: Check if Playwright can connect to Chrome CDP."""
    print("\n" + "="*60)
    print("TEST 3: Testing Playwright CDP connection")
    print("="*60)

    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            print("✓ Playwright initialized")

            try:
                browser = await p.chromium.connect_over_cdp("http://localhost:9222")
                print("✓ Connected to Chrome via CDP")

                contexts = browser.contexts
                print(f"✓ Found {len(contexts)} browser context(s)")

                if contexts:
                    context = contexts[0]
                    pages = context.pages
                    print(f"✓ Found {len(pages)} page(s)")

                    if pages:
                        page = pages[0]
                        url = page.url
                        print(f"✓ Current page URL: {url}")

                await browser.close()
                print("\n✅ Playwright CDP connection successful")
                return True

            except Exception as e:
                print(f"✗ Failed to connect to Chrome: {e}")
                print("\n❌ Playwright cannot connect to Chrome")
                print("\nMake sure Chrome is running with:")
                print("  --remote-debugging-port=9222")
                return False

    except Exception as e:
        print(f"✗ Playwright error: {e}")
        return False


async def test_4_x_login_status():
    """Test 4: Check if logged into X."""
    print("\n" + "="*60)
    print("TEST 4: Checking X login status")
    print("="*60)

    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            print("✓ Connected to Chrome")

            contexts = browser.contexts
            if not contexts:
                print("✗ No browser contexts found")
                print("\n❌ Open Chrome and navigate to x.com")
                return False

            context = contexts[0]
            pages = context.pages

            # Try to find an existing X page or create new one
            x_page = None
            for page in pages:
                if 'x.com' in page.url or 'twitter.com' in page.url:
                    x_page = page
                    print(f"✓ Found X page: {page.url}")
                    break

            if not x_page:
                print("⚠ No X page found, creating new page...")
                x_page = await context.new_page()
                await x_page.goto('https://x.com', timeout=30000)
                await asyncio.sleep(2)

            # Check if logged in by looking for common elements
            url = x_page.url
            print(f"✓ Current URL: {url}")

            # Check for login indicators
            try:
                # Wait a bit for page to load
                await asyncio.sleep(2)

                # Check if we're on login page
                if '/login' in url or '/i/flow/login' in url:
                    print("✗ Currently on login page")
                    print("\n❌ NOT logged into X")
                    print("\nPlease log into X in the Chrome window")
                    await browser.close()
                    return False

                # Try to find home timeline or user menu
                content = await x_page.content()

                if 'login' in content.lower() and 'sign up' in content.lower():
                    print("✗ Page shows login/signup prompts")
                    print("\n❌ NOT logged into X")
                    print("\nPlease log into X in the Chrome window")
                else:
                    print("✓ Page appears to be logged in")
                    print("\n✅ Logged into X")
                    await browser.close()
                    return True

            except Exception as e:
                print(f"⚠ Could not verify login status: {e}")
                print("Please manually verify you're logged into X")

            await browser.close()
            return False

    except Exception as e:
        print(f"✗ Error checking X login: {e}")
        return False


async def test_5_fetch_following():
    """Test 5: Try to fetch following list."""
    print("\n" + "="*60)
    print("TEST 5: Testing following list fetch")
    print("="*60)

    try:
        from scraper.x_scraper import XScraper
        from storage.db import Database

        print("✓ Imported XScraper")

        # Create temporary database
        db = Database(':memory:')
        print("✓ Created temporary database")

        # Create scraper
        scraper = XScraper(
            db=db,
            headless=False,
            browser_data_path=None,
            use_cdp=True,
        )
        print("✓ Created XScraper instance")

        print("\n⏳ Fetching following list (this may take 30-60 seconds)...")
        following = await scraper.get_following_accounts()

        if following:
            print(f"\n✅ Successfully fetched {len(following)} accounts!")
            print("\nFirst 10 accounts:")
            for i, account in enumerate(following[:10], 1):
                print(f"  {i}. @{account}")
            if len(following) > 10:
                print(f"  ... and {len(following) - 10} more")
            return True
        else:
            print("\n❌ No accounts fetched")
            print("\nPossible reasons:")
            print("  - Not logged into X")
            print("  - X page structure changed")
            print("  - Network issues")
            return False

    except Exception as e:
        print(f"\n✗ Error fetching following list: {e}")
        print(f"\nFull error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all diagnostic tests."""
    print("\n" + "="*60)
    print("XDigest Setup Diagnostics")
    print("="*60)
    print("\nThis script will test each component of the setup process.")
    print("Press Ctrl+C to cancel at any time.\n")

    results = {}

    # Test 1: Imports
    results['imports'] = test_1_imports()
    if not results['imports']:
        print("\n⛔ Cannot continue without required packages")
        return

    # Test 2: Chrome CDP
    results['chrome_cdp'] = test_2_chrome_cdp()
    if not results['chrome_cdp']:
        print("\n⛔ Cannot continue without Chrome CDP")
        return

    # Test 3: Playwright CDP
    results['playwright_cdp'] = await test_3_playwright_cdp()
    if not results['playwright_cdp']:
        print("\n⛔ Cannot continue without Playwright connection")
        return

    # Test 4: X login
    results['x_login'] = await test_4_x_login_status()
    if not results['x_login']:
        print("\n⛔ Cannot continue without X login")
        return

    # Test 5: Fetch following
    results['fetch_following'] = await test_5_fetch_following()

    # Summary
    print("\n" + "="*60)
    print("DIAGNOSTIC SUMMARY")
    print("="*60)
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    all_passed = all(results.values())
    if all_passed:
        print("\n🎉 All tests passed! You can now run setup_config.py")
    else:
        print("\n⚠️  Some tests failed. Fix the issues above before running setup_config.py")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Diagnostics cancelled by user")
        sys.exit(1)
