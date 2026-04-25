# time-tracker — Project Rules

## Purpose
Local AI-powered work time tracker. Monitors the active Windows window, classifies tasks by heuristic rules, and at session end uses a local LLM (Mistral via Ollama) to generate human-readable descriptions. Output is a CSV report + terminal summary.

## Architecture (4 layers, strict dependency direction)
```
cli  →  tracker (monitor + classifier + session)
     →  ai (describer)
     →  storage (csv_writer)
```
- `cli` is the only entry point; it calls into the other layers.
- `tracker` has zero I/O — pure domain logic and data structures.
- `ai` calls Ollama post-session only; never during the tracking loop.
- `storage` writes files; no business logic.
- No layer imports from a layer above it (no circular deps).

## Coding Standards
- Type-annotate ALL public functions and methods.
- One function = one responsibility (SRP).
- No global mutable state.
- Never let a transient error (Ollama down, window closed) crash the program — log a warning and continue.
- Do not duplicate logic across modules (DRY): time arithmetic lives in `models.py`, classification lives in `classifier.py`.
- Keep it simple: no abstract base classes or design patterns unless they reduce real duplication (KISS).

## Testing
- Unit tests must not call win32 APIs or real Ollama. Use plain `WindowSnapshot` fixtures.
- One test file per source module.
- Test the unhappy path (Ollama unavailable, None window snapshot) as well as the happy path.

## Key Files
| File | Responsibility |
|------|---------------|
| `src/tracker/models.py` | All data structures |
| `src/tracker/classifier.py` | Heuristic category rules |
| `src/tracker/monitor.py` | Windows active-window detection |
| `src/tracker/session.py` | Session orchestration |
| `src/ai/describer.py` | LLM task description enrichment |
| `src/storage/csv_writer.py` | CSV persistence |
| `src/cli/main.py` | CLI entry point |
