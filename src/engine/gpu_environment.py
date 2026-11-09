"""Keep speech CUDA libraries isolated from the desktop/image environment."""

import os
from pathlib import Path


def speech_environment(python_path: Path, inherited=None) -> dict:
    """Select this venv's libraries before the child interpreter starts."""
    environment = dict(os.environ if inherited is None else inherited)
    root = Path(python_path).parent.parent
    libraries = sorted(root.glob("lib/python*/site-packages/nvidia/*/lib"))
    libraries += sorted(root.glob("lib/python*/site-packages/torch/lib"))
    environment.pop("LD_LIBRARY_PATH", None)
    if libraries:
        environment["LD_LIBRARY_PATH"] = os.pathsep.join(str(path) for path in libraries)
    environment["PYTHONNOUSERSITE"] = "1"
    return environment
