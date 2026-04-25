"""Tests for CLI rendering helpers in cli/main.py."""

from __future__ import annotations

from io import StringIO
from unittest.mock import patch

from cli.main import _format_duration, _format_duration_hms, _render_status_line
from tracker.models import TrackerStatus


def make_status(
    category: str = "coding",
    window_title: str = "main.py - Bolt",
    entry_seconds: int = 72,
    session_seconds: int = 272,
) -> TrackerStatus:
    return TrackerStatus(
        category=category,
        window_title=window_title,
        entry_seconds=entry_seconds,
        session_seconds=session_seconds,
    )


def capture(status: TrackerStatus, max_title_len: int = 50) -> str:
    buf = StringIO()
    with patch("sys.stdout", buf):
        _render_status_line(status, max_title_len=max_title_len)
    return buf.getvalue()


class TestFormatDuration:
    def test_zero_seconds(self) -> None:
        assert _format_duration(0) == "0m"

    def test_under_one_hour(self) -> None:
        assert _format_duration(272) == "4m"

    def test_exactly_one_hour(self) -> None:
        assert _format_duration(3600) == "1h 00m"

    def test_one_hour_thirty_two_minutes(self) -> None:
        assert _format_duration(5520) == "1h 32m"


class TestFormatDurationHms:
    def test_zero_seconds(self) -> None:
        assert _format_duration_hms(0) == "0s"

    def test_seconds_only(self) -> None:
        assert _format_duration_hms(45) == "45s"

    def test_minutes_and_seconds(self) -> None:
        assert _format_duration_hms(72) == "1m 12s"

    def test_hours_minutes_seconds(self) -> None:
        assert _format_duration_hms(3672) == "1h 01m 12s"

    def test_exact_minute(self) -> None:
        assert _format_duration_hms(60) == "1m 00s"


class TestRenderStatusLine:
    def test_normal_line_contains_category(self) -> None:
        out = capture(make_status(category="coding"))
        assert "[coding]" in out, f"Expected '[coding]' in {out!r}"

    def test_normal_line_contains_window_title(self) -> None:
        out = capture(make_status(window_title="session.py - Bolt"))
        assert "session.py - Bolt" in out

    def test_normal_line_contains_entry_duration(self) -> None:
        out = capture(make_status(entry_seconds=72))  # 1m 12s
        assert "entry: 1m 12s" in out, f"Expected 'entry: 1m 12s' in {out!r}"

    def test_normal_line_contains_session_duration(self) -> None:
        out = capture(make_status(session_seconds=272))  # 4m 32s
        assert "session: 4m 32s" in out, f"Expected 'session: 4m 32s' in {out!r}"

    def test_line_starts_with_carriage_return(self) -> None:
        out = capture(make_status())
        assert out.startswith("\r"), f"Expected \\r prefix, got {out[:5]!r}"

    def test_line_contains_ansi_erase_escape(self) -> None:
        out = capture(make_status())
        assert "\x1b[K" in out, "Expected ANSI EL escape \\x1b[K in output"

    def test_idle_shows_idle_label(self) -> None:
        out = capture(make_status(category="idle", window_title=""))
        assert "[idle]" in out, f"Expected '[idle]' in {out!r}"

    def test_idle_omits_entry_label(self) -> None:
        out = capture(make_status(category="idle", window_title=""))
        assert "idle:" in out and "entry:" not in out, (
            f"Idle line must not have 'entry:' label, got {out!r}"
        )

    def test_empty_category_shows_waiting(self) -> None:
        out = capture(make_status(category="", window_title="", entry_seconds=0, session_seconds=0))
        assert "Waiting" in out, f"Expected 'Waiting' in {out!r}"

    def test_long_title_is_truncated_with_ellipsis(self) -> None:
        long_title = "A" * 100
        out = capture(make_status(window_title=long_title), max_title_len=20)
        assert "A" * 100 not in out, "Long title must be truncated"
        assert "…" in out, "Truncated title must end with ellipsis"
        assert "A" * 19 + "…" in out, "Exactly 19 chars + ellipsis expected"

    def test_terminal_width_truncation(self) -> None:
        status = make_status(window_title="some title", entry_seconds=60, session_seconds=120)
        mock_size = type("T", (), {"columns": 30})()
        buf = StringIO()
        with patch("shutil.get_terminal_size", return_value=mock_size):
            with patch("sys.stdout", buf):
                _render_status_line(status)
        content = buf.getvalue().replace("\r", "").replace("\x1b[K", "")
        assert len(content) <= 30, f"Expected <= 30 chars, got {len(content)}: {content!r}"

    def test_empty_window_title_on_non_idle_renders_without_crash(self) -> None:
        out = capture(make_status(category="other", window_title=""))
        assert "[other]" in out

    def test_zero_entry_seconds_renders_zero(self) -> None:
        out = capture(make_status(entry_seconds=0))
        assert "entry: 0s" in out, f"Expected 'entry: 0s', got {out!r}"
