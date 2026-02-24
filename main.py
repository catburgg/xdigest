#!/usr/bin/env python3
"""Main entry point for XDigest.

Orchestrates the entire digest generation process:
1. Load configuration
2. Scrape X posts from followed accounts
3. Enrich content (articles, videos)
4. Summarize with Gemini
5. Send email digest
6. Update state

Usage:
    python main.py            # Run digest (scrape + summarize + email)
    python main.py --login    # Open browser for manual X login
"""

import sys
import asyncio
import argparse
import logging
from datetime import datetime

from config.settings import get_settings
from storage.db import Database
from scraper.x_scraper import XScraper


def setup_logging(log_path):
    """Configure logging."""
    log_file = log_path / f"xdigest_{datetime.now().strftime('%Y%m%d')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

    return logging.getLogger(__name__)


async def run_login(settings, db):
    """Run manual login flow."""
    scraper = XScraper(
        db=db,
        headless=False,
        browser_data_path=str(settings.browser_data_path),
    )
    await scraper.manual_login()


async def run_digest(settings, db, logger):
    """Run the full digest pipeline."""
    # Get last sent timestamp
    last_sent = db.get_last_sent_timestamp()
    if last_sent:
        logger.info(f"Last digest sent: {last_sent}")
    else:
        logger.info("No previous digest found (first run)")

    # Phase 2: Scrape X posts
    scraper = XScraper(
        db=db,
        headless=settings.headless,
        browser_data_path=str(settings.browser_data_path),
    )

    logger.info(f"Scraping {len(settings.follow_accounts)} accounts: {', '.join(settings.follow_accounts)}")
    posts = await scraper.scrape_accounts(settings.follow_accounts, since=last_sent)
    logger.info(f"Scraped {len(posts)} new posts total")

    if not posts:
        logger.info("No new posts found. Skipping digest.")
        return

    # Store posts in database
    for post in posts:
        db.add_post(post.to_dict())

    # TODO: Phase 3 - Implement content enrichment

    # TODO: Phase 4 - Implement Gemini summarization

    # TODO: Phase 5 - Implement email delivery

    # Update last sent timestamp
    db.set_last_sent_timestamp(datetime.now())
    logger.info("XDigest completed successfully")


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description='XDigest - X News Digest')
    parser.add_argument('--login', action='store_true',
                        help='Open browser for manual X login')
    args = parser.parse_args()

    settings = get_settings()
    logger = setup_logging(settings.log_path)

    logger.info("=" * 60)
    logger.info("XDigest started")
    logger.info("=" * 60)

    try:
        db = Database(settings.db_path)
        logger.info(f"Database initialized: {settings.db_path}")

        if args.login:
            logger.info("Starting manual login flow...")
            asyncio.run(run_login(settings, db))
        else:
            asyncio.run(run_digest(settings, db, logger))

    except Exception as e:
        logger.error(f"Error during execution: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
