"""Ordered speech generation using one mandatory, unchanged acoustic reference."""


def batch_size(model, cuda, free_bytes, count):
    """Avoid batch-dependent sampling changes in the user's single-voice narration."""
    return 1


def synthesize_passages(model, request, chunks, size=1, oom_error=MemoryError,
                        on_oom=lambda: None, progress=lambda message: None,
                        reset_seed=lambda: None, voice_prompt=None):
    if voice_prompt is None:
        raise ValueError("A fixed Uncle_Fu voice reference is required before generating passages.")
    size = min(2, max(1, size))
    index = 0
    while index < len(chunks):
        group = chunks[index:index + size]
        progress(f"Synthesizing passage {index + 1}/{len(chunks)} ({len(group)} at once)...")
        retry = False
        try:
            reset_seed()
            wavs, rate = model.generate_voice_clone(
                text=group if len(group) > 1 else group[0], language=request.language,
                voice_clone_prompt=voice_prompt,
                max_new_tokens=2048,
            )
        except oom_error:
            if len(group) == 1:
                raise
            retry = True
        if retry:
            on_oom()
            progress("GPU memory is limited; retrying these passages sequentially...")
            size = 1
            continue
        if len(wavs) != len(group):
            raise RuntimeError("Speech model did not return every requested passage.")
        for offset, wav in enumerate(wavs):
            yield index + offset, wav, rate
        index += len(group)
