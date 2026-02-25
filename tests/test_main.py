"""Integration tests for main.py — Full pipeline orchestration."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
from pathlib import Path
import tempfile

from main import run_digest, run_login, setup_logging


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock()
    settings.follow_accounts = ['OpenAI', 'karpathy']
    settings.headless = True
    settings.browser_data_path = Path('/tmp/browser')
    settings.gemini_api_key = 'test_key'
    settings.smtp_host = 'smtp.gmail.com'
    settings.smtp_port = 587
    settings.smtp_user = 'user@gmail.com'
    settings.smtp_password = 'password'
    settings.from_email = 'user@gmail.com'
    settings.to_email = 'recipient@example.com'
    settings.log_path = Path(tempfile.gettempdir())
    settings.db_path = Path(tempfile.gettempdir()) / 'test.db'
    return settings


@pytest.fixture
def mock_db():
    """Create mock database."""
    db = MagicMock()
    db.get_last_sent_timestamp.return_value = None
    db.create_digest.return_value = 1
    db.add_post.return_value = None
    db.set_last_sent_timestamp.return_value = None
    return db


@pytest.fixture
def mock_logger():
    """Create mock logger."""
    return MagicMock()


class TestSetupLogging:
    """Test logging setup."""

    def test_creates_log_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir)
            logger = setup_logging(log_path)

            assert logger is not None
            # Check log file was created
            log_files = list(log_path.glob('xdigest_*.log'))
            assert len(log_files) == 1


class TestRunLogin:
    """Test manual login flow."""

    @pytest.mark.asyncio
    @patch('main.XScraper')
    async def test_runs_manual_login(self, mock_scraper_cls, mock_settings, mock_db):
        mock_scraper = AsyncMock()
        mock_scraper_cls.return_value = mock_scraper

        await run_login(mock_settings, mock_db)

        mock_scraper_cls.assert_called_once_with(
            db=mock_db,
            headless=False,
            browser_data_path=str(mock_settings.browser_data_path),
            use_cdp=False,
        )
        mock_scraper.manual_login.assert_called_once()


class TestRunDigest:
    """Test full digest pipeline."""

    @pytest.mark.asyncio
    @patch('main.EmailSender')
    @patch('main.GeminiSummarizer')
    @patch('main.process_video')
    @patch('main.fetch_article')
    @patch('main.XScraper')
    async def test_full_pipeline_success(
        self,
        mock_scraper_cls,
        mock_fetch_article,
        mock_process_video,
        mock_summarizer_cls,
        mock_email_cls,
        mock_settings,
        mock_db,
        mock_logger,
    ):
        # Setup mock scraper
        mock_scraper = AsyncMock()
        mock_post = MagicMock()
        mock_post.account = 'OpenAI'
        mock_post.timestamp = datetime(2024, 1, 15, 10, 30)
        mock_post.content = 'GPT-5 released!'
        mock_post.post_id = '123'
        mock_post.urls = ['https://openai.com/gpt5']
        mock_post.media_type = None
        mock_post.to_dict.return_value = {
            'account': 'OpenAI',
            'content': 'GPT-5 released!',
        }
        mock_scraper.scrape_accounts.return_value = [mock_post]
        mock_scraper_cls.return_value = mock_scraper

        # Setup mock article fetcher
        mock_article = MagicMock()
        mock_article.text = 'Article text here'
        mock_article.source = 'trafilatura'
        mock_fetch_article.return_value = mock_article

        # Setup mock summarizer
        mock_summarizer = MagicMock()
        mock_summarizer.summarize_posts.return_value = [
            {
                'account': 'OpenAI',
                'content': 'GPT-5 released!',
                'summary': 'OpenAI announces GPT-5.',
            }
        ]
        mock_summarizer.generate_digest_overview.return_value = 'Big AI news today.'
        mock_summarizer_cls.return_value = mock_summarizer

        # Setup mock email sender
        mock_sender = MagicMock()
        mock_sender.send_digest.return_value = True
        mock_email_cls.return_value = mock_sender

        # Run digest
        await run_digest(mock_settings, mock_db, mock_logger)

        # Verify scraper was called
        mock_scraper.scrape_accounts.assert_called_once()

        # Verify digest was created
        mock_db.create_digest.assert_called_once_with(post_count=1)

        # Verify post was added
        mock_db.add_post.assert_called_once()

        # Verify article was fetched
        mock_fetch_article.assert_called_once_with('https://openai.com/gpt5')

        # Verify summarizer was called
        mock_summarizer.summarize_posts.assert_called_once()
        mock_summarizer.generate_digest_overview.assert_called_once()

        # Verify email was sent
        mock_sender.send_digest.assert_called_once()

        # Verify timestamp was updated
        mock_db.set_last_sent_timestamp.assert_called_once()

    @pytest.mark.asyncio
    @patch('main.XScraper')
    async def test_no_posts_skips_pipeline(
        self,
        mock_scraper_cls,
        mock_settings,
        mock_db,
        mock_logger,
    ):
        mock_scraper = AsyncMock()
        mock_scraper.scrape_accounts.return_value = []
        mock_scraper_cls.return_value = mock_scraper

        await run_digest(mock_settings, mock_db, mock_logger)

        # Should not create digest or update timestamp
        mock_db.create_digest.assert_not_called()
        mock_db.set_last_sent_timestamp.assert_not_called()

    @pytest.mark.asyncio
    @patch('main.EmailSender')
    @patch('main.GeminiSummarizer')
    @patch('main.fetch_article')
    @patch('main.XScraper')
    async def test_email_failure_skips_timestamp_update(
        self,
        mock_scraper_cls,
        mock_fetch_article,
        mock_summarizer_cls,
        mock_email_cls,
        mock_settings,
        mock_db,
        mock_logger,
    ):
        # Setup mock scraper with posts
        mock_scraper = AsyncMock()
        mock_post = MagicMock()
        mock_post.account = 'OpenAI'
        mock_post.timestamp = datetime(2024, 1, 15, 10, 30)
        mock_post.content = 'Test'
        mock_post.post_id = '123'
        mock_post.urls = []
        mock_post.media_type = None
        mock_post.to_dict.return_value = {'account': 'OpenAI', 'content': 'Test'}
        mock_scraper.scrape_accounts.return_value = [mock_post]
        mock_scraper_cls.return_value = mock_scraper

        # Setup mock summarizer
        mock_summarizer = MagicMock()
        mock_summarizer.summarize_posts.return_value = [
            {'account': 'OpenAI', 'content': 'Test', 'summary': 'Summary'}
        ]
        mock_summarizer.generate_digest_overview.return_value = 'Overview'
        mock_summarizer_cls.return_value = mock_summarizer

        # Setup mock email sender to fail
        mock_sender = MagicMock()
        mock_sender.send_digest.return_value = False
        mock_email_cls.return_value = mock_sender

        await run_digest(mock_settings, mock_db, mock_logger)

        # Should not update timestamp on email failure
        mock_db.set_last_sent_timestamp.assert_not_called()

    @pytest.mark.asyncio
    @patch('main.process_video')
    @patch('main.fetch_article')
    @patch('main.EmailSender')
    @patch('main.GeminiSummarizer')
    @patch('main.XScraper')
    async def test_enriches_video_content(
        self,
        mock_scraper_cls,
        mock_summarizer_cls,
        mock_email_cls,
        mock_fetch_article,
        mock_process_video,
        mock_settings,
        mock_db,
        mock_logger,
    ):
        # Setup mock scraper with video post
        mock_scraper = AsyncMock()
        mock_post = MagicMock()
        mock_post.account = 'lexfridman'
        mock_post.timestamp = datetime(2024, 1, 15, 10, 30)
        mock_post.content = 'New podcast'
        mock_post.post_id = '123'
        mock_post.urls = ['https://youtube.com/watch?v=abc']
        mock_post.media_type = 'video'
        mock_post.to_dict.return_value = {'account': 'lexfridman', 'content': 'New podcast'}
        mock_scraper.scrape_accounts.return_value = [mock_post]
        mock_scraper_cls.return_value = mock_scraper

        # Setup mock video processor
        mock_video_info = MagicMock()
        mock_video_info.transcript = 'Video transcript here'
        mock_video_info.source = 'youtube_transcript'
        mock_process_video.return_value = mock_video_info

        # Setup mock summarizer
        mock_summarizer = MagicMock()
        mock_summarizer.summarize_posts.return_value = [
            {'account': 'lexfridman', 'summary': 'Summary'}
        ]
        mock_summarizer.generate_digest_overview.return_value = 'Overview'
        mock_summarizer_cls.return_value = mock_summarizer

        # Setup mock email sender
        mock_sender = MagicMock()
        mock_sender.send_digest.return_value = True
        mock_email_cls.return_value = mock_sender

        await run_digest(mock_settings, mock_db, mock_logger)

        # Verify video was processed
        mock_process_video.assert_called_once_with('https://youtube.com/watch?v=abc')
