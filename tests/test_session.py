"""Tests for SessionTracker time accumulation and entry merging logic."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional
from unittest.mock import patch

import pytest

from tracker.models import Session, TrackerStatus, WindowSnapshot
from tracker.session import SessionTracker, _MIN_ENTRY_SECONDS

BASE = datetime(2026, 4, 25, 9, 0, 0)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def started() -> tuple[SessionTracker, datetime]:
    """A started tracker and a fixed base time for deterministic tests."""
    tracker = SessionTracker()
    tracker.start("test")
    return tracker, BASE


# ---------------------------------------------------------------------------
# Helpers — each owns exactly one responsibility
# ---------------------------------------------------------------------------

def make_snapshot(process: str, title: str, offset_seconds: float = 0.0) -> WindowSnapshot:
    """Build a WindowSnapshot at BASE + offset."""
    return WindowSnapshot(
        timestamp=BASE + timedelta(seconds=offset_seconds),
        process_name=process,
        window_title=title,
    )


def _tick_at(
    tracker: SessionTracker,
    snapshot: Optional[WindowSnapshot],
    t: datetime,
) -> None:
    """Tick the tracker with a controlled clock value."""
    with patch("tracker.session.datetime") as mock_dt:
        mock_dt.now.return_value = t
        tracker.tick(snapshot)


def _stop_at(tracker: SessionTracker, t: datetime) -> Session:
    """Stop the tracker at a controlled clock value and return the session."""
    with patch("tracker.session.datetime") as mock_dt:
        mock_dt.now.return_value = t
        return tracker.stop()


def _status_at(tracker: SessionTracker, t: datetime) -> TrackerStatus:
    """Read tracker.status at a controlled clock value."""
    with patch("tracker.session.datetime") as mock_dt:
        mock_dt.now.return_value = t
        return tracker.status


def _tick_coding(tracker: SessionTracker, base: datetime, count: int = 5, interval: int = 15) -> None:
    """Tick pycharm64.exe on auth.py 'count' times at 'interval' second intervals from 'base'."""
    for i in range(count):
        _tick_at(tracker, make_snapshot("pycharm64.exe", "auth.py"), base + timedelta(seconds=i * interval))


def _tick_idle(tracker: SessionTracker, base: datetime, count: int = 6, interval: int = 15) -> None:
    """Tick None 'count' times at 'interval' second intervals from 'base'."""
    for i in range(count):
        _tick_at(tracker, None, base + timedelta(seconds=i * interval))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

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

    def test_stop_sets_end_time(self, started: tuple[SessionTracker, datetime]) -> None:
        tracker, base = started
        session = _stop_at(tracker, base + timedelta(seconds=30))
        assert session.end_time is not None


class TestEntryMerging:
    def test_same_window_produces_one_entry(self, started: tuple[SessionTracker, datetime]) -> None:
        """Consecutive ticks on the same window should merge into a single entry."""
        tracker, base = started
        snap = make_snapshot("pycharm64.exe", "main.py - Project")
        for i in range(4):  # 0s, 15s, 30s, 45s
            _tick_at(tracker, snap, base + timedelta(seconds=i * 15))
        _tick_at(tracker, make_snapshot("chrome.exe", "Google Chrome"), base + timedelta(seconds=60))
        session = _stop_at(tracker, base + timedelta(seconds=75))

        coding_entries = [e for e in session.entries if e.category == "coding"]
        assert len(coding_entries) == 1, f"Expected 1 coding entry, got {len(coding_entries)}"

    def test_category_switch_creates_new_entry(self, started: tuple[SessionTracker, datetime]) -> None:
        """Switching from coding to browsing should produce two separate entries."""
        tracker, base = started
        ticks = [
            (0,  make_snapshot("pycharm64.exe", "main.py")),
            (15, make_snapshot("pycharm64.exe", "main.py")),
            (30, make_snapshot("pycharm64.exe", "main.py")),
            (45, make_snapshot("chrome.exe", "Google Chrome")),  # switch
            (60, make_snapshot("chrome.exe", "Google Chrome")),
            (75, make_snapshot("chrome.exe", "Google Chrome")),
        ]
        for offset, snap in ticks:
            _tick_at(tracker, snap, base + timedelta(seconds=offset))
        session = _stop_at(tracker, base + timedelta(seconds=90))

        categories = [e.category for e in session.entries]
        assert "coding" in categories, "Expected a coding entry"
        assert "browsing" in categories, "Expected a browsing entry"

    def test_short_entry_is_ignored(self, started: tuple[SessionTracker, datetime]) -> None:
        """Entries shorter than _MIN_ENTRY_SECONDS should not be committed."""
        tracker, base = started
        _tick_at(tracker, make_snapshot("pycharm64.exe", "quick.py"), base)
        _tick_at(tracker, make_snapshot("chrome.exe", "Chrome"), base + timedelta(seconds=5))
        session = _stop_at(tracker, base + timedelta(seconds=60))

        short_coding = [e for e in session.entries if e.category == "coding" and e.duration_seconds < _MIN_ENTRY_SECONDS]
        assert len(short_coding) == 0, "Short entries must not be committed"

    def test_entry_duration_reflects_actual_time(self, started: tuple[SessionTracker, datetime]) -> None:
        """The committed entry's duration should match the time observed on that window."""
        tracker, base = started
        _tick_coding(tracker, base)
        _tick_at(tracker, make_snapshot("chrome.exe", "Chrome"), base + timedelta(seconds=60))
        session = _stop_at(tracker, base + timedelta(seconds=75))

        coding = [e for e in session.entries if e.category == "coding"]
        assert len(coding) == 1
        assert coding[0].duration_seconds == 60, f"Expected 60s, got {coding[0].duration_seconds}"


