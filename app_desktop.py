#!/usr/bin/env python3
"""Linux Desktop Application Executable Launcher for Video Automation Studio."""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from src.ui.main_window import run_app
except ImportError:
    print("PySide6 is required to run the Linux Desktop Application.")
    print("Install via: pip install PySide6")
    sys.exit(1)

if __name__ == "__main__":
    run_app()
