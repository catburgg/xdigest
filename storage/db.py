"""SQLite database for state management.

Tracks:
- Last sent timestamp
- Session cookies
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
            db_path: Path to SQLite database file (or ':memory:' for in-memory DB)
        """
        self.db_path = db_path
        # Only create directory if not using in-memory database
        if db_path != ':memory:' and isinstance(db_path, Path):
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
        """Get timestamp of last sent digest."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT value FROM state WHERE key = 'last_sent_at'")
        row = cursor.fetchone()
        conn.close()

        if row:
            return datetime.fromisoformat(row['value'])
        return None

    def set_last_sent_timestamp(self, timestamp: datetime):
        """Update last sent timestamp."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO state (key, value)
            VALUES ('last_sent_at', ?)
        """, (timestamp.isoformat(),))

        conn.commit()
        conn.close()

    def get_session_cookies(self) -> Optional[List[Dict]]:
        """Get saved session cookies."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT value FROM state WHERE key = 'session_cookies'")
        row = cursor.fetchone()
        conn.close()

        if row:
            return json.loads(row['value'])
        return None

    def save_session_cookies(self, cookies: List[Dict]):
        """Save session cookies."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO state (key, value)
            VALUES ('session_cookies', ?)
        """, (json.dumps(cookies),))

        conn.commit()
        conn.close()
