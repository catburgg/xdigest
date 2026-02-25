"""SQLite database for state management.

Tracks:
- Last sent timestamp
- Post history (deduplication)
- Session cookies
- Digest history
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any


class Database:
    """SQLite database manager."""

    def __init__(self, db_path: Path):
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self):
        """Initialize database schema."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Digests table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS digests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sent_at TIMESTAMP NOT NULL,
                post_count INTEGER,
                status TEXT DEFAULT 'success'
            )
        """)

        # Posts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id TEXT UNIQUE NOT NULL,
                account TEXT NOT NULL,
                content TEXT,
                post_timestamp TIMESTAMP,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                digest_id INTEGER REFERENCES digests(id),
                has_link BOOLEAN DEFAULT FALSE,
                has_video BOOLEAN DEFAULT FALSE,
                has_image BOOLEAN DEFAULT FALSE,
                summary TEXT
            )
        """)

        # State table (key-value store)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS state (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        conn.commit()
        conn.close()

    def get_last_sent_timestamp(self) -> Optional[datetime]:
        """Get timestamp of last sent digest.

        Returns:
            Last sent timestamp or None if never sent
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT value FROM state WHERE key = 'last_sent_at'")
        row = cursor.fetchone()
        conn.close()

        if row:
            return datetime.fromisoformat(row['value'])
        return None

    def set_last_sent_timestamp(self, timestamp: datetime):
        """Update last sent timestamp.

        Args:
            timestamp: Timestamp to store
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO state (key, value)
            VALUES ('last_sent_at', ?)
        """, (timestamp.isoformat(),))

        conn.commit()
        conn.close()

    def create_digest(self, post_count: int) -> int:
        """Create a new digest record.

        Args:
            post_count: Number of posts in digest

        Returns:
            Digest ID
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO digests (sent_at, post_count, status)
            VALUES (?, ?, 'success')
        """, (datetime.now(), post_count))

        digest_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return digest_id

    def add_post(self, post_data: Dict[str, Any], digest_id: Optional[int] = None):
        """Add a post to the database.

        Args:
            post_data: Post data dictionary
            digest_id: Optional digest ID to associate with
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO posts (
                    post_id, account, content, post_timestamp,
                    digest_id, has_link, has_video, has_image, summary
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                post_data['post_id'],
                post_data['account'],
                post_data.get('content'),
                post_data.get('post_timestamp'),
                digest_id,
                post_data.get('has_link', False),
                post_data.get('has_video', False),
                post_data.get('has_image', False),
                post_data.get('summary')
            ))
            conn.commit()
        except sqlite3.IntegrityError:
            # Post already exists (duplicate)
            pass
        finally:
            conn.close()

    def post_exists(self, post_id: str) -> bool:
        """Check if a post already exists in database.

        Args:
            post_id: Post ID to check

        Returns:
            True if post exists
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT 1 FROM posts WHERE post_id = ?", (post_id,))
        exists = cursor.fetchone() is not None

        conn.close()
        return exists

    def get_session_cookies(self) -> Optional[List[Dict]]:
        """Get saved session cookies.

        Returns:
            List of cookie dictionaries or None
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT value FROM state WHERE key = 'session_cookies'")
        row = cursor.fetchone()
        conn.close()

        if row:
            return json.loads(row['value'])
        return None

    def save_session_cookies(self, cookies: List[Dict]):
        """Save session cookies.

        Args:
            cookies: List of cookie dictionaries
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO state (key, value)
            VALUES ('session_cookies', ?)
        """, (json.dumps(cookies),))

        conn.commit()
        conn.close()

    def get_recent_posts(self, limit: int = 100) -> List[Dict]:
        """Get recent posts from database.

        Args:
            limit: Maximum number of posts to return

        Returns:
            List of post dictionaries
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM posts
            ORDER BY post_timestamp DESC
            LIMIT ?
        """, (limit,))

        posts = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return posts

    def cleanup_old_posts(self, keep_days: int = 7):
        """Clean up old posts from database, keeping only recent ones for deduplication.

        Args:
            keep_days: Number of days of posts to keep (default: 7)
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM posts
            WHERE scraped_at < datetime('now', '-' || ? || ' days')
        """, (keep_days,))

        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        return deleted

    def cleanup_old_digests(self, keep_count: int = 10):
        """Clean up old digest records, keeping only the most recent ones.

        Args:
            keep_count: Number of recent digests to keep (default: 10)
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM digests
            WHERE id NOT IN (
                SELECT id FROM digests
                ORDER BY sent_at DESC
                LIMIT ?
            )
        """, (keep_count,))

        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        return deleted
