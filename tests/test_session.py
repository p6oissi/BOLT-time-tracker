"""Tests for SessionTracker time accumulation and entry merging logic."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from tracker.models import WindowSnapshot
from tracker.session import SessionTracker, _MIN_ENTRY_SECONDS


def make_snapshot(process: str, title: str, offset_seconds: float = 0.0) -> WindowSnapshot:
    """Build a WindowSnapshot at a fixed base time + offset (for deterministic tests)."""
    base = datetime(2026, 4, 25, 9, 0, 0)
    return WindowSnapshot(
        timestamp=base + timedelta(seconds=offset_seconds),
        process_name=process,
        window_title=title,
    )


class TestSessionLifecycle:
    def test_start_creates_session(self) -> None:
        tracker = SessionTracker()
        session = tracker.start("My Session")
        assert session.session_name == "My Session"
        assert session.session_id != ""
        assert session.end_time is None

    def test_start_generates_name_when_empty(self) -> None:
        tracker = SessionTracker()
        session = tracker.start("")
        assert session.session_name.startswith("Session ")

    def test_tick_before_start_raises(self) -> None:
        tracker = SessionTracker()
        with pytest.raises(RuntimeError, match="start()"):
            tracker.tick(make_snapshot("chrome.exe", "Google"))

    def test_stop_before_start_raises(self) -> None:
        tracker = SessionTracker()
        with pytest.raises(RuntimeError, match="start()"):
            tracker.stop()

    def test_stop_sets_end_time(self) -> None:
        tracker = SessionTracker()
        tracker.start("test")
        base = datetime(2026, 4, 25, 9, 0, 0)
        with patch("tracker.session.datetime") as mock_dt:
            mock_dt.now.return_value = base + timedelta(seconds=30)
            session = tracker.stop()
        assert session.end_time is not None


class TestEntryMerging:
    def test_same_window_produces_one_entry(self) -> None:
        """Consecutive ticks on the same window should merge into a single entry."""
        tracker = SessionTracker()
        tracker.start("test")
        snap = make_snapshot("pycharm64.exe", "main.py - Project")
        base = datetime(2026, 4, 25, 9, 0, 0)
        for i in range(4):  # 0s, 15s, 30s, 45s
            with patch("tracker.session.datetime") as mock_dt:
                mock_dt.now.return_value = base + timedelta(seconds=i * 15)
                tracker.tick(snap)
        # Switch to a different window to commit the entry
        with patch("tracker.session.datetime") as mock_dt:
            mock_dt.now.return_value = base + timedelta(seconds=60)
            tracker.tick(make_snapshot("chrome.exe", "Google Chrome"))
        with patch("tracker.session.datetime") as mock_dt:
            mock_dt.now.return_value = base + timedelta(seconds=75)
            session = tracker.stop()

        coding_entries = [e for e in session.entries if e.category == "coding"]
        assert len(coding_entries) == 1, f"Expected 1 coding entry, got {len(coding_entries)}"

    def test_category_switch_creates_new_entry(self) -> None:
        """Switching from coding to browsing should produce two separate entries."""
        tracker = SessionTracker()
        tracker.start("test")
        base = datetime(2026, 4, 25, 9, 0, 0)

        ticks = [
            (0,  make_snapshot("pycharm64.exe", "main.py")),
            (15, make_snapshot("pycharm64.exe", "main.py")),
            (30, make_snapshot("pycharm64.exe", "main.py")),
            (45, make_snapshot("chrome.exe", "Google Chrome")),  # switch
            (60, make_snapshot("chrome.exe", "Google Chrome")),
            (75, make_snapshot("chrome.exe", "Google Chrome")),
        ]
        for offset, snap in ticks:
            with patch("tracker.session.datetime") as mock_dt:
                mock_dt.now.return_value = base + timedelta(seconds=offset)
                tracker.tick(snap)

        with patch("tracker.session.datetime") as mock_dt:
            mock_dt.now.return_value = base + timedelta(seconds=90)
            session = tracker.stop()

        categories = [e.category for e in session.entries]
        assert "coding" in categories, "Expected a coding entry"
        assert "browsing" in categories, "Expected a browsing entry"

    def test_short_entry_is_ignored(self) -> None:
        """Entries shorter than _MIN_ENTRY_SECONDS should not be committed."""
        tracker = SessionTracker()
        tracker.start("test")
        base = datetime(2026, 4, 25, 9, 0, 0)
        # Appear for 5 seconds (less than _MIN_ENTRY_SECONDS = 10)
        with patch("tracker.session.datetime") as mock_dt:
            mock_dt.now.return_value = base
            tracker.tick(make_snapshot("pycharm64.exe", "quick.py"))
        with patch("tracker.session.datetime") as mock_dt:
            mock_dt.now.return_value = base + timedelta(seconds=5)
            tracker.tick(make_snapshot("chrome.exe", "Chrome"))  # switch after 5s
        with patch("tracker.session.datetime") as mock_dt:
            mock_dt.now.return_value = base + timedelta(seconds=60)
            session = tracker.stop()

        short_coding = [e for e in session.entries if e.category == "coding" and e.duration_seconds < _MIN_ENTRY_SECONDS]
        assert len(short_coding) == 0, "Short entries must not be committed"

    def test_entry_duration_reflects_actual_time(self) -> None:
        """The committed entry's duration should match the time observed on that window."""
        tracker = SessionTracker()
        tracker.start("test")
        base = datetime(2026, 4, 25, 9, 0, 0)

        for i in range(5):  # 0..60s on PyCharm
            with patch("tracker.session.datetime") as mock_dt:
                mock_dt.now.return_value = base + timedelta(seconds=i * 15)
                tracker.tick(make_snapshot("pycharm64.exe", "auth.py"))
        # Switch at t=60 to commit the 60-second coding entry
        with patch("tracker.session.datetime") as mock_dt:
            mock_dt.now.return_value = base + timedelta(seconds=60)
            tracker.tick(make_snapshot("chrome.exe", "Chrome"))
        with patch("tracker.session.datetime") as mock_dt:
            mock_dt.now.return_value = base + timedelta(seconds=75)
            session = tracker.stop()

        coding = [e for e in session.entries if e.category == "coding"]
        assert len(coding) == 1
        assert coding[0].duration_seconds == 60, f"Expected 60s, got {coding[0].duration_seconds}"


