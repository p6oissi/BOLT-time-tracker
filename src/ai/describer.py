"""Post-session LLM enrichment via Ollama.

Generates a concise human-readable description for each task entry.
Falls back to the raw window title if Ollama is unavailable — tracking
data is never lost due to LLM errors.
"""

from __future__ import annotations

import logging
from typing import Any

from tracker.models import Session, TaskEntry

logger = logging.getLogger(__name__)

# Module-level import makes `ollama` patchable in tests.
# If Ollama is not installed the module still loads; _describe_entry falls back gracefully.
try:
    import ollama
except ImportError:
    ollama = None  # type: ignore[assignment]

# Prompt template is a module-level constant so tests can assert against it.
_PROMPT_TEMPLATE = """\
You are a work-logger assistant. Given the context below about what a developer was doing, \
write a concise 1-sentence description (maximum 15 words) of the work activity. \
Reply with only the description sentence, no extra text.

Category: {category}
Application: {process_name}
Window title: {window_title}
Duration: {duration_minutes} minutes

Description:"""


def build_prompt(entry: TaskEntry) -> str:
    """Return the formatted prompt for a single task entry."""
    return _PROMPT_TEMPLATE.format(
        category=entry.category,
        process_name=entry.process_name,
        window_title=entry.window_title,
        duration_minutes=entry.duration_minutes,
    )


def _describe_entry(entry: TaskEntry, model: str) -> str:
    """Call Ollama and return the generated description, or window_title on failure."""
    if ollama is None:
        logger.warning("ollama package not installed — using window title as fallback")
        return entry.window_title
    try:
        response: Any = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": build_prompt(entry)}],
        )
        text: str = response["message"]["content"].strip()
        return text if text else entry.window_title
    except Exception as exc:
        logger.warning("Ollama unavailable for entry '%s': %s — using window title as fallback", entry.window_title, exc)
        return entry.window_title


def enrich_session(session: Session, model: str = "mistral") -> Session:
    """Generate AI descriptions for all non-idle entries in the session.

    Mutates each TaskEntry.ai_description in place and returns the session.
    This function must not raise — all Ollama errors are handled per-entry.
    """
    non_idle = [e for e in session.entries if e.category != "idle"]
    logger.info("Generating AI descriptions for %d entries (model: %s)...", len(non_idle), model)

    for i, entry in enumerate(non_idle, start=1):
        logger.info("  [%d/%d] %s — %s", i, len(non_idle), entry.category, entry.window_title)
        entry.ai_description = _describe_entry(entry, model)

    return session
