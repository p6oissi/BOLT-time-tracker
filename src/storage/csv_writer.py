"""Write an enriched Session to a CSV file.

One file per session. Never overwrites an existing file.
Idle entries are excluded from the output.
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from tracker.models import Session

logger = logging.getLogger(__name__)

_COLUMNS = [
    "session_id",
    "session_name",
    "date",
    "start_time",
    "end_time",
    "duration_minutes",
    "category",
    "process_name",
    "window_title",
    "ai_description",
]


def write_session(session: Session, output_dir: Path) -> Path:
    """Write all non-idle entries of the session to a CSV file.

    Args:
        session: The completed, enriched session.
        output_dir: Directory to write the file into (created if absent).

    Returns:
        Path to the written CSV file.

    Raises:
        FileExistsError: If a file for this session already exists.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    date_str = session.start_time.strftime("%Y-%m-%d")
    filename = f"{session.session_id[:8]}_{date_str}.csv"
    output_path = output_dir / filename

    if output_path.exists():
        raise FileExistsError(f"Session file already exists: {output_path}")

    non_idle = [e for e in session.entries if e.category != "idle"]

    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_COLUMNS)
        writer.writeheader()
        for entry in non_idle:
            writer.writerow(
                {
                    "session_id": session.session_id,
                    "session_name": session.session_name,
                    "date": entry.start_time.strftime("%Y-%m-%d"),
                    "start_time": entry.start_time.strftime("%H:%M:%S"),
                    "end_time": entry.end_time.strftime("%H:%M:%S"),
                    "duration_minutes": entry.duration_minutes,
                    "category": entry.category,
                    "process_name": entry.process_name,
                    "window_title": entry.window_title,
                    "ai_description": entry.ai_description,
                }
            )

    logger.info("Session written to %s (%d entries)", output_path, len(non_idle))
    return output_path
