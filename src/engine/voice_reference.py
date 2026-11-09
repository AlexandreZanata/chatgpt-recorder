"""One immutable original Uncle_Fu acoustic/style reference for the entire narration."""

import hashlib
from pathlib import Path

from src.core.narration import VOICE_REFERENCE_SHA256

REFERENCE_AUDIO = Path(__file__).resolve().parents[2] / "assets/voices/Uncle_Fu-reference.wav"
REFERENCE_TEXT = (
    "Beyond the quiet hills, a new morning begins. The sunlight touches the trees, "
    "and the world feels peaceful. Take a breath, listen closely, and let the story unfold."
)


def validate_reference(path=None):
    reference = REFERENCE_AUDIO if path is None else Path(path)
    if not reference.is_file():
        raise FileNotFoundError("The approved Uncle_Fu voice reference is missing. Restore the bundled WAV.")
    if hashlib.sha256(reference.read_bytes()).hexdigest() != VOICE_REFERENCE_SHA256:
        raise ValueError("The Uncle_Fu voice reference changed; generation stopped to prevent a different voice.")
    return reference


def create_reference_prompt(model, path=None):
    reference = validate_reference(path)
    prompt = model.create_voice_clone_prompt(ref_audio=str(reference), ref_text=REFERENCE_TEXT,
                                             x_vector_only_mode=False)
    if len(prompt) != 1 or not prompt[0].icl_mode or prompt[0].x_vector_only_mode or prompt[0].ref_code is None:
        raise RuntimeError("The model did not prepare the complete fixed voice reference.")
    return prompt
