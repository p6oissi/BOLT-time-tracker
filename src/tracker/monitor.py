"""Windows active-window detection using win32 APIs.

This is the only module that imports win32. All errors are swallowed here
so callers never need to handle win32-specific exceptions.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import psutil

from tracker.models import WindowSnapshot

logger = logging.getLogger(__name__)

# win32 imports are optional so unit tests can run on any platform.
try:
    import win32gui
    import win32process

    _WIN32_AVAILABLE = True
except ImportError:  # pragma: no cover
    _WIN32_AVAILABLE = False


def get_active_window() -> Optional[WindowSnapshot]:
    """Return a snapshot of the current foreground window, or None on any error.

    Returns None when:
    - win32 is not available (non-Windows environment)
    - No foreground window exists
    - Process information cannot be read (access denied, process exited)
    """
    if not _WIN32_AVAILABLE:
        logger.debug("win32 not available — skipping window snapshot")
        return None

    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return None

        window_title: str = win32gui.GetWindowText(hwnd) or ""

        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        process = psutil.Process(pid)
        process_name: str = process.name()

        return WindowSnapshot(
            timestamp=datetime.now(),
            process_name=process_name,
            window_title=window_title,
        )
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        # Process exited or is protected — normal during window switches
        return None
    except Exception as exc:
        logger.warning("Unexpected error reading active window: %s", exc)
        return None
