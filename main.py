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
from scraper.article_fetcher import fetch_article
from scraper.video_processor import process_video
from summarizer.gemini_summarizer import GeminiSummarizer
from email_service.sender import EmailSender


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

    # Create digest record
    digest_id = db.create_digest(post_count=len(posts))
    logger.info(f"Created digest record: {digest_id}")

    # Store posts in database
    for post in posts:
        post_dict = post.to_dict()
        post_dict['digest_id'] = digest_id
        db.add_post(post_dict)

    # Phase 3: Enrich content (articles and videos)
    logger.info("Enriching content...")
    enriched_posts = []

    for post in posts:
        post_data = {
            'account': post.account,
            'timestamp': post.timestamp.strftime('%B %d, %Y at %I:%M %p') if post.timestamp else '',
            'content': post.content,
            'post_url': f"https://x.com/{post.account}/status/{post.post_id}" if post.post_id else '',
            'urls': post.urls,
            'media_type': post.media_type,
            'article_text': '',
            'video_transcript': '',
            'image_bytes': None,
        }

        # Fetch articles
        if post.urls:
            for url in post.urls:
                article = fetch_article(url)
                if article:
                    post_data['article_text'] = article.text
                    logger.info(f"Fetched article from {url} ({article.source})")
                    break  # Use first successful article

        # Process videos
        if post.media_type == 'video' and post.urls:
            for url in post.urls:
                video_info = process_video(url)
                if video_info:
                    post_data['video_transcript'] = video_info.transcript or video_info.description
                    logger.info(f"Processed video from {url} ({video_info.source})")
                    break  # Use first successful video

        enriched_posts.append(post_data)

    logger.info(f"Enriched {len(enriched_posts)} posts")

    # Phase 4: Summarize with Gemini
    logger.info("Generating summaries with Gemini...")
    summarizer = GeminiSummarizer(api_key=settings.gemini_api_key)

    summarized_posts = summarizer.summarize_posts(enriched_posts)
    logger.info(f"Generated {len(summarized_posts)} post summaries")

    # Generate digest overview
    post_summaries = [
        {'account': p['account'], 'summary': p.get('summary', '')}
        for p in summarized_posts
    ]
    overview = summarizer.generate_digest_overview(post_summaries)
    logger.info("Generated digest overview")

    # Phase 5: Send email
    logger.info("Sending email digest...")
    email_sender = EmailSender(
        smtp_host=settings.smtp_host,
        smtp_port=settings.smtp_port,
        smtp_user=settings.smtp_user,
        smtp_password=settings.smtp_password,
        from_email=settings.from_email,
        to_email=settings.to_email,
    )

    success = email_sender.send_digest(
        posts=summarized_posts,
        overview=overview,
    )

    if success:
        logger.info(f"Email digest sent successfully to {settings.to_email}")
        # Update last sent timestamp only on successful send
        db.set_last_sent_timestamp(datetime.now())
    else:
        logger.error("Failed to send email digest")
        return

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
