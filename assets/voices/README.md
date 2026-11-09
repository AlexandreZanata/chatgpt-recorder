# Approved synthetic voice reference

`Uncle_Fu-reference.wav` is the user's selected original synthetic narration audition:
Qwen3-TTS CustomVoice 0.6B, Uncle_Fu, seed 321. It is preserved byte-for-byte, not trimmed,
time stretched, or converted: mono PCM16 at 24 kHz, 14.16 seconds.

SHA256: `37c0f7ecb126f36e96723cef6e9f7d6f9efc251879ae9cf5e32981b6399ada76`.

Exact transcript:

> Beyond the quiet hills, a new morning begins. The sunlight touches the trees, and the
> world feels peaceful. Take a breath, listen closely, and let the story unfold.

The Base narrator extracts the complete in-context speaker/acoustic prompt once and
reuses it across all passages. Do not silently replace this asset, use a generated
passage as the next reference, or fall back to a different preset. A changed reference
requires an explicit user decision, profile revision and renewed listening validation.
