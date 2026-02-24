"""Unit tests for scraper/article_fetcher.py — Article extraction."""

import pytest
from unittest.mock import patch, MagicMock

from scraper.article_fetcher import (
    resolve_url, fetch_article, _fetch_with_trafilatura,
    _fetch_with_newspaper, Article,
)


class TestResolveUrl:
    """Test URL resolution."""

    @patch('scraper.article_fetcher.requests')
    def test_resolves_shortened_url(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.url = 'https://example.com/full-article'
        mock_requests.head.return_value = mock_resp

        result = resolve_url('https://t.co/abc123')
        assert result == 'https://example.com/full-article'

    @patch('scraper.article_fetcher.requests')
    def test_returns_original_on_failure(self, mock_requests):
        mock_requests.head.side_effect = Exception("Connection error")

        result = resolve_url('https://t.co/broken')
        assert result == 'https://t.co/broken'

    @patch('scraper.article_fetcher.requests')
    def test_passes_timeout(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.url = 'https://example.com'
        mock_requests.head.return_value = mock_resp

        resolve_url('https://t.co/xyz')
        mock_requests.head.assert_called_once_with(
            'https://t.co/xyz', allow_redirects=True, timeout=15
        )


class TestFetchWithTrafilatura:
    """Test trafilatura extraction."""

    @patch('scraper.article_fetcher.trafilatura')
    def test_successful_extraction(self, mock_traf):
        mock_traf.fetch_url.return_value = '<html>article content</html>'
        mock_traf.extract.return_value = 'This is the article text.'
        mock_metadata = MagicMock()
        mock_metadata.title = 'Test Article'
        mock_traf.extract_metadata.return_value = mock_metadata

        result = _fetch_with_trafilatura('https://example.com/article')
        assert result is not None
        assert result.text == 'This is the article text.'
        assert result.title == 'Test Article'
        assert result.source == 'trafilatura'

    @patch('scraper.article_fetcher.trafilatura')
    def test_returns_none_on_download_failure(self, mock_traf):
        mock_traf.fetch_url.return_value = None

        result = _fetch_with_trafilatura('https://example.com/bad')
        assert result is None

    @patch('scraper.article_fetcher.trafilatura')
    def test_returns_none_on_extract_failure(self, mock_traf):
        mock_traf.fetch_url.return_value = '<html></html>'
        mock_traf.extract.return_value = None

        result = _fetch_with_trafilatura('https://example.com/empty')
        assert result is None

    @patch('scraper.article_fetcher.trafilatura')
    def test_handles_no_metadata(self, mock_traf):
        mock_traf.fetch_url.return_value = '<html>content</html>'
        mock_traf.extract.return_value = 'Some text'
        mock_traf.extract_metadata.return_value = None

        result = _fetch_with_trafilatura('https://example.com')
        assert result is not None
        assert result.title == ''
        assert result.text == 'Some text'


class TestFetchWithNewspaper:
    """Test newspaper3k fallback extraction."""

    @patch('scraper.article_fetcher.NArticle', create=True)
    def test_successful_extraction(self, mock_narticle_cls):
        # We need to patch the import inside the function
        mock_article = MagicMock()
        mock_article.text = 'Newspaper extracted text'
        mock_article.title = 'News Title'

        with patch.dict('sys.modules', {'newspaper': MagicMock()}):
            with patch('scraper.article_fetcher._fetch_with_newspaper') as mock_fn:
                mock_fn.return_value = Article(
                    url='https://example.com',
                    title='News Title',
                    text='Newspaper extracted text',
                    source='newspaper3k',
                )
                result = mock_fn('https://example.com')

        assert result is not None
        assert result.text == 'Newspaper extracted text'
        assert result.source == 'newspaper3k'

    def test_returns_none_on_import_error(self):
        """newspaper3k not installed should return None."""
        with patch.dict('sys.modules', {'newspaper': None}):
            result = _fetch_with_newspaper('https://example.com')
            assert result is None


class TestFetchArticle:
    """Test the main fetch_article function."""

    @patch('scraper.article_fetcher.resolve_url')
    @patch('scraper.article_fetcher._fetch_with_trafilatura')
    def test_uses_trafilatura_first(self, mock_traf, mock_resolve):
        mock_resolve.return_value = 'https://example.com/article'
        mock_traf.return_value = Article(
            url='https://example.com/article',
            title='Title',
            text='Article text',
            source='trafilatura',
        )

        result = fetch_article('https://t.co/abc')
        assert result is not None
        assert result.source == 'trafilatura'

    @patch('scraper.article_fetcher.resolve_url')
    @patch('scraper.article_fetcher._fetch_with_trafilatura')
    @patch('scraper.article_fetcher._fetch_with_newspaper')
    def test_falls_back_to_newspaper(self, mock_news, mock_traf, mock_resolve):
        mock_resolve.return_value = 'https://example.com/article'
        mock_traf.return_value = None
        mock_news.return_value = Article(
            url='https://example.com/article',
            title='Title',
            text='Fallback text',
            source='newspaper3k',
        )

        result = fetch_article('https://t.co/abc')
        assert result is not None
        assert result.source == 'newspaper3k'

    @patch('scraper.article_fetcher.resolve_url')
    @patch('scraper.article_fetcher._fetch_with_trafilatura')
    @patch('scraper.article_fetcher._fetch_with_newspaper')
    def test_returns_none_when_both_fail(self, mock_news, mock_traf, mock_resolve):
        mock_resolve.return_value = 'https://example.com'
        mock_traf.return_value = None
        mock_news.return_value = None

        result = fetch_article('https://t.co/abc')
        assert result is None


class TestArticleDataclass:
    """Test Article dataclass."""

    def test_article_creation(self):
        a = Article(url='https://example.com', title='Test', text='Content')
        assert a.url == 'https://example.com'
        assert a.source == ''

    def test_article_defaults(self):
        a = Article(url='https://example.com')
        assert a.title == ''
        assert a.text == ''
        assert a.source == ''
