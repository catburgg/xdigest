"""Unit tests for email_service/sender.py — Email delivery."""

import pytest
from unittest.mock import patch, MagicMock, call
from datetime import datetime
from pathlib import Path

from email_service.sender import EmailSender, TEMPLATE_DIR


@pytest.fixture
def sender():
    """Create an EmailSender instance."""
    return EmailSender(
        smtp_host='smtp.gmail.com',
        smtp_port=587,
        smtp_user='user@gmail.com',
        smtp_password='password123',
        from_email='user@gmail.com',
        to_email='recipient@example.com',
    )


class TestEmailSenderInit:
    """Test EmailSender initialization."""

    def test_stores_smtp_config(self, sender):
        assert sender.smtp_host == 'smtp.gmail.com'
        assert sender.smtp_port == 587
        assert sender.smtp_user == 'user@gmail.com'
        assert sender.smtp_password == 'password123'

    def test_stores_email_addresses(self, sender):
        assert sender.from_email == 'user@gmail.com'
        assert sender.to_email == 'recipient@example.com'

    def test_initializes_jinja_env(self, sender):
        assert sender.jinja_env is not None
        # Verify template directory is correct
        loader = sender.jinja_env.loader
        assert str(TEMPLATE_DIR) in str(loader.searchpath)


class TestRenderDigest:
    """Test HTML rendering."""

    def test_renders_basic_digest(self, sender):
        posts = [
            {
                'account': 'OpenAI',
                'timestamp': '2024-01-15 10:30',
                'content': 'We released GPT-5!',
                'summary': 'OpenAI announces GPT-5.',
                'urls': ['https://openai.com/gpt5'],
                'post_url': 'https://x.com/OpenAI/status/123',
                'media_type': None,
            }
        ]

        html = sender.render_digest(posts, overview='Big AI news today.')

        assert 'OpenAI' in html
        assert 'We released GPT-5!' in html
        assert 'OpenAI announces GPT-5.' in html
        assert 'Big AI news today.' in html
        assert 'https://openai.com/gpt5' in html

    def test_renders_with_custom_date(self, sender):
        posts = [{'account': 'user', 'content': 'test'}]
        html = sender.render_digest(posts, date='January 1, 2024')
        assert 'January 1, 2024' in html

    def test_renders_with_default_date(self, sender):
        posts = [{'account': 'user', 'content': 'test'}]
        html = sender.render_digest(posts)
        # Should contain current date
        today = datetime.now().strftime('%B %d, %Y')
        assert today in html

    def test_calculates_account_count(self, sender):
        posts = [
            {'account': 'OpenAI', 'content': 'Post 1'},
            {'account': 'OpenAI', 'content': 'Post 2'},
            {'account': 'karpathy', 'content': 'Post 3'},
        ]
        html = sender.render_digest(posts)
        assert '3 posts from 2 accounts' in html

    def test_renders_image_badge(self, sender):
        posts = [
            {
                'account': 'user',
                'content': 'Check this out',
                'media_type': 'image',
            }
        ]
        html = sender.render_digest(posts)
        assert '📷 Image' in html

    def test_renders_video_badge(self, sender):
        posts = [
            {
                'account': 'user',
                'content': 'Watch this',
                'media_type': 'video',
            }
        ]
        html = sender.render_digest(posts)
        assert '🎥 Video' in html

    def test_renders_multiple_urls(self, sender):
        posts = [
            {
                'account': 'user',
                'content': 'Multiple links',
                'urls': ['https://example.com/1', 'https://example.com/2'],
            }
        ]
        html = sender.render_digest(posts)
        assert 'https://example.com/1' in html
        assert 'https://example.com/2' in html

    def test_handles_empty_overview(self, sender):
        posts = [{'account': 'user', 'content': 'test'}]
        html = sender.render_digest(posts, overview='')
        # Should still render without errors
        assert 'user' in html


class TestSendDigest:
    """Test email sending."""

    @patch('email_service.sender.smtplib.SMTP')
    def test_sends_email_successfully(self, mock_smtp_cls, sender):
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        posts = [
            {
                'account': 'OpenAI',
                'timestamp': '2024-01-15 10:30',
                'content': 'Test post',
                'summary': 'Summary',
            }
        ]

        result = sender.send_digest(posts, overview='Overview')

        assert result is True
        mock_smtp_cls.assert_called_once_with('smtp.gmail.com', 587)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with('user@gmail.com', 'password123')
        mock_server.send_message.assert_called_once()

    @patch('email_service.sender.smtplib.SMTP')
    def test_email_has_correct_headers(self, mock_smtp_cls, sender):
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        posts = [{'account': 'user', 'content': 'test'}]
        sender.send_digest(posts)

        # Get the message that was sent
        call_args = mock_server.send_message.call_args[0]
        msg = call_args[0]

        assert msg['From'] == 'user@gmail.com'
        assert msg['To'] == 'recipient@example.com'
        assert 'X Digest' in msg['Subject']

    @patch('email_service.sender.smtplib.SMTP')
    def test_custom_subject(self, mock_smtp_cls, sender):
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        posts = [{'account': 'user', 'content': 'test'}]
        sender.send_digest(posts, subject='Custom Subject')

        call_args = mock_server.send_message.call_args[0]
        msg = call_args[0]
        assert msg['Subject'] == 'Custom Subject'

    def test_returns_false_for_empty_posts(self, sender):
        result = sender.send_digest([])
        assert result is False

    @patch('email_service.sender.smtplib.SMTP')
    def test_returns_false_on_smtp_error(self, mock_smtp_cls, sender):
        mock_smtp_cls.return_value.__enter__.side_effect = Exception("SMTP error")

        posts = [{'account': 'user', 'content': 'test'}]
        result = sender.send_digest(posts)

        assert result is False

    @patch('email_service.sender.smtplib.SMTP')
    def test_returns_false_on_login_error(self, mock_smtp_cls, sender):
        mock_server = MagicMock()
        mock_server.login.side_effect = Exception("Auth failed")
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        posts = [{'account': 'user', 'content': 'test'}]
        result = sender.send_digest(posts)

        assert result is False

    @patch('email_service.sender.smtplib.SMTP')
    def test_email_contains_html(self, mock_smtp_cls, sender):
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        posts = [{'account': 'OpenAI', 'content': 'GPT-5 released'}]
        sender.send_digest(posts)

        # Verify HTML content was sent
        call_args = mock_server.send_message.call_args[0]
        msg = call_args[0]

        # Get the HTML part
        payload = msg.get_payload()
        html_part = payload[0]
        html_content = html_part.get_payload(decode=True).decode('utf-8')

        assert 'OpenAI' in html_content
        assert 'GPT-5 released' in html_content
