# Standard mode: subtitles and particle backgrounds

Standard mode keeps its existing narration, music mixing, aspect ratio, output
numbering, and outro duration. AI Story mode is unaffected.

- Subtitles are checked on every new app launch. Users can uncheck them.
- Enabled subtitles transcribe narration once and burn synchronized text into
  the video. Disabled subtitles skip transcription entirely.
- Standard subtitles are large, bold white text centered horizontally and
  vertically. At 1080p, the font is approximately 97 px, with a black outline
  and safe horizontal margins. Long phrases wrap within the centered text area.
- Catholic Renaissance, Enigmatic black, Zaflas Agro, and fallem prince are
  optional checkboxes. Selecting one clears all others and disables the
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

The app uses existing FFmpeg/NVENC rendering. No diffusion model is needed for
video export. All artwork is generated once and bundled with the app.
Regenerate bundled video loops with
`python scripts/build-particle-backgrounds.py` (Pillow, NumPy, and FFmpeg).

If transcription fails or returns no speech, enabled subtitles report an error
instead of silently delivering an uncaptioned video. Users can disable subtitles
to export audio without speech. Subtitle timestamps cover narration, not the outro.