class TestIdleDetection:
    def test_none_snapshot_becomes_idle(self) -> None:
        """A None snapshot should create an idle entry."""
        tracker = SessionTracker()
        tracker.start("test")
        base = datetime(2026, 4, 25, 9, 0, 0)

        for i in range(6):  # 0..75s, all None
            with patch("tracker.session.datetime") as mock_dt:
                mock_dt.now.return_value = base + timedelta(seconds=i * 15)
                tracker.tick(None)

        with patch("tracker.session.datetime") as mock_dt:
            mock_dt.now.return_value = base + timedelta(seconds=90)
            session = tracker.stop()

        idle_entries = [e for e in session.entries if e.category == "idle"]
        assert len(idle_entries) >= 1, "Expected at least one idle entry"

    def test_idle_merges_into_single_entry(self) -> None:
        """Multiple consecutive None ticks must produce ONE idle entry, not one per tick.

        This covers the default 5-second interval case where per-tick entries
        would all be < _MIN_ENTRY_SECONDS and silently dropped.
        """
        tracker = SessionTracker()
        tracker.start("test")
        base = datetime(2026, 4, 25, 9, 0, 0)

        # Simulate 20 ticks at 5-second intervals (100 seconds of idle at 5s/tick)
        for i in range(20):
            with patch("tracker.session.datetime") as mock_dt:
                mock_dt.now.return_value = base + timedelta(seconds=i * 5)
                tracker.tick(None)

        with patch("tracker.session.datetime") as mock_dt:
            mock_dt.now.return_value = base + timedelta(seconds=100)
            session = tracker.stop()

        idle_entries = [e for e in session.entries if e.category == "idle"]
        assert len(idle_entries) == 1, (
            f"Expected 1 merged idle entry, got {len(idle_entries)}. "
            "Per-tick idle entries would be dropped as too short at a 5s interval."
        )

    def test_idle_excluded_from_duration_by_category(self) -> None:
        """Idle time must not appear in duration_by_category()."""
        tracker = SessionTracker()
        tracker.start("test")
        base = datetime(2026, 4, 25, 9, 0, 0)
        for i in range(6):
            with patch("tracker.session.datetime") as mock_dt:
                mock_dt.now.return_value = base + timedelta(seconds=i * 15)
                tracker.tick(None)
        with patch("tracker.session.datetime") as mock_dt:
            mock_dt.now.return_value = base + timedelta(seconds=90)
            session = tracker.stop()

        assert "idle" not in session.duration_by_category(), "Idle must be excluded from duration totals"

    def test_idle_then_active_produces_correct_sequence(self) -> None:
        """After idle, switching to a real window should resume normal tracking."""
        tracker = SessionTracker()
        tracker.start("test")
        base = datetime(2026, 4, 25, 9, 0, 0)

        # 3 ticks idle (45s total)
        for i in range(3):
            with patch("tracker.session.datetime") as mock_dt:
                mock_dt.now.return_value = base + timedelta(seconds=i * 15)
                tracker.tick(None)
        # Switch to coding (triggers idle commit)
        with patch("tracker.session.datetime") as mock_dt:
            mock_dt.now.return_value = base + timedelta(seconds=45)
            tracker.tick(make_snapshot("pycharm64.exe", "models.py"))
        # 3 more coding ticks
        for i in range(3):
            with patch("tracker.session.datetime") as mock_dt:
                mock_dt.now.return_value = base + timedelta(seconds=60 + i * 15)
                tracker.tick(make_snapshot("pycharm64.exe", "models.py"))
        with patch("tracker.session.datetime") as mock_dt:
            mock_dt.now.return_value = base + timedelta(seconds=120)
            session = tracker.stop()

        categories = [e.category for e in session.entries]
        assert "idle" in categories, "Expected an idle entry"
        assert "coding" in categories, "Expected a coding entry after idle"