class TestIdleDetection:
    def test_none_snapshot_becomes_idle(self, started: tuple[SessionTracker, datetime]) -> None:
        """A None snapshot should create an idle entry."""
        tracker, base = started
        _tick_idle(tracker, base)
        session = _stop_at(tracker, base + timedelta(seconds=90))

        idle_entries = [e for e in session.entries if e.category == "idle"]
        assert len(idle_entries) >= 1, "Expected at least one idle entry"

    def test_idle_merges_into_single_entry(self, started: tuple[SessionTracker, datetime]) -> None:
        """Multiple consecutive None ticks must produce ONE idle entry, not one per tick.

        This covers the default 5-second interval case where per-tick entries
        would all be < _MIN_ENTRY_SECONDS and silently dropped.
        """
        tracker, base = started
        _tick_idle(tracker, base, count=20, interval=5)
        session = _stop_at(tracker, base + timedelta(seconds=100))

        idle_entries = [e for e in session.entries if e.category == "idle"]
        assert len(idle_entries) == 1, (
            f"Expected 1 merged idle entry, got {len(idle_entries)}. "
            "Per-tick idle entries would be dropped as too short at a 5s interval."
        )

    def test_idle_excluded_from_duration_by_category(self, started: tuple[SessionTracker, datetime]) -> None:
        """Idle time must not appear in duration_by_category()."""
        tracker, base = started
        _tick_idle(tracker, base)
        session = _stop_at(tracker, base + timedelta(seconds=90))
        assert "idle" not in session.duration_by_category(), "Idle must be excluded from duration totals"

    def test_idle_then_active_produces_correct_sequence(self, started: tuple[SessionTracker, datetime]) -> None:
        """After idle, switching to a real window should resume normal tracking."""
        tracker, base = started
        _tick_idle(tracker, base, count=3)
        _tick_at(tracker, make_snapshot("pycharm64.exe", "models.py"), base + timedelta(seconds=45))
        for i in range(3):
            _tick_at(tracker, make_snapshot("pycharm64.exe", "models.py"), base + timedelta(seconds=60 + i * 15))
        session = _stop_at(tracker, base + timedelta(seconds=120))

        categories = [e.category for e in session.entries]
        assert "idle" in categories, "Expected an idle entry"
        assert "coding" in categories, "Expected a coding entry after idle"


class TestTrackerStatus:
    """Tests for SessionTracker.status property."""

    def test_status_before_start_returns_empty(self) -> None:
        tracker = SessionTracker()
        s = tracker.status
        assert s.category == "", f"Expected empty category, got {s.category!r}"
        assert s.entry_seconds == 0
        assert s.session_seconds == 0

    def test_status_after_start_before_tick_returns_zeros(self, started: tuple[SessionTracker, datetime]) -> None:
        tracker, _ = started
        s = tracker.status
        assert s.category == "", f"Expected empty category before first tick, got {s.category!r}"
        assert s.entry_seconds == 0
        assert s.session_seconds == 0

    def test_status_reflects_current_category(self, started: tuple[SessionTracker, datetime]) -> None:
        tracker, base = started
        _tick_at(tracker, make_snapshot("pycharm64.exe", "main.py - Bolt"), base)
        s = _status_at(tracker, base + timedelta(seconds=30))
        assert s.category == "coding", f"Expected 'coding', got {s.category!r}"

    def test_status_entry_seconds_grows_with_time(self, started: tuple[SessionTracker, datetime]) -> None:
        tracker, base = started
        _tick_at(tracker, make_snapshot("pycharm64.exe", "main.py - Bolt"), base)
        s = _status_at(tracker, base + timedelta(seconds=72))
        assert s.entry_seconds == 72, f"Expected 72, got {s.entry_seconds}"

    def test_status_session_seconds_includes_committed_plus_current(self, started: tuple[SessionTracker, datetime]) -> None:
        tracker, base = started
        _tick_coding(tracker, base)
        _tick_at(tracker, make_snapshot("chrome.exe", "Chrome"), base + timedelta(seconds=60))  # commits 60s coding
        s = _status_at(tracker, base + timedelta(seconds=90))
        assert s.session_seconds == 90, (
            f"Expected 90s (60 committed + 30 current), got {s.session_seconds}"
        )

    def test_status_session_seconds_excludes_idle(self, started: tuple[SessionTracker, datetime]) -> None:
        tracker, base = started
        _tick_coding(tracker, base)
        _tick_at(tracker, None, base + timedelta(seconds=60))  # commits 60s coding, starts idle
        s = _status_at(tracker, base + timedelta(seconds=90))
        assert s.category == "idle", f"Expected 'idle', got {s.category!r}"
        assert s.session_seconds == 60, (
            f"Expected 60s (idle excluded), got {s.session_seconds}"
        )

    def test_status_window_title_matches_current_window(self, started: tuple[SessionTracker, datetime]) -> None:
        tracker, base = started
        _tick_at(tracker, make_snapshot("pycharm64.exe", "session.py - Bolt"), base)
        s = _status_at(tracker, base + timedelta(seconds=5))
        assert s.window_title == "session.py - Bolt", (
            f"Expected 'session.py - Bolt', got {s.window_title!r}"
        )

    def test_status_idle_has_empty_window_title(self, started: tuple[SessionTracker, datetime]) -> None:
        tracker, base = started
        _tick_at(tracker, None, base)
        s = _status_at(tracker, base + timedelta(seconds=5))
        assert s.category == "idle"
        assert s.window_title == "", f"Expected empty title for idle, got {s.window_title!r}"
