"""Tests for LLM describer: prompt construction and fallback behavior."""

from datetime import datetime, timedelta
from unittest.mock import patch

from ai.describer import build_prompt, enrich_session
from tracker.models import TaskEntry, Session


def make_entry(category: str = "coding", process: str = "pycharm64.exe", title: str = "main.py - Project", duration_s: int = 300) -> TaskEntry:
    start = datetime(2026, 4, 25, 9, 0, 0)
    return TaskEntry(
        category=category,
        process_name=process,
        window_title=title,
        start_time=start,
        end_time=start + timedelta(seconds=duration_s),
    )


def make_session(*entries: TaskEntry) -> Session:
    return Session(
        session_id="test-id",
        session_name="Test Session",
        start_time=datetime(2026, 4, 25, 9, 0, 0),
        end_time=datetime(2026, 4, 25, 10, 0, 0),
        entries=list(entries),
    )


class TestBuildPrompt:
    def test_prompt_contains_all_fields(self) -> None:
        entry = make_entry(category="coding", process="pycharm64.exe", title="models.py - AuthService", duration_s=1920)
        prompt = build_prompt(entry)
        assert "coding" in prompt
        assert "pycharm64.exe" in prompt
        assert "models.py - AuthService" in prompt
        assert "32 minutes" in prompt  # 1920s = 32min

    def test_prompt_is_deterministic(self) -> None:
        entry = make_entry()
        assert build_prompt(entry) == build_prompt(entry)


class TestEnrichSession:
    def test_happy_path_sets_ai_description(self) -> None:
        """When Ollama responds, ai_description should be set from the response."""
        entry = make_entry()
        session = make_session(entry)

        mock_response = {"message": {"content": "Implementing data models in PyCharm."}}
        with patch("ai.describer.ollama") as mock_ollama:
            mock_ollama.chat.return_value = mock_response
            result = enrich_session(session, model="mistral")

        assert result.entries[0].ai_description == "Implementing data models in PyCharm."

    def test_fallback_when_ollama_raises(self) -> None:
        """When Ollama raises any exception, ai_description falls back to window_title."""
        entry = make_entry(title="main.py - MyProject")
        session = make_session(entry)

        with patch("ai.describer.ollama") as mock_ollama:
            mock_ollama.chat.side_effect = ConnectionRefusedError("Ollama not running")
            result = enrich_session(session, model="mistral")

        assert result.entries[0].ai_description == "main.py - MyProject", (
            "Fallback must be window_title when Ollama is unavailable"
        )

    def test_idle_entries_are_skipped(self) -> None:
        """Idle entries must never be sent to the LLM."""
        idle_entry = make_entry(category="idle")
        coding_entry = make_entry(category="coding")
        session = make_session(idle_entry, coding_entry)

        mock_response = {"message": {"content": "Writing Python code."}}
        with patch("ai.describer.ollama") as mock_ollama:
            mock_ollama.chat.return_value = mock_response
            enrich_session(session, model="mistral")

        # chat should have been called exactly once (for coding_entry only)
        assert mock_ollama.chat.call_count == 1, "Ollama must not be called for idle entries"
        assert idle_entry.ai_description == "", "Idle entry ai_description must remain empty"

    def test_empty_response_falls_back_to_window_title(self) -> None:
        """An empty string response from Ollama should fall back to window_title."""
        entry = make_entry(title="reports.py - DataPipeline")
        session = make_session(entry)

        with patch("ai.describer.ollama") as mock_ollama:
            mock_ollama.chat.return_value = {"message": {"content": "  "}}
            result = enrich_session(session, model="mistral")

        assert result.entries[0].ai_description == "reports.py - DataPipeline"

    def test_enrich_session_does_not_raise(self) -> None:
        """enrich_session must not propagate any exception from Ollama."""
        entry = make_entry()
        session = make_session(entry)

        with patch("ai.describer.ollama") as mock_ollama:
            mock_ollama.chat.side_effect = RuntimeError("unexpected crash")
            # Should complete without raising
            enrich_session(session, model="mistral")
