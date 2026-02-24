"""Video processor for XDigest.

Extracts transcripts and metadata from video URLs.
Supports YouTube (transcript API), and other platforms (yt-dlp metadata).
"""

import logging
import re
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class VideoInfo:
    """Extracted video data."""
    url: str
    title: str = ""
    transcript: str = ""
    description: str = ""
    duration: Optional[int] = None  # seconds
    thumbnail_url: str = ""
    source: str = ""  # extraction method used


def extract_youtube_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from URL.

    Handles:
        - youtube.com/watch?v=ID
        - youtu.be/ID
        - youtube.com/embed/ID
        - youtube.com/shorts/ID

    Args:
        url: YouTube URL

    Returns:
        Video ID or None
    """
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/shorts/)([a-zA-Z0-9_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def is_youtube_url(url: str) -> bool:
    """Check if URL is a YouTube video."""
    return extract_youtube_id(url) is not None


def process_video(url: str) -> Optional[VideoInfo]:
    """Process a video URL and extract available information.

    Fallback chain:
    1. YouTube transcript (if YouTube URL)
    2. yt-dlp metadata (title, description, duration)
    3. None if all fail

    Args:
        url: Video URL

    Returns:
        VideoInfo object or None
    """
    logger.info(f"Processing video: {url}")

    # Try YouTube transcript first
    if is_youtube_url(url):
        info = _get_youtube_transcript(url)
        if info and info.transcript:
            return info

    # Fallback to yt-dlp metadata
    info = _get_ytdlp_metadata(url)
    if info:
        return info

    logger.warning(f"Failed to process video: {url}")
    return None


def _get_youtube_transcript(url: str) -> Optional[VideoInfo]:
    """Get YouTube video transcript.

    Args:
        url: YouTube URL

    Returns:
        VideoInfo with transcript or None
    """
    video_id = extract_youtube_id(url)
    if not video_id:
        return None

    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)

        # Combine transcript segments into full text
        transcript_text = " ".join(
            segment['text'] for segment in transcript_list
        )

        return VideoInfo(
            url=url,
            transcript=transcript_text,
            source='youtube_transcript',
        )

    except Exception as e:
        logger.debug(f"YouTube transcript failed for {video_id}: {e}")
        return None


def _get_ytdlp_metadata(url: str) -> Optional[VideoInfo]:
    """Get video metadata using yt-dlp (no download).

    Args:
        url: Video URL

    Returns:
        VideoInfo with metadata or None
    """
    try:
        import yt_dlp

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'extract_flat': False,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if not info:
            return None

        return VideoInfo(
            url=url,
            title=info.get('title', ''),
            description=info.get('description', ''),
            duration=info.get('duration'),
            thumbnail_url=info.get('thumbnail', ''),
            source='yt_dlp',
        )

    except Exception as e:
        logger.debug(f"yt-dlp failed for {url}: {e}")
        return None
