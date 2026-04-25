"""Data structures shared across all layers. No I/O, no side effects."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class WindowSnapshot:
    """A single observation of the foreground window at a point in time."""

    timestamp: datetime
    process_name: str  # e.g. "pycharm64.exe"
    window_title: str  # e.g. "main.py - MyProject"


@dataclass
class TaskEntry:
    """A contiguous block of time spent in one category/window combination."""

    category: str       # e.g. "coding", "browsing", "idle"
    process_name: str
    window_title: str   # most representative title observed during this entry
    start_time: datetime
    end_time: datetime
    ai_description: str = ""  # filled by describer.py after session ends

    @property
    def duration_seconds(self) -> int:
        delta = self.end_time - self.start_time
        return max(0, int(delta.total_seconds()))

    @property
    def duration_minutes(self) -> int:
        return self.duration_seconds // 60


@dataclass
class Session:
    """A complete work session from start to stop."""

    session_id: str
    session_name: str
    start_time: datetime
    end_time: Optional[datetime]
    entries: list[TaskEntry] = field(default_factory=list)

    @classmethod
    def create(cls, session_name: str) -> "Session":
        """Create a new session with a generated UUID and current timestamp."""
        name = session_name or f"Session {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        return cls(
            session_id=str(uuid.uuid4()),
            session_name=name,
            start_time=datetime.now(),
            end_time=None,
            entries=[],
        )

    def duration_by_category(self) -> dict[str, int]:
        """Return total seconds per category, excluding 'idle'."""
        totals: dict[str, int] = {}
        for entry in self.entries:
            if entry.category == "idle":
                continue
            totals[entry.category] = totals.get(entry.category, 0) + entry.duration_seconds
        return totals

    @property
    def total_active_seconds(self) -> int:
        return sum(self.duration_by_category().values())
