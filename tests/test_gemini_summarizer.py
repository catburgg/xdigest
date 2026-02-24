"""Unit tests for summarizer/gemini_summarizer.py — Gemini API integration."""

import pytest
from unittest.mock import patch, MagicMock

from summarizer.gemini_summarizer import (
    GeminiSummarizer, MODEL_NAME, POST_SUMMARY_PROMPT, DIGEST_OVERVIEW_PROMPT,
)


@pytest.fixture
def summarizer():
    """Create a GeminiSummarizer with mocked API."""
    with patch('summarizer.gemini_summarizer.genai') as mock_genai:
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        s = GeminiSummarizer(api_key='test_key')
        s._mock_client = mock_client
        yield s


class TestGeminiSummarizerInit:
    """Test initialization."""

    def test_creates_client_with_api_key(self):
        with patch('summarizer.gemini_summarizer.genai') as mock_genai:
            GeminiSummarizer(api_key='my_key')
            mock_genai.Client.assert_called_once_with(api_key='my_key')


class TestSummarizePost:
    """Test per-post summarization."""

    @patch('summarizer.gemini_summarizer.time')
    @patch('summarizer.gemini_summarizer.types')
    def test_basic_post_summary(self, mock_types, mock_time, summarizer):
        mock_types.Part.from_text.return_value = 'text_part'
        mock_response = MagicMock()
        mock_response.text = '  OpenAI announced a new model with improved reasoning.  '
        summarizer._mock_client.models.generate_content.return_value = mock_response

        result = summarizer.summarize_post(
            account='OpenAI',
            post_text='We just released GPT-5!',
        )

        assert result == 'OpenAI announced a new model with improved reasoning.'
        summarizer._mock_client.models.generate_content.assert_called_once()

    @patch('summarizer.gemini_summarizer.time')
    @patch('summarizer.gemini_summarizer.types')
    def test_post_with_article(self, mock_types, mock_time, summarizer):
        mock_types.Part.from_text.return_value = 'text_part'
        mock_response = MagicMock()
        mock_response.text = 'Summary with article context.'
        summarizer._mock_client.models.generate_content.return_value = mock_response

        result = summarizer.summarize_post(
            account='karpathy',
            post_text='Great read on transformers',
            article_text='This article explains transformer architecture in detail...',
        )

        assert result == 'Summary with article context.'
        # Verify prompt included article text
        call_args = mock_types.Part.from_text.call_args
        assert 'Linked article' in call_args[1]['text']

    @patch('summarizer.gemini_summarizer.time')
    @patch('summarizer.gemini_summarizer.types')
    def test_post_with_video_transcript(self, mock_types, mock_time, summarizer):
        mock_types.Part.from_text.return_value = 'text_part'
        mock_response = MagicMock()
        mock_response.text = 'Summary with video context.'
        summarizer._mock_client.models.generate_content.return_value = mock_response

        result = summarizer.summarize_post(
            account='lexfridman',
            post_text='New podcast episode',
            video_transcript='In this episode we discuss AI safety...',
        )

        assert result == 'Summary with video context.'
        call_args = mock_types.Part.from_text.call_args
        assert 'Video transcript' in call_args[1]['text']

    @patch('summarizer.gemini_summarizer.time')
    @patch('summarizer.gemini_summarizer.types')
    def test_post_with_image(self, mock_types, mock_time, summarizer):
        mock_types.Part.from_text.return_value = 'text_part'
        mock_types.Part.from_bytes.return_value = 'image_part'
        mock_response = MagicMock()
        mock_response.text = 'Summary with image analysis.'
        summarizer._mock_client.models.generate_content.return_value = mock_response

        result = summarizer.summarize_post(
            account='demishassabis',
            post_text='Check out this chart',
            image_bytes=b'\xff\xd8\xff\xe0fake_jpeg_data',
        )

        assert result == 'Summary with image analysis.'
        mock_types.Part.from_bytes.assert_called_once_with(
            data=b'\xff\xd8\xff\xe0fake_jpeg_data',
            mime_type='image/jpeg',
        )

    @patch('summarizer.gemini_summarizer.time')
    @patch('summarizer.gemini_summarizer.types')
    def test_truncates_long_article(self, mock_types, mock_time, summarizer):
        mock_types.Part.from_text.return_value = 'text_part'
        mock_response = MagicMock()
        mock_response.text = 'Summary.'
        summarizer._mock_client.models.generate_content.return_value = mock_response

        long_article = 'x' * 5000
        summarizer.summarize_post(
            account='user',
            post_text='Post',
            article_text=long_article,
        )

        call_args = mock_types.Part.from_text.call_args
        prompt_text = call_args[1]['text']
        # Article should be truncated to 3000 chars
        assert 'x' * 3000 in prompt_text
        assert 'x' * 3001 not in prompt_text

    @patch('summarizer.gemini_summarizer.time')
    @patch('summarizer.gemini_summarizer.types')
    def test_api_failure_returns_fallback(self, mock_types, mock_time, summarizer):
        mock_types.Part.from_text.return_value = 'text_part'
        summarizer._mock_client.models.generate_content.side_effect = Exception("API error")

        result = summarizer.summarize_post(
            account='user',
            post_text='Short post text',
        )

        assert result == 'Short post text'

    @patch('summarizer.gemini_summarizer.time')
    @patch('summarizer.gemini_summarizer.types')
    def test_api_failure_truncates_long_fallback(self, mock_types, mock_time, summarizer):
        mock_types.Part.from_text.return_value = 'text_part'
        summarizer._mock_client.models.generate_content.side_effect = Exception("API error")

        long_text = 'a' * 300
        result = summarizer.summarize_post(
            account='user',
            post_text=long_text,
        )

        assert len(result) == 203  # 200 chars + "..."
        assert result.endswith('...')

    @patch('summarizer.gemini_summarizer.time')
    @patch('summarizer.gemini_summarizer.types')
    def test_respects_api_delay(self, mock_types, mock_time, summarizer):
        mock_types.Part.from_text.return_value = 'text_part'
        mock_response = MagicMock()
        mock_response.text = 'Summary.'
        summarizer._mock_client.models.generate_content.return_value = mock_response

        summarizer.summarize_post(account='user', post_text='Post')
        mock_time.sleep.assert_called_once_with(1)


