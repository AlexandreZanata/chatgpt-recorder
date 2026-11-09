# Local narration and voice auditions

## User-visible contract

- Classic mode opens by default. Both video modes share a multiline narration editor.
- Use text for video is checked on launch. Unchecking it restores audio-file input,
  which remains available without speech dependencies.
- English is the fixed narration language; Uncle_Fu is the default voice selected from the user's
  audition. It is a Chinese-native, low, mellow male preset that can narrate in English.
  Built-in narration is locked to this one voice; alternate preset selection is disabled.
  The language selector contains only American English and is disabled. Non-English or
  automatic-language requests are rejected before inference. Existing audition files are preserved.
- Qwen3-TTS Base 0.6B is the default. The optional Base 1.7B uses the same voice reference.
  The approved original Uncle_Fu WAV and its transcript are the immutable voice/delivery
  reference. A full in-context prompt (speaker embedding plus reference acoustic codes)
  is prepared once per job and reused unchanged for every English passage.
  Missing or modified reference audio stops generation; no preset substitution is allowed.
  Free-form delivery controls are disabled so they cannot change the narrator's style.
- Every speech-model call explicitly receives English, never automatic detection.
  Subtitle recognition explicitly receives `en`, including callers passing no language.
  Other recognition languages are rejected. Recognition does not change spoken pronunciation;
  English conditioning does not guarantee an American accent from this multilingual model.
  The approved voice reference, seed, model precision and delivery settings remain unchanged.
- Test voice generates only a short excerpt and plays it in the app. Preview audio is never
  substituted for a longer narration. If a preview covers the complete script with identical
  voice/model/settings, full generation reuses its exact WAV instead of synthesizing it again.
- Generate narration synthesizes the entire text in bounded, ordered chunks, saves a WAV,
  and selects it as narration in the active video mode.
- Narration uses one passage at a time, the same original Uncle_Fu reference prompt, and
  seed 321 reset before every passage. The speaker/delivery reference never comes from a
  newly generated passage, avoiding cascading drift. Independent CustomVoice preset
  synthesis is not used for narration. Reference conditioning is stronger than a preset
  ID and seed alone, but perceptual identity across a long article still requires listening.
- Eligible CUDA/0.6B synthesis uses a locally tested optional CUDA-graph decoder with the
  same model weights, bfloat16 precision, and sampling settings. Graphs warm up once per
  job. Unpadded attention masks built during warmup are reused for single-passage input;
  padded input still rebuilds its appropriate masks. If acceleration is unavailable,
  the original engine uses the same voice and seed.
  No alternate voice, online API, time stretching, or quantization is used as a fallback.
- The narration cache revision includes the Base/reference profile and approved WAV digest.
  The English-only revision also excludes earlier multilingual-profile narration; original
  audio remains on disk. Recognition caches from automatic language detection are not reused.
  Neither earlier random-preset audio nor fixed-seed CustomVoice audio is reused. Older generated
  audio is preserved but cannot silently replace newly corrected narration.
- With Use text for video enabled, Generate Video waits for complete, current narration.
  Changes to text, voice, language, model or voice-reference revision invalidate reuse.
  Unsupported delivery instruction text has no effect on the fixed-reference request.
- Empty text is rejected before loading a model. Identical completed requests reuse their WAV.
- Generation is asynchronous. Concurrent speech/video jobs are blocked. Cancellation never
  exposes a partial WAV as complete narration; errors are visible and controls recover.
- The app/worker packet includes the voice-profile revision. A stale app launching a new
  worker is rejected with a restart instruction, rather than mislabeling reference-based
  audio under an old preset cache key. Restart after an existing job completes; code edits
  do not replace the narrator or style inside a running job.
- Speech runs in a separate Python process/environment and releases its model before video
  generation. It uses only its own bundled CUDA/cuDNN library paths, never inherited Fooocus
  GPU paths. The existing Fooocus dependencies are not modified.
- The first synthesis downloads official model weights if absent. Later synthesis uses the
  local model cache without network checks when its required files are complete.
  No narration is sent to an online speech API.

## Setup

Run `bash scripts/setup-local-tts.sh` once from the project directory. It installs a separate
speech environment under `.local/tts-venv`, not into the desktop or Fooocus environment.
Restart the desktop app, leave **Use text for video** enabled, paste narration for Uncle_Fu,
and click **Test voice**. Use **Generate narration** to save the entire script, or click
**Generate Video** to generate narration before the existing video workflow.

The first model download requires Internet access and several GB of disk space. CUDA is
preferred; CPU fallback works but can be significantly slower. The 1.7B option uses more
memory than 0.6B. Neither latency nor GPU compatibility is guaranteed without a local test.
Voice tests use up to 60 words, not the entire article. WAVs are saved in `audio/generated/`
and `audio/previews/`. Stop playback is separate from Cancel generation.

## References

- [Qwen3-TTS models, presets and generation API](https://github.com/QwenLM/Qwen3-TTS)
- [Published qwen-tts package](https://pypi.org/project/qwen-tts/)
- [Optional CUDA-graph decoder (tested version 0.2.6)](https://github.com/andimarafioti/faster-qwen3-tts)
- [Qt audio player](https://doc.qt.io/qtforpython-6/PySide6/QtMultimedia/QMediaPlayer.html)

## Validation scope

The reference-based Base 0.6B path was tested through the real app adapter on the local
RTX 4060 Laptop after the user's existing export finished. One full reference prompt
was prepared for three passages; generation produced 71.16 seconds of mono 24 kHz PCM16
audio in 56.61 seconds including startup. Independent transcription matched the complete
script without leaking reference text. This validates generation/words, not perceived
voice identity across a full-length video; compare the new listening sample with the
approved original before another long export. The five-minute full-export target is
not established by this test.

The following timing measurements concern the earlier CustomVoice decoder, not the new
reference-anchored Base path. They must not be presented as Base performance measurements.

Automated tests cover contracts with deterministic speech adapters and Qt offscreen UI.
These are not measurements of real Qwen speech quality, synthesis speed, or laptop CUDA.

On the local RTX 4060 Laptop, with the GPU free, a real two-passage opening produced
70.66 seconds of speech in 44.19 seconds through the application adapter, including
process/model/graph startup. The final WAV matches the checked opening byte-for-byte.
The same completed request reused its WAV without inference. A separate short warm test
took 6.14 seconds with graphs versus 12.15 seconds with the original decoder. These are
sample measurements, not a full-video timing guarantee. Transcript checks detect missing
words, not perceived voice identity; listen to the revised opening before a long export.

Warm decoding of a 32-second passage took approximately 13.8 seconds with the GPU alone
at approximately 96–98% utilization. Extrapolating this sample gives approximately 17–26
minutes of synthesis for 40–60 minutes of narration, before subtitle/video work; this is
not a measured long-video run. The under-five-minute complete-export target is not met
by this configuration. Extra speech processes are not enabled just to maximize process
count: they contend for the same busy GPU and reintroduce batch-dependent variation.
