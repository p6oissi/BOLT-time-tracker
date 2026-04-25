# src/tracker/ — Domain Logic Rules

## classifier.py
- `classify()` is a pure function: same input always returns same output.
- No I/O, no logging, no side effects.
- Rules are a single list of `(keywords, category)` tuples — easy to extend without touching other code (Open/Closed).
- Matching is case-insensitive on both process_name and window_title.

## monitor.py
- `get_active_window()` MUST return `None` on any error — never raise.
- Errors to handle: no foreground window, process access denied, window destroyed between calls.
- Keep win32 API calls isolated here; no other module imports win32.

## session.py
- `SessionTracker` owns ALL time arithmetic. No other module computes durations.
- `tick()` merges consecutive snapshots with the same (category, window_title) into a single `TaskEntry`.
- An entry is only committed when a different window/category is detected (or `stop()` is called).
- Idle snapshots (same snapshot for >60s) are recorded as category `"idle"` but excluded from the CSV.

## models.py
- Pure dataclasses: no methods with side effects, no I/O.
- `duration_seconds` is a `@property` on `TaskEntry`.
- `Session.duration_by_category()` returns `dict[str, int]` (category → total seconds), excluding `"idle"`.
