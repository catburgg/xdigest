"""Playwright-based X (Twitter) scraper.

Handles:
- Manual login via visible browser (--login mode)
- Session cookie persistence in SQLite
- Post extraction from followed accounts
- Stealth mode to avoid anti-bot detection
"""

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import List, Dict, Optional
from dataclasses import dataclass, field, asdict

from playwright.async_api import async_playwright, Page, BrowserContext
from playwright_stealth import Stealth

from storage.db import Database

logger = logging.getLogger(__name__)

X_BASE_URL = "https://x.com"
LOGIN_URL = f"{X_BASE_URL}/i/flow/login"
HOME_URL = f"{X_BASE_URL}/home"

# Selectors using data-testid (more stable than CSS classes)
SELECTORS = {
    'tweet': 'article[data-testid="tweet"]',
    'tweet_text': '[data-testid="tweetText"]',
    'tweet_time': 'time',
    'tweet_link': 'a[href*="/status/"]',
    'tweet_media_image': '[data-testid="tweetPhoto"]',
    'tweet_media_video': '[data-testid="videoPlayer"]',
}


@dataclass
class Post:
    """Represents a scraped X post."""
    post_id: str
    account: str
    content: str = ""
    post_timestamp: Optional[str] = None
    urls: List[str] = field(default_factory=list)
    has_link: bool = False
    has_video: bool = False
    has_image: bool = False

    def to_dict(self) -> Dict:
        return asdict(self)


