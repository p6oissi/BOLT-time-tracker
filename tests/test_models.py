"""Tests for data model properties and methods."""

from datetime import datetime, timedelta

from tracker.models import Session, TaskEntry


def make_entry(category: str, duration_s: int, offset_s: int = 0) -> TaskEntry:
    base = datetime(2026, 4, 25, 9, 0, 0)
    return TaskEntry(
        category=category,
        process_name="test.exe",
        window_title=f"window-{category}",
        start_time=base + timedelta(seconds=offset_s),
        end_time=base + timedelta(seconds=offset_s + duration_s),
    )


class TestTaskEntryDuration:
    def test_duration_seconds_correct(self) -> None:
        entry = make_entry("coding", duration_s=3600)
        assert entry.duration_seconds == 3600

    def test_duration_minutes_floors_to_whole_minutes(self) -> None:
        entry = make_entry("coding", duration_s=3750)  # 62.5 minutes
        assert entry.duration_minutes == 62

    def test_duration_seconds_never_negative(self) -> None:
        # End before start should clamp to 0, not go negative
        base = datetime(2026, 4, 25, 9, 0, 0)
        entry = TaskEntry(
            category="coding",
            process_name="test.exe",
            window_title="test",
            start_time=base + timedelta(seconds=10),
            end_time=base,  # end before start
        )
        assert entry.duration_seconds == 0

    def test_duration_zero_for_same_start_end(self) -> None:
        base = datetime(2026, 4, 25, 9, 0, 0)
        entry = TaskEntry(
            category="coding",
            process_name="test.exe",
            window_title="test",
            start_time=base,
            end_time=base,
        )
        assert entry.duration_seconds == 0
        assert entry.duration_minutes == 0


class TestSessionDurationByCategory:
    def test_sums_seconds_per_category(self) -> None:
        session = Session(
            session_id="test",
            session_name="test",
            start_time=datetime(2026, 4, 25, 9, 0, 0),
            end_time=None,
            entries=[
                make_entry("coding", 1800),   # 30 min
                make_entry("coding", 600),    # 10 min — same category, should add up
                make_entry("browsing", 900),  # 15 min
            ],
        )
        result = session.duration_by_category()
        assert result["coding"] == 2400, f"Expected 2400s coding, got {result['coding']}"
        assert result["browsing"] == 900, f"Expected 900s browsing, got {result['browsing']}"

    def test_excludes_idle_entries(self) -> None:
        session = Session(
            session_id="test",
            session_name="test",
            start_time=datetime(2026, 4, 25, 9, 0, 0),
            end_time=None,
            entries=[
                make_entry("coding", 600),
                make_entry("idle", 300),
            ],
        )
        result = session.duration_by_category()
        assert "idle" not in result, "Idle must not appear in duration_by_category()"
        assert "coding" in result

    def test_empty_session_returns_empty_dict(self) -> None:
        session = Session(
            session_id="test",
            session_name="test",
            start_time=datetime(2026, 4, 25, 9, 0, 0),
            end_time=None,
            entries=[],
        )
        assert session.duration_by_category() == {}

    def test_only_idle_entries_returns_empty_dict(self) -> None:
        session = Session(
            session_id="test",
            session_name="test",
            start_time=datetime(2026, 4, 25, 9, 0, 0),
            end_time=None,
            entries=[make_entry("idle", 300)],
        )
        assert session.duration_by_category() == {}


class TestSessionTotalActiveSeconds:
    def test_total_excludes_idle(self) -> None:
        session = Session(
            session_id="test",
            session_name="test",
            start_time=datetime(2026, 4, 25, 9, 0, 0),
            end_time=None,
            entries=[
                make_entry("coding", 600),
                make_entry("browsing", 300),
                make_entry("idle", 9999),  # should not count
            ],
        )
        assert session.total_active_seconds == 900

    def test_total_zero_when_no_entries(self) -> None:
        session = Session(
            session_id="test",
            session_name="test",
            start_time=datetime(2026, 4, 25, 9, 0, 0),
            end_time=None,
        )
        assert session.total_active_seconds == 0


class TestSessionCreate:
    def test_creates_unique_ids(self) -> None:
        s1 = Session.create("A")
        s2 = Session.create("B")
        assert s1.session_id != s2.session_id

    def test_auto_generates_name(self) -> None:
        s = Session.create("")
        assert s.session_name.startswith("Session ")

    def test_uses_provided_name(self) -> None:
        s = Session.create("Sprint 3")
        assert s.session_name == "Sprint 3"

    def test_end_time_is_none_on_creation(self) -> None:
        s = Session.create("test")
        assert s.end_time is None
