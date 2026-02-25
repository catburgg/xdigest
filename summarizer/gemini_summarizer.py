"""Gemini API integration for content summarization.

Provides two levels of summarization:
1. Per-post summary — 2-3 sentences covering key news/insight
2. Digest overview — 3-5 sentence summary of key themes across all posts

Uses Google Gemini 1.5 Flash for fast, cheap, multimodal summarization.
"""

import time
import logging
from typing import List, Optional, Dict, Any

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

MODEL_NAME = 'gemini-1.5-flash'  # Updated to available model
API_DELAY = 1  # seconds between API calls (courtesy rate limiting)

POST_SUMMARY_PROMPT = """Summarize this social media post and any linked content into 2-3 concise sentences.
Focus on key news, facts, and insights. Be specific and informative.

Post by @{account}:
{post_text}

{extra_context}"""

DIGEST_OVERVIEW_PROMPT = """Write a brief 3-5 sentence overview of the key themes and most important news items
from the following post summaries. Highlight the most significant developments.

{summaries}"""


class GeminiSummarizer:
    """Summarizes content using Google Gemini API."""

    def __init__(self, api_key: str):
        """Initialize Gemini client.

        Args:
            api_key: Google Gemini API key
        """
        self.client = genai.Client(api_key=api_key)

    def summarize_post(
        self,
        account: str,
        post_text: str,
        article_text: str = "",
        video_transcript: str = "",
        image_bytes: Optional[bytes] = None,
    ) -> str:
        """Generate a summary for a single post.

        Args:
            account: X account username
            post_text: Original post text
            article_text: Extracted article text (if post has link)
            video_transcript: Video transcript (if post has video)
            image_bytes: Image data (if post has image)

        Returns:
            Summary string (2-3 sentences)
        """
        # Build extra context from enriched content
        extra_parts = []
        if article_text:
            extra_parts.append(f"Linked article:\n{article_text[:3000]}")
        if video_transcript:
            extra_parts.append(f"Video transcript:\n{video_transcript[:3000]}")

        extra_context = "\n\n".join(extra_parts) if extra_parts else "No additional context."

        prompt = POST_SUMMARY_PROMPT.format(
            account=account,
            post_text=post_text,
            extra_context=extra_context,
        )

        # Build content parts for multimodal input
        content_parts = [types.Part.from_text(text=prompt)]
        if image_bytes:
            content_parts.append(types.Part.from_bytes(
                data=image_bytes,
                mime_type='image/jpeg',
            ))

        try:
            response = self.client.models.generate_content(
                model=MODEL_NAME,
                contents=content_parts,
            )
            time.sleep(API_DELAY)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini summarization failed for @{account} post: {e}")
            # Fallback: return truncated post text
            return post_text[:200] + "..." if len(post_text) > 200 else post_text

    def generate_digest_overview(self, post_summaries: List[Dict[str, str]]) -> str:
        """Generate an overview of all post summaries.

        Args:
            post_summaries: List of dicts with 'account' and 'summary' keys

        Returns:
            Overview string (3-5 sentences)
        """
        if not post_summaries:
            return "No new posts to summarize."

        summaries_text = "\n\n".join(
            f"@{ps['account']}: {ps['summary']}"
            for ps in post_summaries
        )

        prompt = DIGEST_OVERVIEW_PROMPT.format(summaries=summaries_text)

        try:
            response = self.client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
            )
            time.sleep(API_DELAY)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini digest overview failed: {e}")
            return "Unable to generate overview."

    def summarize_posts(self, posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Summarize a list of posts and generate digest overview.

        Args:
            posts: List of post dicts with keys: account, content,
                   article_text, video_transcript, image_bytes

        Returns:
            List of post dicts with added 'summary' key
        """
        post_summaries = []

        for post in posts:
            summary = self.summarize_post(
                account=post.get('account', ''),
                post_text=post.get('content', ''),
                article_text=post.get('article_text', ''),
                video_transcript=post.get('video_transcript', ''),
                image_bytes=post.get('image_bytes'),
            )
            post['summary'] = summary
            post_summaries.append({
                'account': post.get('account', ''),
                'summary': summary,
            })
            logger.info(f"Summarized post from @{post.get('account', 'unknown')}")

        return posts
