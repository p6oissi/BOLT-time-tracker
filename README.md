# time-tracker

A local AI-powered work time tracker for developers. Runs entirely on your machine — no cloud, no external servers. It monitors your active Windows window in the background, classifies what you're working on using heuristic rules (coding, browsing, terminal, etc.), and at the end of your session uses a local LLM (Mistral via Ollama) to generate a human-readable description for each task. Output is a CSV report and a terminal summary table.

---

## How it works

```
start ──► poll active window (every N seconds)
             │
             ▼
         classify by process name + window title
         (coding / browsing / terminal / communication / ...)
             │
             ▼
         accumulate time per task entry
             │
         Ctrl+C
             │
             ▼
         call Mistral (Ollama) for each entry ──► fallback to window title if unavailable
             │
             ▼
         write CSV  +  print terminal summary
```

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Python 3.11+ | Tested on 3.12 |
| Windows | Uses win32 API for window detection |
| [Ollama](https://ollama.com) | For AI descriptions (optional — tracker works without it) |

---

## Setup (one-time)

```powershell
# From inside the time-tracker/ directory:
pip install -r requirements.txt

# Pull the Mistral model (only needed if you want AI descriptions):
ollama pull mistral
```

> **Note:** The tracker works fine without Ollama. If Ollama is not running, descriptions will show the raw window title instead of an AI-generated sentence.

---

## Running the tracker

All commands are run from inside the `time-tracker/` directory using `run.py`:

### Start a session

```powershell
python run.py start
```

With options:

```powershell
python run.py start --name "Sprint 3 - Auth" --interval 5
```

| Option | Default | Description |
|--------|---------|-------------|
| `--name` | auto-generated | Session name shown in the CSV and summary |
| `--interval` | `5` | How often (in seconds) to sample the active window |
| `--model` | `mistral` | Ollama model to use for AI descriptions |
| `--output` | `logs` | Directory to save the CSV file |

**Press `Ctrl+C` to stop tracking.** The session is saved and the summary prints automatically.

### Print a report from an existing CSV

```powershell
python run.py report logs\<filename>.csv
```

Replace `<filename>` with the actual filename created in `logs/` (e.g. `a1b2c3d4_2026-04-25.csv`).

---

## Running the tests

```powershell
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

Run with coverage:

```powershell
python -m pytest tests/ -v --cov=src
```

All 63 tests pass without Ollama or real win32 hardware.

---

## Example session output

```
[OK] Ollama is running — AI descriptions will use 'mistral'.
Tracking started: 'Sprint 3 - Auth' (interval: 5s). Press Ctrl+C to stop.

^C
Session stopped. Generating AI descriptions...

Session: Sprint 3 - Auth  |  2026-04-25  |  Total: 1h 42m

Category    Duration    %    AI Description (last entry)
----------  --------  ---  --------------------------------------------
coding      1h 05m    64%  Implementing OAuth2 data models in PyCharm
browsing    22m       21%  Reading Flask documentation in Chrome
terminal    15m       15%  Running pytest and reviewing test output

Report saved to: logs\a1b2c3d4_2026-04-25.csv
```

---

## CSV format

One file per session, saved as `<session_id[:8]>_<YYYY-MM-DD>.csv`:

| Column | Example |
|--------|---------|
| `session_id` | `a1b2c3d4-...` |
| `session_name` | `Sprint 3 - Auth` |
| `date` | `2026-04-25` |
| `start_time` | `09:15:00` |
| `end_time` | `09:47:00` |
| `duration_minutes` | `32` |
| `category` | `coding` |
| `process_name` | `pycharm64.exe` |
| `window_title` | `models.py - AuthService` |
| `ai_description` | `Implementing authentication data models in PyCharm` |

Idle periods (no active window) are excluded from the CSV.

---

## Project structure

```
time-tracker/
├── run.py              ← entry point (use this to run the tracker)
├── src/
│   ├── tracker/        ← domain logic: models, window monitor, classifier, session
│   ├── ai/             ← LLM enrichment via Ollama (post-session, fallback-safe)
│   ├── storage/        ← CSV persistence
│   └── cli/            ← click CLI (thin layer, no business logic)
├── tests/              ← 63 unit tests, one file per source module
└── logs/               ← CSV output (git-ignored)
```

---

## Limitations and next steps

- **Windows only** — `monitor.py` uses win32 APIs; Linux/Mac would need platform-specific backends
- **No keyboard/mouse idle detection** — idle is only recorded when there is no active foreground window; a future version could use `GetLastInputInfo()` for true idle detection
- **Heuristics only** — classification rules are good but not perfect; unknown apps fall back to "other"
- **No session aggregation** — each session is independent; a future version could produce weekly/monthly summaries
- **GitHub/Jira integration** — ticket numbers are already detectable in window titles; a future version could auto-link entries to issues
