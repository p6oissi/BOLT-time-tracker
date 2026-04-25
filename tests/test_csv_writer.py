"""Tests for CSV persistence layer."""

import csv
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from storage.csv_writer import write_session, _COLUMNS
from tracker.models import TaskEntry, Session


def make_entry(category: str, title: str, offset_start: int = 0, duration_s: int = 600) -> TaskEntry:
    base = datetime(2026, 4, 25, 9, 0, 0)
    entry = TaskEntry(
        category=category,
        process_name="test.exe",
        window_title=title,
        start_time=base + timedelta(seconds=offset_start),
        end_time=base + timedelta(seconds=offset_start + duration_s),
        ai_description="AI description for " + title,
    )
    return entry


def make_session(entries: list[TaskEntry]) -> Session:
    return Session(
        session_id="abcdef12-0000-0000-0000-000000000000",
        session_name="Test Session",
        start_time=datetime(2026, 4, 25, 9, 0, 0),
        end_time=datetime(2026, 4, 25, 10, 0, 0),
        entries=entries,
    )


class TestWriteSession:
    def test_creates_file_in_output_dir(self, tmp_path: Path) -> None:
        session = make_session([make_entry("coding", "main.py")])
        result = write_session(session, tmp_path)
        assert result.exists(), "CSV file was not created"

    def test_filename_format(self, tmp_path: Path) -> None:
        session = make_session([make_entry("coding", "main.py")])
        result = write_session(session, tmp_path)
        # filename should be <first 8 chars of session_id>_<date>.csv
        assert result.name == "abcdef12_2026-04-25.csv"

    def test_correct_headers(self, tmp_path: Path) -> None:
        session = make_session([make_entry("coding", "main.py")])
        result = write_session(session, tmp_path)
        with result.open(encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            assert reader.fieldnames == _COLUMNS, f"Headers mismatch: {reader.fieldnames}"

    def test_row_count_excludes_idle(self, tmp_path: Path) -> None:
        entries = [
            make_entry("coding", "main.py", offset_start=0),
            make_entry("idle", "idle", offset_start=600),
            make_entry("browsing", "Chrome", offset_start=1200),
        ]
        session = make_session(entries)
        result = write_session(session, tmp_path)
        with result.open(encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        assert len(rows) == 2, f"Expected 2 non-idle rows, got {len(rows)}"

    def test_duration_minutes_correct(self, tmp_path: Path) -> None:
        entry = make_entry("coding", "main.py", duration_s=1920)  # 32 minutes
        session = make_session([entry])
        result = write_session(session, tmp_path)
        with result.open(encoding="utf-8") as fh:
            row = next(csv.DictReader(fh))
        assert row["duration_minutes"] == "32", f"Expected 32, got {row['duration_minutes']}"

    def test_ai_description_written(self, tmp_path: Path) -> None:
        entry = make_entry("coding", "auth.py")
        entry.ai_description = "Implementing OAuth2 authentication flow."
        session = make_session([entry])
        result = write_session(session, tmp_path)
        with result.open(encoding="utf-8") as fh:
            row = next(csv.DictReader(fh))
        assert row["ai_description"] == "Implementing OAuth2 authentication flow."

    def test_raises_if_file_exists(self, tmp_path: Path) -> None:
        session = make_session([make_entry("coding", "main.py")])
        write_session(session, tmp_path)
        with pytest.raises(FileExistsError):
            write_session(session, tmp_path)

    def test_creates_output_dir_if_missing(self, tmp_path: Path) -> None:
        nested = tmp_path / "a" / "b" / "logs"
        session = make_session([make_entry("coding", "main.py")])
        result = write_session(session, nested)
        assert result.exists()
