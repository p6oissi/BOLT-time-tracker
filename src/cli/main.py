"""CLI entry point. Thin layer — all business logic lives in tracker/ai/storage."""

from __future__ import annotations

import csv
import logging
import sys
import time
from pathlib import Path

import click
from tabulate import tabulate

from ai.describer import enrich_session
from storage.csv_writer import write_session
from tracker.models import TaskEntry
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


def _print_summary(session_name: str, date_str: str, durations: dict[str, int], entries: list[TaskEntry]) -> None:
    total_seconds = sum(durations.values())
    click.echo()
    click.echo(f"Session: {session_name}  |  {date_str}  |  Total: {_format_duration(total_seconds)}")
    click.echo()

    # Build table rows: one row per category showing last AI description for that category
    last_desc: dict[str, str] = {}
    for entry in entries:
        if entry.category != "idle":
            last_desc[entry.category] = entry.ai_description or entry.window_title

    rows = []
    for category, seconds in sorted(durations.items(), key=lambda x: x[1], reverse=True):
        pct = int(seconds / total_seconds * 100) if total_seconds else 0
        rows.append([category, _format_duration(seconds), f"{pct}%", last_desc.get(category, "—")])

    headers = ["Category", "Duration", "%", "AI Description (last entry)"]
    click.echo(tabulate(rows, headers=headers, tablefmt="simple"))
    click.echo()


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
            time.sleep(interval)
    except KeyboardInterrupt:
        pass

    session = tracker.stop()
    click.echo("\nSession stopped. Generating AI descriptions...")
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

    total_seconds = sum(durations.values())
    click.echo()
    click.echo(f"Session: {session_name}  |  {date_str}  |  Total: {_format_duration(total_seconds)}")
    click.echo()

    table_rows = []
    for cat, seconds in sorted(durations.items(), key=lambda x: x[1], reverse=True):
        pct = int(seconds / total_seconds * 100) if total_seconds else 0
        table_rows.append([cat, _format_duration(seconds), f"{pct}%", last_desc.get(cat, "—")])

    headers = ["Category", "Duration", "%", "AI Description (last entry)"]
    click.echo(tabulate(table_rows, headers=headers, tablefmt="simple"))
    click.echo()


if __name__ == "__main__":
    cli()
