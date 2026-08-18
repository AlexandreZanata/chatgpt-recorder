"""Batch generator for Fooocus / SDXL local checkpoints with zero cloud dependencies."""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
import urllib.request


FOOOCUS_API_URL = "http://127.0.0.1:7865/api/predict"


def check_fooocus_running(url: str = "http://127.0.0.1:7865") -> bool:
    """Check if the local Fooocus AI engine is running."""
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=1.5):
            return True
    except Exception:
        return False


def get_available_checkpoints(models_dir: Optional[str] = None) -> List[str]:
    """Scan and list all available SDXL checkpoint files."""
    if not models_dir:
        home = Path.home()
        models_dir = str(home / "PESSOAL-PROJETOS-ALEXANDRE" / "Fooocus" / "models" / "checkpoints")

    dir_path = Path(models_dir)
    if not dir_path.exists():
        return []

    return [f.name for f in dir_path.glob("*.safetensors")]
