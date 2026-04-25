"""Project entry point — run this directly instead of managing PYTHONPATH.

Usage:
    python run.py start --name "My Session"
    python run.py report logs/<file>.csv
"""

import sys
from pathlib import Path

# Add src/ to the path so 'tracker', 'ai', 'storage', 'cli' are importable.
sys.path.insert(0, str(Path(__file__).parent / "src"))

from cli.main import cli

if __name__ == "__main__":
    cli()
