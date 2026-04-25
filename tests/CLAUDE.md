# tests/ — Testing Conventions

## Rules
- One test file per source module (test_classifier, test_session, test_describer, test_csv_writer).
- Unit tests MUST NOT call real win32 APIs or real Ollama.
  - Build `WindowSnapshot` fixtures directly (they are plain dataclasses — no mocking needed).
  - Mock `ollama.chat` using `unittest.mock.patch` in test_describer.py.
- Test BOTH the happy path AND the error/fallback path.
- Use `conftest.py` for shared fixtures (e.g., a sample Session with known entries).
- Tests should be fast (<1s total): no sleep, no file I/O to real disk (use `tmp_path` fixture).
- Assertion messages should say what was expected, e.g.: `assert result == "coding", f"Expected 'coding', got {result!r}"`.
