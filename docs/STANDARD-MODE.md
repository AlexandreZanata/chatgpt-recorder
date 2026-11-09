# Standard mode: subtitles and particle backgrounds

Standard mode keeps its existing narration, music mixing, aspect ratio, output
numbering, and outro duration. AI Story mode is unaffected.

- Subtitles are checked on every new app launch. Users can uncheck them.
- Classic mode and text narration are the startup defaults; imported audio remains optional.
- Enabled subtitles transcribe narration once and burn synchronized text into
  the video. Disabled subtitles skip transcription entirely.
- All scripts are English: subtitle recognition is explicitly locked to `en`, never
  automatic language detection. Old automatic-detection caches are not reused.
- Transcription results are cached locally by audio bytes, model, language, timestamp settings,
  and installed transcription-engine versions. Changing any of these invalidates reuse.
  Failed/empty transcription is never cached; corrupt cache entries are regenerated.
- Standard subtitles are large, bold white text centered horizontally and
  vertically. At 1080p, the font is approximately 97 px, with a black outline
  and safe horizontal margins. Long phrases wrap within the centered text area.
- Catholic Renaissance, Enigmatic black, Zaflas Agro, fallem prince, and
  Whispers From Heaven are optional checkboxes. Selecting one clears all others and disables the
  background image picker. Clearing all selections
  restores the image picker and its previous value.
- A selected theme overrides the image, including when no image was selected.
- Each background is a bundled, silent, 24-second H.264 loop. Particle position
  and brightness are periodic, avoiding a reset or fade at the loop boundary.
- All themes use subpixel particle rendering: fractional movements, including
  0.1-pixel translations, change the glow raster instead of snapping to integer
  coordinates. Brightness varies continuously, without coarse opacity steps.
- Particles rise in one continuous direction with gentle lateral drift and
  depth-dependent travel. Individual particles fade smoothly before recycling;
  the background never fades, moves, or zooms. Motion and glow remain periodic.
- Catholic Renaissance uses a painterly Italian chapel with classical arches,
  aged gold ornament, burgundy drapery, marble, warm light, and a cross above
  the altar. Fine amber dust and softly blurred foreground motes drift slowly
  over the artwork, with reduced brightness behind centered text. Its shadowed middle
  preserves centered subtitle contrast in landscape and portrait.
  Enigmatic black uses white dust and subtle mist over black.
- Zaflas Agro uses emerald crop rows, golden-hour light, and restrained warm
  pollen-like particles. Its landscape remains quiet behind centered captions.
- fallem prince uses a strictly monochrome medieval castle engraving, charcoal
  mist, and sparse silver dust, with no human anatomy. The original Enigmatic
  black and religious artwork remain available and unchanged; particle motion
  is improved consistently across all four backgrounds.
- Whispers From Heaven uses monochromatic brown biblical stippling and antique
  Bible engraving: an olive tree, a figure in prayer, an ancient Judean valley,
  and soft heavenly light. Muted sepia particles drift gently over separate
  landscape and portrait compositions. It adds an optional fifth theme without
  changing the four existing themes, their assets, or the export workflow.
  Prompts and targeted rebuild instructions are in
  `assets/backgrounds/WHISPERS-ART-PROMPTS.md`.
- The new themes are inspired by the public channels' visual direction, not
  copies of their banners or thumbnails. See the channel artwork prompt record
  in `assets/backgrounds/CHANNEL-ART-PROMPTS.md` for sources and exact prompts.
- Every theme has separate landscape and portrait loops. Selecting the Shorts
  / Reels preset automatically selects that theme's `_shorts.mp4` background,
  1080x1920 export, portrait particle composition, and large centered captions.
  Switching back to Standard selects its original landscape loop again.
- Portrait artwork is composed for 9:16, not cropped from the landscape video.
  Particle radii scale with the shorter dimension to preserve gentle dust size.
- Bundled loops are 1280x720 (landscape) or 720x1280 (portrait), with the same
  pixel count, frame rate, and existing single-pass export workflow. No image
  generation occurs when switching presets or exporting a video.
- Custom still images retain their original fit-and-pad behavior in both
  formats. Animated backgrounds render at 30 fps. Shorts retain their existing
  narration-only duration without the landscape outro.
- Static backgrounds decode/scale at 1 fps and repeat the identical frame at the existing
  output frame rate before subtitle rendering. Animated particle loops are not decimated.
  Resolution, subtitle styling, NVENC preset/QP, frame rates, and audio bitrate are unchanged.
- WAV narration duration comes directly from its frame count; other formats use metadata
  first, with packet scanning only when metadata cannot provide a finite positive duration.
- Long Classic exports (at least 120 seconds, with at least eight logical CPU cores)
  use four bounded FFmpeg workers. Each encodes an exact, ordered frame range at the existing
  NVENC preset/QP. Background loop phase and subtitle times stay on the global timeline.
  Workers discard the initial loop-phase offset by exact frame count before scaling, without input seeking,
  so FFmpeg repeats the complete background loop rather than a shortened seeked section.
  Final assembly stream-copies video and encodes/mixes the complete audio once, avoiding
  audio gaps at chunk boundaries or a second lossy video encode. Both static and animated
  backgrounds retain their original frame rates. Short exports stay single-pass.
  Parallel failure falls back to the existing single-pass renderer with the same quality.

The app uses existing FFmpeg/NVENC rendering. No diffusion model is needed for
video export. All artwork is generated once and bundled with the app.
Regenerate bundled video loops with
`python scripts/build-particle-backgrounds.py` (Pillow, NumPy, and FFmpeg).
This rebuilds every theme; the Whispers prompt record shows how to rebuild only
the two Whispers loops while preserving all other assets.

If transcription fails or returns no speech, enabled subtitles report an error
instead of silently delivering an uncaptioned video. Users can disable subtitles
to export audio without speech. Subtitle timestamps cover narration, not the outro.
