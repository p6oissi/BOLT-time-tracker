# src/storage/ — Persistence Layer Rules

## csv_writer.py
- Write-once per session: one CSV file per `session_id`.
- File name format: `<session_id[:8]>_<YYYY-MM-DD>.csv` inside the given `output_dir`.
- Raise `FileExistsError` if the file already exists — never silently overwrite.
- All datetimes written in ISO 8601 format (`YYYY-MM-DD` and `HH:MM:SS`).
- Duration is written in whole minutes (round down).
- `idle` entries are excluded from the CSV output.
- Column order: `session_id, session_name, date, start_time, end_time, duration_minutes, category, process_name, window_title, ai_description`
