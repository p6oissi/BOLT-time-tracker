# src/ — Module Conventions

## Data Flow
```
cli/main.py
  → creates SessionTracker (tracker/session.py)
  → loop: calls tracker.tick(monitor.get_active_window())
  → on stop: calls ai/describer.enrich_session(session)
  → calls storage/csv_writer.write_session(session, output_dir)
  → prints summary table
```

## Import Rules
- `tracker` modules may only import from `tracker.models`.
- `ai` modules may import from `tracker.models` only.
- `storage` modules may import from `tracker.models` only.
- `cli` may import from all other layers but contains no business logic.

## Conventions
- All `__init__.py` files are empty (no re-exports).
- No module-level side effects (no code that runs on import).
- Log using the standard `logging` module. Logger name = module `__name__`.
