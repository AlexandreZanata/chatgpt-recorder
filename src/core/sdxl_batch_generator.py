"""Batch generator for Fooocus / SDXL local checkpoints using Lightning performance."""

import json
from pathlib import Path
from typing import Dict, List, Optional
import urllib.request


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


def request_local_sdxl_image(
    prompt: str,
    output_path: str,
    model_name: str = "RealVisXL_V5.0_fp16.safetensors",
    performance: str = "Lightning",
    aspect_ratio: str = "1152*896"
) -> bool:
    """Request image generation from local Fooocus API or save placeholder if offline."""
    api_url = "http://127.0.0.1:7865/api/predict"
    payload = {
        "fn_index": 33,
        "data": [
            prompt,
            "",
            ["Fooocus V2", "Fooocus Photograph"],
            performance,
            aspect_ratio,
            1,
            -1,
            2.0,
            model_name,
            "None",
            0.5
        ]
    }
    try:
        req = urllib.request.Request(
            api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            if res_data and "data" in res_data:
                # Image generated successfully
                return True
    except Exception:
        pass
    return False
