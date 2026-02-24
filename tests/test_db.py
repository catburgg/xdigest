"""Unit tests for storage/db.py — SQLite state management."""

import os
import json
import tempfile
import pytest
from datetime import datetime
from pathlib import Path

from storage.db import Database


@pytest.fixture
def db(tmp_path):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test.db"
    return Database(db_path)


class TestDatabaseInit:
    """Test database initialization and schema creation."""

    def test_creates_db_file(self, tmp_path):
        db_path = tmp_path / "test.db"
        Database(db_path)
        assert db_path.exists()

    def test_creates_parent_directories(self, tmp_path):
        db_path = tmp_path / "nested" / "dir" / "test.db"
        Database(db_path)
        assert db_path.exists()

    def test_schema_tables_exist(self, db):
        conn = db._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row['name'] for row in cursor.fetchall()}
        conn.close()
        assert 'digests' in tables
        assert 'posts' in tables
        assert 'state' in tables


class TestLastSentTimestamp:
    """Test last_sent_at state tracking."""

    def test_returns_none_when_never_sent(self, db):
        assert db.get_last_sent_timestamp() is None

    def test_set_and_get_timestamp(self, db):
        now = datetime(2026, 2, 24, 7, 0, 0)
        db.set_last_sent_timestamp(now)
        result = db.get_last_sent_timestamp()
        assert result == now

    def test_update_timestamp(self, db):
        first = datetime(2026, 2, 24, 7, 0, 0)
        second = datetime(2026, 2, 24, 19, 0, 0)
        db.set_last_sent_timestamp(first)
        db.set_last_sent_timestamp(second)
        assert db.get_last_sent_timestamp() == second


class TestDigests:
    """Test digest record creation."""

    def test_create_digest(self, db):
        digest_id = db.create_digest(post_count=10)
        assert digest_id is not None
        assert isinstance(digest_id, int)

    def test_multiple_digests_increment_id(self, db):
        id1 = db.create_digest(5)
        id2 = db.create_digest(10)
        assert id2 > id1


class TestPosts:
    """Test post storage and deduplication."""

    def test_add_post(self, db):
        post = {
            'post_id': '123456',
            'account': 'testuser',
            'content': 'Hello world',
            'post_timestamp': datetime.now().isoformat(),
            'has_link': True,
            'has_video': False,
            'has_image': False,
        }
        db.add_post(post)
        assert db.post_exists('123456')

    def test_post_not_exists(self, db):
        assert not db.post_exists('nonexistent')

    def test_duplicate_post_ignored(self, db):
        post = {
            'post_id': 'dup123',
            'account': 'testuser',
            'content': 'Duplicate post',
        }
        db.add_post(post)
        db.add_post(post)  # Should not raise
        assert db.post_exists('dup123')

    def test_add_post_with_digest_id(self, db):
        digest_id = db.create_digest(1)
        post = {
            'post_id': 'linked_post',
            'account': 'testuser',
            'content': 'Linked to digest',
        }
        db.add_post(post, digest_id=digest_id)
        assert db.post_exists('linked_post')

    def test_get_recent_posts(self, db):
        for i in range(5):
            db.add_post({
                'post_id': f'post_{i}',
                'account': 'testuser',
                'content': f'Post {i}',
                'post_timestamp': datetime(2026, 2, 24, i).isoformat(),
            })
        posts = db.get_recent_posts(limit=3)
        assert len(posts) == 3

    def test_get_recent_posts_empty(self, db):
        posts = db.get_recent_posts()
        assert posts == []


class TestSessionCookies:
    """Test session cookie persistence."""

    def test_no_cookies_initially(self, db):
        assert db.get_session_cookies() is None

    def test_save_and_load_cookies(self, db):
        cookies = [
            {'name': 'auth_token', 'value': 'abc123', 'domain': '.x.com'},
            {'name': 'ct0', 'value': 'def456', 'domain': '.x.com'},
        ]
        db.save_session_cookies(cookies)
        loaded = db.get_session_cookies()
        assert loaded == cookies

    def test_update_cookies(self, db):
        old = [{'name': 'old', 'value': '1'}]
        new = [{'name': 'new', 'value': '2'}]
        db.save_session_cookies(old)
        db.save_session_cookies(new)
        assert db.get_session_cookies() == new