class TestGenerateDigestOverview:
    """Test digest overview generation."""

    @patch('summarizer.gemini_summarizer.time')
    def test_generates_overview(self, mock_time, summarizer):
        mock_response = MagicMock()
        mock_response.text = 'Key themes: AI safety and new model releases.'
        summarizer._mock_client.models.generate_content.return_value = mock_response

        result = summarizer.generate_digest_overview([
            {'account': 'OpenAI', 'summary': 'Released GPT-5.'},
            {'account': 'AnthropicAI', 'summary': 'New safety research.'},
        ])

        assert result == 'Key themes: AI safety and new model releases.'

    def test_empty_summaries(self, summarizer):
        result = summarizer.generate_digest_overview([])
        assert result == 'No new posts to summarize.'

    @patch('summarizer.gemini_summarizer.time')
    def test_api_failure_returns_fallback(self, mock_time, summarizer):
        summarizer._mock_client.models.generate_content.side_effect = Exception("API error")

        result = summarizer.generate_digest_overview([
            {'account': 'user', 'summary': 'Test.'},
        ])

        assert result == 'Unable to generate overview.'

    @patch('summarizer.gemini_summarizer.time')
    def test_includes_all_accounts_in_prompt(self, mock_time, summarizer):
        mock_response = MagicMock()
        mock_response.text = 'Overview.'
        summarizer._mock_client.models.generate_content.return_value = mock_response

        summarizer.generate_digest_overview([
            {'account': 'OpenAI', 'summary': 'Summary 1.'},
            {'account': 'karpathy', 'summary': 'Summary 2.'},
            {'account': 'a16z', 'summary': 'Summary 3.'},
        ])

        call_args = summarizer._mock_client.models.generate_content.call_args
        prompt = call_args[1]['contents']
        assert '@OpenAI' in prompt
        assert '@karpathy' in prompt
        assert '@a16z' in prompt


class TestSummarizePosts:
    """Test batch post summarization."""

    @patch('summarizer.gemini_summarizer.time')
    @patch('summarizer.gemini_summarizer.types')
    def test_summarizes_all_posts(self, mock_types, mock_time, summarizer):
        mock_types.Part.from_text.return_value = 'text_part'
        mock_response = MagicMock()
        mock_response.text = 'Post summary.'
        summarizer._mock_client.models.generate_content.return_value = mock_response

        posts = [
            {'account': 'OpenAI', 'content': 'Post 1'},
            {'account': 'karpathy', 'content': 'Post 2'},
        ]

        result = summarizer.summarize_posts(posts)
        assert len(result) == 2
        assert result[0]['summary'] == 'Post summary.'
        assert result[1]['summary'] == 'Post summary.'

    @patch('summarizer.gemini_summarizer.time')
    def test_empty_posts(self, mock_time, summarizer):
        result = summarizer.summarize_posts([])
        assert result == []

    @patch('summarizer.gemini_summarizer.time')
    @patch('summarizer.gemini_summarizer.types')
    def test_preserves_original_post_data(self, mock_types, mock_time, summarizer):
        mock_types.Part.from_text.return_value = 'text_part'
        mock_response = MagicMock()
        mock_response.text = 'Summary.'
        summarizer._mock_client.models.generate_content.return_value = mock_response

        posts = [{'account': 'user', 'content': 'Original', 'post_id': '123'}]
        result = summarizer.summarize_posts(posts)

        assert result[0]['post_id'] == '123'
        assert result[0]['content'] == 'Original'
        assert result[0]['summary'] == 'Summary.'
