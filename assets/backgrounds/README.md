# Seamless particle backgrounds

These original backgrounds belong to Standard mode only.

- `religious_particles.mp4`: Catholic Renaissance chapel, classical arches,
  aged gold, marble, burgundy drapery, sacred cross, and soft drifting gold dust.
  Fine distant specks and a few softly blurred foreground motes create depth.
  The warm amber particles move slowly and dim gently behind centered subtitles.
- `religious_renaissance_plate.png`: the original generated artwork consumed by
  the offline loop builder. The app exports the video loop without AI generation.
- `enigmatic_black.mp4`: white floating dust and subtle mist over deep black.
- `zaflas_agro.mp4`: emerald agricultural fields at golden hour with restrained
  amber pollen-like dust, inspired by Zaflas' green agricultural visual direction.
- `fallem_prince.mp4`: charcoal medieval castle engraving and sparse silver dust,
  inspired by the channel's monochrome, philosophical medieval imagery.
- `zaflas_agro_plate.png` and `fallem_prince_plate.png`: original generated
  artwork used by the offline loop builder; no generated lettering or logos.

Each silent video is 1280×720 or 720×1280, 30 fps, and 24 seconds long. The app repeats it
without limit until the existing narration/outro duration is reached. Every
particle follows a periodic path with periodic brightness. There is no intro,
outro, fade to black, or hard particle reset.

Use `python scripts/build-particle-backgrounds.py` to rebuild all eight loops and
their JPEG previews. Generation is offline and happens once; exporting a video
only decodes the bundled loop. Both 16:9 and 9:16 videos fill the output frame.
The new themes use fewer, slower particles than the religious theme to keep
their atmosphere subtle. Original artwork is preserved; there is no camera zoom.
All loops now use subpixel Gaussian glows, continuous opacity, gentle upward
travel, and soft individual lifecycle fades instead of integer-position jumps.
Depth-dependent movement separates fine distant dust from soft foreground motes.
Landscape loops use CRF 14 and portrait loops use CRF 12 to retain artwork
detail and reduce compression changes at the repeat boundary. Export still only
decodes the bundled loop; particles are not simulated during video export.

Every theme has a dedicated `_shorts.mp4` loop, selected automatically by the
Shorts / Reels preset. Portrait artwork is composed for 9:16, with a quiet
middle for centered subtitles; it is not a crop of the landscape video.
Portrait particle radii scale with the shorter dimension. The four portrait
artwork files end in `_shorts_plate.png`. The black portrait plate is generated
procedurally, preserving its established black-and-white visual language.
The other three portraits used built-in image generation with their landscape
artwork as references. Exact prompts are in [SHORTS-ART-PROMPTS.md](SHORTS-ART-PROMPTS.md).

The religious plate was created with the built-in image-generation tool.
The complete prompt is saved in [RELIGIOUS-ART-PROMPT.md](RELIGIOUS-ART-PROMPT.md).
Prompt brief: an uninhabited Italian Catholic Renaissance chapel circa 1500,
old-master oil-painting texture and sfumato, rounded classical arches, aged gold,
marble, burgundy velvet, golden light, a high cross and a low altar, with a quiet
shadowed middle for large white subtitles. No people, faces, hands, or lettering.

The channel artwork also used the built-in image-generation tool. Public
branding observations, provenance, and the complete prompts are saved in
[CHANNEL-ART-PROMPTS.md](CHANNEL-ART-PROMPTS.md).
