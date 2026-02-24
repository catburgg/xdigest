"""Email delivery service for sending digest emails.

Renders HTML email from Jinja2 template and sends via SMTP.
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).parent.parent / 'templates'


class EmailSender:
    """Sends digest emails via SMTP."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        from_email: str,
        to_email: str,
    ):
        """Initialize email sender.

        Args:
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port (typically 587 for TLS)
            smtp_user: SMTP username
            smtp_password: SMTP password
            from_email: Sender email address
            to_email: Recipient email address
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.from_email = from_email
        self.to_email = to_email

        # Setup Jinja2 template environment
        self.jinja_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

    def render_digest(
        self,
        posts: List[Dict[str, Any]],
        overview: str = "",
        date: str = None,
    ) -> str:
        """Render digest HTML from template.

        Args:
            posts: List of post dicts with keys: account, timestamp, content,
                   summary, urls, post_url, media_type
            overview: Digest overview text (key themes)
            date: Date string for email header (defaults to today)

        Returns:
            Rendered HTML string
        """
        if date is None:
            date = datetime.now().strftime('%B %d, %Y')

        template = self.jinja_env.get_template('digest.html')

        # Calculate stats
        account_count = len(set(p.get('account', '') for p in posts))
        post_count = len(posts)

        return template.render(
            posts=posts,
            overview=overview,
            date=date,
            account_count=account_count,
            post_count=post_count,
        )

    def send_digest(
        self,
        posts: List[Dict[str, Any]],
        overview: str = "",
        subject: str = None,
    ) -> bool:
        """Send digest email.

        Args:
            posts: List of post dicts
            overview: Digest overview text
            subject: Email subject (defaults to "X Digest - [date]")

        Returns:
            True if sent successfully, False otherwise
        """
        if not posts:
            logger.warning("No posts to send in digest")
            return False

        # Render HTML
        html_content = self.render_digest(posts, overview)

        # Create email
        if subject is None:
            subject = f"X Digest - {datetime.now().strftime('%B %d, %Y')}"

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.from_email
        msg['To'] = self.to_email

        # Attach HTML
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)

        # Send via SMTP
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Digest email sent successfully to {self.to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send digest email: {e}")
            return False