class XScraper:
    """Scrapes posts from X using Playwright."""

    def __init__(self, db: Database, headless: bool = True, browser_data_path: str = None):
        self.db = db
        self.headless = headless
        self.browser_data_path = browser_data_path
        self._browser = None
        self._context = None
        self._page = None

    async def _launch_browser(self, playwright, headless: bool = None):
        """Launch browser with stealth mode."""
        use_headless = headless if headless is not None else self.headless

        self._browser = await playwright.chromium.launch(
            headless=use_headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
            ]
        )

        self._context = await self._browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent=(
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/131.0.0.0 Safari/537.36'
            ),
            locale='en-US',
        )

        self._page = await self._context.new_page()
        stealth = Stealth()
        await stealth.apply_stealth_async(self._page)

        return self._page

    async def _restore_cookies(self) -> bool:
        """Restore saved session cookies. Returns True if cookies were loaded."""
        cookies = self.db.get_session_cookies()
        if cookies:
            await self._context.add_cookies(cookies)
            logger.info(f"Restored {len(cookies)} session cookies")
            return True
        return False

    async def _save_cookies(self):
        """Save current session cookies to database."""
        cookies = await self._context.cookies()
        self.db.save_session_cookies(cookies)
        logger.info(f"Saved {len(cookies)} session cookies")

    async def _is_logged_in(self) -> bool:
        """Check if we're logged in by navigating to home."""
        try:
            await self._page.goto(HOME_URL, wait_until='domcontentloaded', timeout=15000)
            await self._page.wait_for_timeout(3000)

            # If redirected to login page, we're not logged in
            current_url = self._page.url
            if '/login' in current_url or '/i/flow/login' in current_url:
                return False

            # Check for home timeline indicators
            try:
                await self._page.wait_for_selector(
                    SELECTORS['tweet'], timeout=10000
                )
                return True
            except Exception:
                return False
        except Exception as e:
            logger.warning(f"Login check failed: {e}")
            return False

    async def manual_login(self):
        """Launch visible browser for user to log in manually.

        Opens X login page in a visible browser window.
        User completes login (handles CAPTCHA, 2FA, etc).
        Saves session cookies once logged in.
        """
        async with async_playwright() as p:
            # Always visible for manual login
            await self._launch_browser(p, headless=False)

            logger.info("Opening X login page in browser...")
            logger.info("Please log in manually. The browser will close automatically once login is detected.")

            await self._page.goto(LOGIN_URL, wait_until='domcontentloaded')

            # Poll until user completes login
            print("\n" + "=" * 60)
            print("  MANUAL LOGIN REQUIRED")
            print("  Please log in to X in the browser window.")
            print("  This window will close automatically after login.")
            print("=" * 60 + "\n")

            max_wait = 300  # 5 minutes
            poll_interval = 3
            waited = 0

            while waited < max_wait:
                await self._page.wait_for_timeout(poll_interval * 1000)
                waited += poll_interval

                current_url = self._page.url
                # Check if we've left the login flow
                if '/home' in current_url or (
                    '/login' not in current_url
                    and '/i/flow' not in current_url
                    and 'x.com' in current_url
                ):
                    # Verify by checking for tweet content
                    try:
                        await self._page.goto(HOME_URL, wait_until='domcontentloaded')
                        await self._page.wait_for_timeout(3000)
                        await self._page.wait_for_selector(SELECTORS['tweet'], timeout=10000)

                        # Login successful
                        await self._save_cookies()
                        print("\n✓ Login successful! Session cookies saved.")
                        logger.info("Manual login completed successfully")
                        break
                    except Exception:
                        continue

            else:
                print("\n✗ Login timed out after 5 minutes.")
                logger.error("Manual login timed out")

            await self._browser.close()

    async def scrape_accounts(
        self, accounts: List[str], since: Optional[datetime] = None
    ) -> List[Post]:
        """Scrape posts from multiple accounts.

        Args:
            accounts: List of X usernames to scrape
            since: Only collect posts newer than this timestamp

        Returns:
            List of Post objects
        """
        all_posts = []

        async with async_playwright() as p:
            await self._launch_browser(p)

            # Try to restore cookies
            has_cookies = await self._restore_cookies()
            if not has_cookies:
                logger.error("No session cookies found. Run with --login first.")
                await self._browser.close()
                return []

            # Verify login
            if not await self._is_logged_in():
                logger.error("Session expired. Run with --login to re-authenticate.")
                await self._browser.close()
                return []

            logger.info("Session valid, starting scrape...")

            for account in accounts:
                try:
                    posts = await self._scrape_account(account, since)
                    all_posts.extend(posts)
                    logger.info(f"@{account}: scraped {len(posts)} new posts")

                    # Random delay between accounts (2-5 seconds)
                    import random
                    delay = random.uniform(2, 5)
                    await self._page.wait_for_timeout(int(delay * 1000))

                except Exception as e:
                    logger.error(f"Error scraping @{account}: {e}")
                    continue

            # Save updated cookies
            await self._save_cookies()
            await self._browser.close()

        return all_posts

    async def _scrape_account(
        self, account: str, since: Optional[datetime] = None
    ) -> List[Post]:
        """Scrape posts from a single account.

        Args:
            account: X username
            since: Only collect posts newer than this

        Returns:
            List of Post objects
        """
        url = f"{X_BASE_URL}/{account}"
        logger.info(f"Scraping @{account}: {url}")

        await self._page.goto(url, wait_until='domcontentloaded')
        await self._page.wait_for_timeout(3000)

        # Wait for tweets to load
        try:
            await self._page.wait_for_selector(SELECTORS['tweet'], timeout=15000)
        except Exception:
            logger.warning(f"No tweets found for @{account}")
            return []

        posts = []
        seen_ids = set()
        scroll_attempts = 0
        max_scrolls = 10

        while scroll_attempts < max_scrolls:
            tweet_elements = await self._page.query_selector_all(SELECTORS['tweet'])

            for tweet_el in tweet_elements:
                post = await self._parse_tweet(tweet_el, account)
                if post is None or post.post_id in seen_ids:
                    continue

                seen_ids.add(post.post_id)

                # Skip if already in database
                if self.db.post_exists(post.post_id):
                    continue

                # Check timestamp cutoff
                if since and post.post_timestamp:
                    try:
                        post_dt = datetime.fromisoformat(post.post_timestamp)
                        if post_dt.tzinfo is None:
                            post_dt = post_dt.replace(tzinfo=timezone.utc)
                        since_aware = since if since.tzinfo else since.replace(tzinfo=timezone.utc)
                        if post_dt < since_aware:
                            # Reached posts older than cutoff
                            return posts
                    except (ValueError, TypeError):
                        pass

                posts.append(post)

            # Scroll down to load more
            await self._page.evaluate('window.scrollBy(0, window.innerHeight * 2)')
            await self._page.wait_for_timeout(2000)
            scroll_attempts += 1

            # Check if we got new content
            new_tweets = await self._page.query_selector_all(SELECTORS['tweet'])
            if len(new_tweets) == len(tweet_elements):
                break  # No new tweets loaded

        return posts

    async def _parse_tweet(self, tweet_el, account: str) -> Optional[Post]:
        """Parse a tweet element into a Post object.

        Args:
            tweet_el: Playwright element handle for the tweet
            account: Account username

        Returns:
            Post object or None if parsing fails
        """
        try:
            # Extract post ID from status link
            post_id = await self._extract_post_id(tweet_el)
            if not post_id:
                return None

            # Extract text content
            content = ""
            try:
                text_el = await tweet_el.query_selector(SELECTORS['tweet_text'])
                if text_el:
                    content = await text_el.inner_text()
            except Exception:
                pass

            # Extract timestamp
            timestamp = None
            try:
                time_el = await tweet_el.query_selector(SELECTORS['tweet_time'])
                if time_el:
                    timestamp = await time_el.get_attribute('datetime')
            except Exception:
                pass

            # Extract URLs from tweet text
            urls = []
            try:
                link_els = await tweet_el.query_selector_all('a[href]')
                for link_el in link_els:
                    href = await link_el.get_attribute('href')
                    if href and ('http' in href) and '/status/' not in href and 'x.com' not in href:
                        urls.append(href)
            except Exception:
                pass

            # Check for media
            has_image = await tweet_el.query_selector(SELECTORS['tweet_media_image']) is not None
            has_video = await tweet_el.query_selector(SELECTORS['tweet_media_video']) is not None
            has_link = len(urls) > 0

            return Post(
                post_id=post_id,
                account=account,
                content=content,
                post_timestamp=timestamp,
                urls=urls,
                has_link=has_link,
                has_video=has_video,
                has_image=has_image,
            )

        except Exception as e:
            logger.debug(f"Failed to parse tweet: {e}")
            return None

    async def _extract_post_id(self, tweet_el) -> Optional[str]:
        """Extract post ID from a tweet element."""
        try:
            link_els = await tweet_el.query_selector_all('a[href*="/status/"]')
            for link_el in link_els:
                href = await link_el.get_attribute('href')
                if href:
                    match = re.search(r'/status/(\d+)', href)
                    if match:
                        return match.group(1)
        except Exception:
            pass
        return None
