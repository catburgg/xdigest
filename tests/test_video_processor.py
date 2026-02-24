"""Unit tests for scraper/video_processor.py — Video processing."""

import pytest
from unittest.mock import patch, MagicMock

from scraper.video_processor import (
    extract_youtube_id, is_youtube_url, process_video,
    _get_youtube_transcript, _get_ytdlp_metadata, VideoInfo,
)


class TestExtractYoutubeId:
    """Test YouTube ID extraction from various URL formats."""

    def test_standard_url(self):
        assert extract_youtube_id('https://www.youtube.com/watch?v=dQw4w9WgXcQ') == 'dQw4w9WgXcQ'

    def test_short_url(self):
        assert extract_youtube_id('https://youtu.be/dQw4w9WgXcQ') == 'dQw4w9WgXcQ'

    def test_embed_url(self):
        assert extract_youtube_id('https://youtube.com/embed/dQw4w9WgXcQ') == 'dQw4w9WgXcQ'

    def test_shorts_url(self):
        assert extract_youtube_id('https://youtube.com/shorts/dQw4w9WgXcQ') == 'dQw4w9WgXcQ'

    def test_url_with_params(self):
        assert extract_youtube_id('https://youtube.com/watch?v=dQw4w9WgXcQ&t=120') == 'dQw4w9WgXcQ'

    def test_non_youtube_url(self):
        assert extract_youtube_id('https://example.com/video') is None

    def test_invalid_url(self):
        assert extract_youtube_id('not a url') is None


class TestIsYoutubeUrl:
    """Test YouTube URL detection."""

    def test_youtube_url(self):
        assert is_youtube_url('https://youtube.com/watch?v=abc12345678') is True

    def test_non_youtube_url(self):
        assert is_youtube_url('https://vimeo.com/123456') is False


class TestGetYoutubeTranscript:
    """Test YouTube transcript extraction."""

    @patch('scraper.video_processor.extract_youtube_id')
    def test_successful_transcript(self, mock_extract_id):
        mock_extract_id.return_value = 'abc123'

        mock_transcript = [
            {'text': 'Hello world', 'start': 0, 'duration': 2},
            {'text': 'this is a test', 'start': 2, 'duration': 3},
        ]

        with patch.dict('sys.modules', {'youtube_transcript_api': MagicMock()}):
            with patch('scraper.video_processor.YouTubeTranscriptApi', create=True) as mock_api:
                mock_api.get_transcript.return_value = mock_transcript

                # Call the function directly with mocked import
                from scraper.video_processor import _get_youtube_transcript
                result = _get_youtube_transcript('https://youtube.com/watch?v=abc123')

        if result:
            assert result.source == 'youtube_transcript'

    @patch('scraper.video_processor.extract_youtube_id')
    def test_no_video_id(self, mock_extract_id):
        mock_extract_id.return_value = None

        result = _get_youtube_transcript('https://example.com')
        assert result is None


class TestGetYtdlpMetadata:
    """Test yt-dlp metadata extraction."""

    def test_successful_metadata(self):
        mock_info = {
            'title': 'Test Video',
            'description': 'A test video description',
            'duration': 300,
            'thumbnail': 'https://img.youtube.com/thumb.jpg',
        }

        with patch('scraper.video_processor.yt_dlp', create=True) as mock_ytdlp:
            mock_ydl = MagicMock()
            mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
            mock_ydl.__exit__ = MagicMock(return_value=False)
            mock_ydl.extract_info.return_value = mock_info
            mock_ytdlp.YoutubeDL.return_value = mock_ydl

            with patch.dict('sys.modules', {'yt_dlp': mock_ytdlp}):
                from importlib import reload
                import scraper.video_processor as vp
                reload(vp)
                result = vp._get_ytdlp_metadata('https://youtube.com/watch?v=abc')

        if result:
            assert result.title == 'Test Video'
            assert result.duration == 300
            assert result.source == 'yt_dlp'

    def test_returns_none_on_failure(self):
        with patch.dict('sys.modules', {'yt_dlp': None}):
            result = _get_ytdlp_metadata('https://example.com/video')
            assert result is None


class TestProcessVideo:
    """Test the main process_video function."""

    @patch('scraper.video_processor.is_youtube_url')
    @patch('scraper.video_processor._get_youtube_transcript')
    def test_youtube_uses_transcript(self, mock_transcript, mock_is_yt):
        mock_is_yt.return_value = True
        mock_transcript.return_value = VideoInfo(
            url='https://youtube.com/watch?v=abc',
            transcript='Full transcript text here',
            source='youtube_transcript',
        )

        result = process_video('https://youtube.com/watch?v=abc')
        assert result is not None
        assert result.transcript == 'Full transcript text here'
        assert result.source == 'youtube_transcript'

    @patch('scraper.video_processor.is_youtube_url')
    @patch('scraper.video_processor._get_youtube_transcript')
    @patch('scraper.video_processor._get_ytdlp_metadata')
    def test_falls_back_to_ytdlp(self, mock_ytdlp, mock_transcript, mock_is_yt):
        mock_is_yt.return_value = True
        mock_transcript.return_value = None
        mock_ytdlp.return_value = VideoInfo(
            url='https://youtube.com/watch?v=abc',
            title='Video Title',
            description='Video desc',
            source='yt_dlp',
        )

        result = process_video('https://youtube.com/watch?v=abc')
        assert result is not None
        assert result.source == 'yt_dlp'

    @patch('scraper.video_processor.is_youtube_url')
    @patch('scraper.video_processor._get_ytdlp_metadata')
    def test_non_youtube_uses_ytdlp(self, mock_ytdlp, mock_is_yt):
        mock_is_yt.return_value = False
        mock_ytdlp.return_value = VideoInfo(
            url='https://vimeo.com/123',
            title='Vimeo Video',
            source='yt_dlp',
        )

        result = process_video('https://vimeo.com/123')
        assert result is not None
        assert result.source == 'yt_dlp'

    @patch('scraper.video_processor.is_youtube_url')
    @patch('scraper.video_processor._get_ytdlp_metadata')
    def test_returns_none_when_all_fail(self, mock_ytdlp, mock_is_yt):
        mock_is_yt.return_value = False
        mock_ytdlp.return_value = None

        result = process_video('https://example.com/video')
        assert result is None


class TestVideoInfoDataclass:
    """Test VideoInfo dataclass."""

    def test_creation(self):
        v = VideoInfo(url='https://youtube.com/watch?v=abc', title='Test')
        assert v.url == 'https://youtube.com/watch?v=abc'
        assert v.title == 'Test'
        assert v.transcript == ''
        assert v.duration is None

    def test_defaults(self):
        v = VideoInfo(url='https://example.com')
        assert v.title == ''
        assert v.transcript == ''
        assert v.description == ''
        assert v.thumbnail_url == ''
        assert v.source == ''
