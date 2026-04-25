# src/cli/ — CLI Layer Rules

## main.py
- Thin layer: delegate ALL logic to tracker/ai/storage modules. No business logic here.
- Use `click` for all CLI parsing.
- Exit codes: 0 = success, 1 = user/config error, 2 = unexpected system error.
- On startup, print Ollama availability status so the user knows whether AI descriptions will work.
- On KeyboardInterrupt (Ctrl+C), finish gracefully: stop session, enrich, write CSV, print summary.
- Do not catch KeyboardInterrupt silently — re-raise after cleanup so the shell gets exit code 130.

## Commands
| Command | Purpose |
|---------|---------|
| `tracker start` | Start a new tracking session (blocking, Ctrl+C to stop) |
| `tracker report <file>` | Print a summary table from an existing CSV |
