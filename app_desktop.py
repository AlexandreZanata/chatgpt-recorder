#!/usr/bin/env python3
"""Linux Desktop Application Executable Launcher for Video Automation Studio."""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

if __name__ == "__main__":
    try:
        from src.ui.main_window import run_app
    except ImportError as err:
        print(f"Error loading desktop application: {err}", file=sys.stderr)
        sys.exit(1)
    run_app()
