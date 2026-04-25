"""Session orchestration: owns all time arithmetic and entry merging logic."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from tracker.classifier import classify
from tracker.models import Session, TaskEntry, WindowSnapshot

logger = logging.getLogger(__name__)

# A window must be observed for at least this many seconds before it counts.
# Prevents single-tick noise from rapid alt-tabbing.
_MIN_ENTRY_SECONDS = 10


class SessionTracker:
    """Tracks a single work session by processing window snapshots over time."""

    def __init__(self) -> None:
        self._session: Optional[Session] = None
        # The entry currently being built (not yet committed to session.entries)
        self._current_category: Optional[str] = None
        self._current_process: str = ""
        self._current_title: str = ""
        self._current_start: Optional[datetime] = None
        self._last_snapshot: Optional[WindowSnapshot] = None

    def start(self, session_name: str = "") -> Session:
        """Begin a new session and return it."""
        self._session = Session.create(session_name)
        self._reset_current()
        logger.info("Session started: %s (%s)", self._session.session_name, self._session.session_id)
        return self._session

    def tick(self, snapshot: Optional[WindowSnapshot]) -> None:
        """Process one window observation. Call this on every poll interval."""
        if self._session is None:
            raise RuntimeError("Call start() before tick()")

        now = datetime.now()

        if snapshot is None:
            # No foreground window — transition to idle only once, not on every tick.
            # The idle entry grows until a real window returns.
            if self._current_category != "idle":
                self._handle_category_change("idle", "", "", now)
            return

        category = classify(snapshot.process_name, snapshot.window_title)

        if category != self._current_category:
            self._handle_category_change(category, snapshot.process_name, snapshot.window_title, now)

        self._last_snapshot = snapshot

    def stop(self) -> Session:
        """Finalize and return the completed session."""
        if self._session is None:
            raise RuntimeError("Call start() before stop()")
        now = datetime.now()
        self._commit_current(now)
        self._session.end_time = now
        logger.info("Session stopped. Entries: %d", len(self._session.entries))
        return self._session

    # --- private helpers ---

    def _handle_category_change(
        self, new_category: str, process_name: str, window_title: str, now: datetime
    ) -> None:
        """Commit the in-progress entry and start a new one."""
        self._commit_current(now)
        self._current_category = new_category
        self._current_process = process_name
        self._current_title = window_title
        self._current_start = now

    def _commit_current(self, end_time: datetime) -> None:
        """Write the current in-progress entry to the session if it's long enough."""
        if (
            self._session is None
            or self._current_category is None
            or self._current_start is None
        ):
            return

        duration = (end_time - self._current_start).total_seconds()
        if duration < _MIN_ENTRY_SECONDS:
            return  # Too short — ignore noise

        entry = TaskEntry(
            category=self._current_category,
            process_name=self._current_process,
            window_title=self._current_title,
            start_time=self._current_start,
            end_time=end_time,
        )
        self._session.entries.append(entry)
        logger.debug("Committed entry: %s | %s | %.0fs", entry.category, entry.window_title, duration)

    def _reset_current(self) -> None:
        self._current_category = None
        self._current_process = ""
        self._current_title = ""
        self._current_start = None
        self._last_snapshot = None
