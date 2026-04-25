"""Shared fixtures for the test suite."""

from datetime import datetime, timedelta

import pytest

from tracker.models import TaskEntry, Session


@pytest.fixture
def sample_session() -> Session:
    """A realistic session with coding, browsing, and idle entries."""
    base = datetime(2026, 4, 25, 9, 0, 0)
    return Session(
        session_id="fixture-id-0000",
        session_name="Fixture Session",
        start_time=base,
        end_time=base + timedelta(hours=2),
        entries=[
            TaskEntry(
                category="coding",
                process_name="pycharm64.exe",
                window_title="models.py - MyProject",
                start_time=base,
                end_time=base + timedelta(minutes=50),
                ai_description="Building data models in PyCharm.",
            ),
            TaskEntry(
                category="browsing",
                process_name="chrome.exe",
                window_title="Stack Overflow - Google Chrome",
                start_time=base + timedelta(minutes=50),
                end_time=base + timedelta(minutes=70),
                ai_description="Researching Python dataclass patterns.",
            ),
            TaskEntry(
                category="idle",
                process_name="",
                window_title="",
                start_time=base + timedelta(minutes=70),
                end_time=base + timedelta(minutes=80),
            ),
            TaskEntry(
                category="terminal",
                process_name="WindowsTerminal.exe",
                window_title="PowerShell",
                start_time=base + timedelta(minutes=80),
                end_time=base + timedelta(minutes=100),
                ai_description="Running pytest test suite.",
            ),
        ],
    )
