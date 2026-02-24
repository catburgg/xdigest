"""Article fetcher for XDigest.

Resolves shortened URLs (t.co) and extracts article text.
Uses trafilatura as primary extractor, newspaper3k as fallback.
"""

import logging
from typing import Optional
from dataclasses import dataclass

import requests
import trafilatura

logger = logging.getLogger(__name__)

# Timeout for HTTP requests
REQUEST_TIMEOUT = 15


@dataclass
class Article:
    """Extracted article data."""
    url: str
    title: str = ""
    text: str = ""
    source: str = ""  # extraction method used


def resolve_url(url: str) -> str:
    """Resolve shortened URLs (t.co, bit.ly, etc.) to final destination.

    Args:
        url: Potentially shortened URL

    Returns:
        Resolved URL (or original if resolution fails)
    """
    try:
        resp = requests.head(url, allow_redirects=True, timeout=REQUEST_TIMEOUT)
        return resp.url
    except Exception as e:
        logger.debug(f"URL resolution failed for {url}: {e}")
        return url


def fetch_article(url: str) -> Optional[Article]:
    """Fetch and extract article text from a URL.

    Tries trafilatura first, falls back to newspaper3k.

    Args:
        url: Article URL

    Returns:
        Article object or None if extraction fails
    """
    # Resolve shortened URLs
    resolved_url = resolve_url(url)
    logger.info(f"Fetching article: {resolved_url}")

    # Try trafilatura first
    article = _fetch_with_trafilatura(resolved_url)
    if article and article.text:
        return article

    # Fallback to newspaper3k
    article = _fetch_with_newspaper(resolved_url)
    if article and article.text:
        return article

    logger.warning(f"Failed to extract article from {resolved_url}")
    return None


def _fetch_with_trafilatura(url: str) -> Optional[Article]:
    """Extract article using trafilatura.

    Args:
        url: Article URL

    Returns:
        Article object or None
    """
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return None

        result = trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=False,
            favor_precision=True,
        )

        if not result:
            return None

        # Get metadata for title
        metadata = trafilatura.extract_metadata(downloaded)
        title = metadata.title if metadata and metadata.title else ""

        return Article(
            url=url,
            title=title,
            text=result,
            source='trafilatura',
        )

    except Exception as e:
        logger.debug(f"Trafilatura failed for {url}: {e}")
        return None


def _fetch_with_newspaper(url: str) -> Optional[Article]:
    """Extract article using newspaper3k as fallback.

    Args:
        url: Article URL

    Returns:
        Article object or None
    """
    try:
        from newspaper import Article as NArticle

        article = NArticle(url)
        article.download()
        article.parse()

        if not article.text:
            return None

        return Article(
            url=url,
            title=article.title or "",
            text=article.text,
            source='newspaper3k',
        )

    except Exception as e:
        logger.debug(f"Newspaper3k failed for {url}: {e}")
        return None
