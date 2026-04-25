"""CLI entry point. Thin layer — all business logic lives in tracker/ai/storage."""

from __future__ import annotations

import csv
import logging
import shutil
import sys
import time
from pathlib import Path

import click
from tabulate import tabulate

from ai.describer import enrich_session
from storage.csv_writer import write_session
from tracker.models import TaskEntry, TrackerStatus
from tracker.monitor import get_active_window
from tracker.session import SessionTracker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
# Suppress HTTP-level chatter from the Ollama SDK's transport layer.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def _check_ollama(model: str) -> bool:
    """Return True if Ollama is reachable and the model is available."""
    try:
        import ollama

        ollama.show(model)
        return True
    except Exception:
        return False


def _format_duration(total_seconds: int) -> str:
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    if h:
        return f"{h}h {m:02d}m"
    return f"{m}m"


def _format_duration_hms(total_seconds: int) -> str:
    """Format seconds as '1m 12s' (seconds-precision) for the live status line."""
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    if h:
        return f"{h}h {m:02d}m {s:02d}s"
    if m:
        return f"{m}m {s:02d}s"
    return f"{s}s"


def _render_status_line(status: TrackerStatus, max_title_len: int = 50) -> None:
    """Overwrite the current terminal line with live tracking status.

    Uses \\r (carriage return) to rewrite in place; \\x1b[K clears leftover
    characters when a shorter line follows a longer one.
    """
    if not status.category:
        line = "Waiting for first window..."
    elif status.category == "idle":
        line = (
            f"[idle]  |  idle: {_format_duration_hms(status.entry_seconds)}"
            f"  |  session: {_format_duration_hms(status.session_seconds)}"
        )
    else:
        title = status.window_title
        if len(title) > max_title_len:
            title = title[: max_title_len - 1] + "…"
        line = (
            f"[{status.category}]  {title}"
            f"  |  entry: {_format_duration_hms(status.entry_seconds)}"
            f"  |  session: {_format_duration_hms(status.session_seconds)}"
        )

    term_width = shutil.get_terminal_size(fallback=(80, 24)).columns
    if len(line) > term_width:
        line = line[: term_width - 1] + "…"

    sys.stdout.write(f"\r{line}\x1b[K")
    sys.stdout.flush()


def _render_table(session_name: str, date_str: str, durations: dict[str, int], last_desc: dict[str, str]) -> None:
    """Print the formatted summary table. Shared by both `start` and `report` commands."""
    total_seconds = sum(durations.values())
    click.echo()
    click.echo(f"Session: {session_name}  |  {date_str}  |  Total: {_format_duration(total_seconds)}")
    click.echo()

    rows = []
    for category, seconds in sorted(durations.items(), key=lambda x: x[1], reverse=True):
        pct = int(seconds / total_seconds * 100) if total_seconds else 0
        rows.append([category, _format_duration(seconds), f"{pct}%", last_desc.get(category, "—")])

    headers = ["Category", "Duration", "%", "AI Description (last entry)"]
    click.echo(tabulate(rows, headers=headers, tablefmt="simple"))
    click.echo()


def _print_summary(session_name: str, date_str: str, durations: dict[str, int], entries: list[TaskEntry]) -> None:
    last_desc: dict[str, str] = {
        e.category: e.ai_description or e.window_title
        for e in entries
        if e.category != "idle"
    }
    _render_table(session_name, date_str, durations, last_desc)


@click.group()
def cli() -> None:
    """AI-powered local work time tracker."""


@cli.command()
@click.option("--name", default="", help="Session name (auto-generated if omitted).")
@click.option("--interval", default=5, show_default=True, type=int, help="Polling interval in seconds.")
@click.option("--model", default="mistral", show_default=True, help="Ollama model for AI descriptions.")
@click.option("--output", default="logs", show_default=True, help="Directory to save the CSV report.")
def start(name: str, interval: int, model: str, output: str) -> None:
    """Start a tracking session. Press Ctrl+C to stop and save."""
    ollama_ok = _check_ollama(model)
    if ollama_ok:
        click.echo(f"[OK] Ollama is running — AI descriptions will use '{model}'.")
    else:
        click.echo(f"[WARN] Ollama not available — descriptions will use raw window titles.")

    tracker = SessionTracker()
    session = tracker.start(name)
    click.echo(f"Tracking started: '{session.session_name}' (interval: {interval}s). Press Ctrl+C to stop.\n")

    try:
        while True:
            snapshot = get_active_window()
            tracker.tick(snapshot)
            _render_status_line(tracker.status)
            time.sleep(interval)
    except KeyboardInterrupt:
        sys.stdout.write("\n")
        sys.stdout.flush()

    session = tracker.stop()
    click.echo("Session stopped. Generating AI descriptions...")
    session = enrich_session(session, model=model)

    output_dir = Path(output)
    try:
        csv_path = write_session(session, output_dir)
    except FileExistsError as exc:
        click.echo(f"[ERROR] {exc}", err=True)
        sys.exit(1)

    _print_summary(
        session.session_name,
        session.start_time.strftime("%Y-%m-%d"),
        session.duration_by_category(),
        session.entries,
    )
    click.echo(f"Report saved to: {csv_path}")


@cli.command()
@click.argument("csv_file", type=click.Path(exists=True, dir_okay=False))
def report(csv_file: str) -> None:
    """Print a summary table from an existing CSV session report."""
    path = Path(csv_file)
    rows: list[dict[str, str]] = []
    with path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    if not rows:
        click.echo("No entries found in the file.")
        sys.exit(0)

    session_name = rows[0].get("session_name", "Unknown")
    date_str = rows[0].get("date", "")

    # Aggregate durations
    durations: dict[str, int] = {}
    last_desc: dict[str, str] = {}
    for row in rows:
        cat = row.get("category", "other")
        minutes = int(row.get("duration_minutes", 0))
        durations[cat] = durations.get(cat, 0) + minutes * 60
        last_desc[cat] = row.get("ai_description", row.get("window_title", ""))

    _render_table(session_name, date_str, durations, last_desc)


if __name__ == "__main__":
    cli()
