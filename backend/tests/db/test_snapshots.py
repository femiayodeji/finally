"""Tests for the portfolio_snapshots repository."""

from __future__ import annotations

import time

from app.db import insert_snapshot, list_snapshots


class TestSnapshotsRepository:
    """Unit tests for portfolio value snapshots."""

    def test_insert_and_list_snapshot(self):
        """Test a single snapshot round-trips with its total_value rounded to cents."""
        insert_snapshot(11925.4567)
        snapshots = list_snapshots()
        assert len(snapshots) == 1
        assert snapshots[0]["total_value"] == 11925.46
        assert snapshots[0]["recorded_at"]

    def test_list_snapshots_chronological(self):
        """Test list_snapshots() returns oldest first."""
        insert_snapshot(10000.0)
        time.sleep(0.002)
        insert_snapshot(10500.0)
        time.sleep(0.002)
        insert_snapshot(10250.0)
        values = [s["total_value"] for s in list_snapshots()]
        assert values == [10000.0, 10500.0, 10250.0]

    def test_list_snapshots_respects_limit(self):
        """Test list_snapshots() caps the number of rows via `limit`, keeping the most recent."""
        for value in (100.0, 200.0, 300.0, 400.0):
            insert_snapshot(value)
            time.sleep(0.002)
        limited = list_snapshots(limit=2)
        assert [s["total_value"] for s in limited] == [300.0, 400.0]

    def test_snapshots_scoped_per_user(self):
        """Test snapshots are isolated per user_id."""
        insert_snapshot(500.0, user_id="alice")
        assert list_snapshots() == []
        assert len(list_snapshots(user_id="alice")) == 1
