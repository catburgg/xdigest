#!/usr/bin/env python3
"""Main entry point for XDigest.

Orchestrates the entire digest generation process:
1. Load configuration
2. Scrape X posts from followed accounts
3. Enrich content (articles, videos)
4. Summarize with Gemini
5. Send email digest
6. Update state
"""

import sys
import logging
from datetime import datetime
from pathlib import Path

from config.settings import settings
from storage.db import Database


def setup_logging():
    """Configure logging."""
    log_file = settings.log_path / f"xdigest_{datetime.now().strftime('%Y%m%d')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

    return logging.getLogger(__name__)


def main():
    """Main execution function."""
    logger = setup_logging()
    logger.info("=" * 60)
    logger.info("XDigest started")
    logger.info("=" * 60)

    try:
        # Initialize database
        db = Database(settings.db_path)
        logger.info(f"Database initialized: {settings.db_path}")

        # Get last sent timestamp
        last_sent = db.get_last_sent_timestamp()
        if last_sent:
            logger.info(f"Last digest sent: {last_sent}")
        else:
            logger.info("No previous digest found (first run)")

        # TODO: Phase 2 - Implement X scraping
        logger.info(f"Following {len(settings.follow_accounts)} accounts: {', '.join(settings.follow_accounts)}")

        # TODO: Phase 3 - Implement content enrichment

        # TODO: Phase 4 - Implement Gemini summarization

        # TODO: Phase 5 - Implement email delivery

        # TODO: Phase 6 - Update state

        logger.info("XDigest completed successfully")

    except Exception as e:
        logger.error(f"Error during execution: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
