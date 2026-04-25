# src/ai/ — LLM Layer Rules

## describer.py
- `enrich_session()` is called ONCE after the session ends, never during tracking.
- It MUST NOT raise: catch all Ollama errors, log a warning, fall back to `window_title` as `ai_description`.
- The prompt template is a module-level constant (deterministic, easy to test).
- Idle entries are skipped — do not send them to the LLM.
- Each entry is enriched independently (no batching complexity needed for prototype).

## Ollama dependency
- Uses the `ollama` SDK (`import ollama`), which calls `localhost:11434`.
- Default model is `"mistral"` but must be overridable via function argument.
- If Ollama is not installed or not running, the tracker still works — descriptions will equal the raw window title.
