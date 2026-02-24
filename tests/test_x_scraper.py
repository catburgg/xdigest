"""Unit tests for scraper/x_scraper.py — X post scraping logic."""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from scraper.x_scraper import XScraper, Post, SELECTORS


class TestPost:
    """Test Post dataclass."""

    def test_post_creation(self):
        post = Post(post_id='123', account='testuser', content='Hello')
        assert post.post_id == '123'
        assert post.account == 'testuser'
        assert post.content == 'Hello'
        assert post.urls == []
        assert post.has_link is False
        assert post.has_video is False
        assert post.has_image is False

    def test_post_to_dict(self):
        post = Post(
            post_id='456',
            account='openai',
            content='New model released',
            post_timestamp='2026-02-24T07:00:00Z',
            urls=['https://example.com/article'],
            has_link=True,
            has_video=False,
            has_image=True,
        )
        d = post.to_dict()
        assert d['post_id'] == '456'
        assert d['account'] == 'openai'
        assert d['urls'] == ['https://example.com/article']
        assert d['has_link'] is True
        assert d['has_image'] is True

    def test_post_defaults(self):
        post = Post(post_id='789', account='user')
        d = post.to_dict()
        assert d['content'] == ''
        assert d['post_timestamp'] is None
        assert d['urls'] == []


class TestXScraperInit:
    """Test XScraper initialization."""

    def test_init_defaults(self):
        db = MagicMock()
        scraper = XScraper(db=db)
        assert scraper.headless is True
        assert scraper.db is db

    def test_init_custom(self):
        db = MagicMock()
        scraper = XScraper(db=db, headless=False, browser_data_path='/tmp/browser')
        assert scraper.headless is False
        assert scraper.browser_data_path == '/tmp/browser'


class TestCookieManagement:
    """Test cookie save/restore logic."""

    @pytest.mark.asyncio
    async def test_restore_cookies_success(self):
        db = MagicMock()
        db.get_session_cookies.return_value = [
            {'name': 'auth_token', 'value': 'abc', 'domain': '.x.com'}
        ]

        scraper = XScraper(db=db)
        scraper._context = AsyncMock()

        result = await scraper._restore_cookies()
        assert result is True
        scraper._context.add_cookies.assert_called_once()

    @pytest.mark.asyncio
    async def test_restore_cookies_none(self):
        db = MagicMock()
        db.get_session_cookies.return_value = None

        scraper = XScraper(db=db)
        scraper._context = AsyncMock()

        result = await scraper._restore_cookies()
        assert result is False

    @pytest.mark.asyncio
    async def test_save_cookies(self):
        db = MagicMock()
        scraper = XScraper(db=db)
        scraper._context = AsyncMock()
        scraper._context.cookies.return_value = [
            {'name': 'ct0', 'value': 'xyz', 'domain': '.x.com'}
        ]

        await scraper._save_cookies()
        db.save_session_cookies.assert_called_once()
        saved = db.save_session_cookies.call_args[0][0]
        assert len(saved) == 1
        assert saved[0]['name'] == 'ct0'


class TestPostIdExtraction:
    """Test post ID extraction from tweet elements."""

    @pytest.mark.asyncio
    async def test_extract_post_id(self):
        db = MagicMock()
        scraper = XScraper(db=db)

        # Mock a link element with a status URL
        link_el = AsyncMock()
        link_el.get_attribute.return_value = '/openai/status/1234567890'

        tweet_el = AsyncMock()
        tweet_el.query_selector_all.return_value = [link_el]

        post_id = await scraper._extract_post_id(tweet_el)
        assert post_id == '1234567890'

    @pytest.mark.asyncio
    async def test_extract_post_id_no_link(self):
        db = MagicMock()
        scraper = XScraper(db=db)

        tweet_el = AsyncMock()
        tweet_el.query_selector_all.return_value = []

        post_id = await scraper._extract_post_id(tweet_el)
        assert post_id is None

    @pytest.mark.asyncio
    async def test_extract_post_id_invalid_href(self):
        db = MagicMock()
        scraper = XScraper(db=db)

        link_el = AsyncMock()
        link_el.get_attribute.return_value = '/openai/followers'

        tweet_el = AsyncMock()
        tweet_el.query_selector_all.return_value = [link_el]

        post_id = await scraper._extract_post_id(tweet_el)
        assert post_id is None


class TestParseTweet:
    """Test tweet element parsing."""

    def _make_tweet_el(self, post_id='999', content='Test post',
                       timestamp='2026-02-24T10:00:00.000Z',
                       urls=None, has_image=False, has_video=False):
        """Helper to create a mock tweet element."""
        tweet_el = AsyncMock()

        # Post ID link
        status_link = AsyncMock()
        status_link.get_attribute.return_value = f'/user/status/{post_id}'
        tweet_el.query_selector_all.return_value = [status_link]

        # Text content
        text_el = AsyncMock()
        text_el.inner_text.return_value = content

        # Time element
        time_el = AsyncMock()
        time_el.get_attribute.return_value = timestamp

        # Media elements
        image_el = AsyncMock() if has_image else None
        video_el = AsyncMock() if has_video else None

        # URL links
        link_els = []
        if urls:
            for url in urls:
                link = AsyncMock()
                link.get_attribute.return_value = url
                link_els.append(link)

        def query_selector_side_effect(selector):
            if selector == SELECTORS['tweet_text']:
                return text_el
            elif selector == SELECTORS['tweet_time']:
                return time_el
            elif selector == SELECTORS['tweet_media_image']:
                return image_el
            elif selector == SELECTORS['tweet_media_video']:
                return video_el
            return None

        # query_selector for single elements
        tweet_el.query_selector = AsyncMock(side_effect=query_selector_side_effect)

        # query_selector_all for links (called twice: once for post_id, once for urls)
        async def query_selector_all_side_effect(selector):
            if '/status/' in selector:
                return [status_link]
            elif 'a[href]' in selector:
                return link_els
            return []

        tweet_el.query_selector_all = AsyncMock(side_effect=query_selector_all_side_effect)

        return tweet_el

    @pytest.mark.asyncio
    async def test_parse_basic_tweet(self):
        db = MagicMock()
        scraper = XScraper(db=db)

        tweet_el = self._make_tweet_el(
            post_id='111', content='Hello world', timestamp='2026-02-24T10:00:00.000Z'
        )

        post = await scraper._parse_tweet(tweet_el, 'testuser')
        assert post is not None
        assert post.post_id == '111'
        assert post.account == 'testuser'
        assert post.content == 'Hello world'
        assert post.post_timestamp == '2026-02-24T10:00:00.000Z'

    @pytest.mark.asyncio
    async def test_parse_tweet_with_image(self):
        db = MagicMock()
        scraper = XScraper(db=db)

        tweet_el = self._make_tweet_el(post_id='222', has_image=True)
        post = await scraper._parse_tweet(tweet_el, 'user')
        assert post.has_image is True
        assert post.has_video is False

    @pytest.mark.asyncio
    async def test_parse_tweet_with_video(self):
        db = MagicMock()
        scraper = XScraper(db=db)

        tweet_el = self._make_tweet_el(post_id='333', has_video=True)
        post = await scraper._parse_tweet(tweet_el, 'user')
        assert post.has_video is True

    @pytest.mark.asyncio
    async def test_parse_tweet_with_urls(self):
        db = MagicMock()
        scraper = XScraper(db=db)

        tweet_el = self._make_tweet_el(
            post_id='444',
            urls=['https://example.com/article', 'https://youtube.com/watch?v=abc']
        )
        post = await scraper._parse_tweet(tweet_el, 'user')
        assert post.has_link is True
        assert len(post.urls) == 2


class TestScrapeAccountsNoSession:
    """Test scrape_accounts when no session cookies exist."""

    @pytest.mark.asyncio
    async def test_no_cookies_returns_empty(self):
        db = MagicMock()
        db.get_session_cookies.return_value = None

        scraper = XScraper(db=db)

        with patch('scraper.x_scraper.async_playwright') as mock_pw:
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_page = AsyncMock()

            mock_pw.return_value.__aenter__.return_value.chromium.launch.return_value = mock_browser
            mock_browser.new_context.return_value = mock_context
            mock_context.new_page.return_value = mock_page

            posts = await scraper.scrape_accounts(['openai'])
            assert posts == []
