# Channel background artwork

Generated once with the built-in image-generation tool. The original PNGs are
bundled in this directory; video export never calls an image-generation model.
Original artwork inspired by visual direction, not copied channel assets.

## Public branding observations

The Studio URLs required sign-in. The corresponding public channel pages were
inspected instead on 2026-10-01:

- [Zaflas](https://www.youtube.com/channel/UCi2aftoK7vlS3A6OozMHXKg),
  handle `@zaflas`: bright green avatar; agricultural thumbnails featuring
  emerald crops, warm golden sunlight, and dark contrast. The background uses
  those landscape and palette cues without reproducing its logo or lettering.
- [fallem prince](https://www.youtube.com/channel/UCc288lF54UDCCGhTKIkr7BQ),
  handle `@fallemprince`: black-and-white medieval banner and engraved,
  introspective imagery. The background uses castle architecture, etched stone,
  charcoal mist, and silver dust, omitting people and human anatomy.

## Zaflas Agro — exact generation prompt

```text
Use case: photorealistic-natural
Asset type: original 16:9 cinematic artwork plate for a calm looping YouTube narration background.
Primary request: a premium Brazilian agricultural landscape inspired by the public Zaflas agro channel's vivid green crops, dark contrast and golden agricultural sunset imagery. Original artwork, not a copy of any thumbnail.
Scene/backdrop: rolling emerald soybean fields with beautifully organized crop rows, distant tree lines and gentle golden light along a high horizon; close natural crop leaves at the bottom edge. No people or machinery.
Style/medium: refined photorealistic agricultural editorial photography with cinematic depth, authentic leaf detail and subtle atmospheric perspective.
Composition/framing: widescreen 16:9, panoramic fields; concentrate sunset highlights in the upper quarter and leaf detail in the lower quarter. Preserve a broad, calm, naturally shadowed deep-green middle for large white centered subtitles. The center crop must still read as agriculture for portrait videos.
Lighting/mood: warm golden-hour rim light, optimistic, fertile, peaceful, professional; emerald and forest green with restrained amber highlights.
Constraints: clean unlettered background, no typography, no logo, no watermark, no UI, no border. No faces, hands or people. Do not bake floating particles into the artwork: particles will be animated separately. Avoid an overexposed center, excessive noise or oversharpening.
```

Saved artwork: `zaflas_agro_plate.png`.
Original generation filename: `exec-08218706-b323-4771-af1d-053ecf3e0da9.png`.

## fallem prince — exact generation prompt

```text
Use case: stylized-concept
Asset type: original 16:9 monochrome artwork plate for a calm looping philosophical YouTube narration background.
Primary request: a premium enigmatic black background aligned with the public fallem prince channel's monochrome medieval engraving aesthetic, introspection and gothic castle imagery. Original artwork, not a copy of its banner.
Scene/backdrop: distant medieval stone castle towers high in a misty landscape, a weathered stone path and restrained ruined masonry along the lower edges, subtly dissolving into deep charcoal atmosphere.
Style/medium: exquisite black-and-white copperplate engraving, fine crosshatching and etched stone texture, dramatic yet quiet, timeless philosophical book illustration; strictly monochrome, not glossy 3D.
Composition/framing: widescreen 16:9, architectural silhouette in upper quarter, foreground etched stones near lower corners, broad low-detail charcoal mist through the middle. Keep the middle naturally dark and quiet for large white centered subtitles; maintain recognizable atmosphere in a portrait center crop.
Lighting/mood: silver-gray rim light through distant mist, black and graphite shadows, restrained pale highlights, solemn contemplative mystery.
Constraints: no people, bodies, faces, hands or skeletons, no text, typography, logo, watermark, border, saturated color or neon. No bright white central sky and no baked floating particles; sparse silver dust will be animated separately.
```

Saved artwork: `fallem_prince_plate.png`.
Original generation filename: `exec-2f6dcb76-d021-4536-8ff6-dfa95492ccca.png`.

## Animation

Particle profiles are in `src/engine/particle_profiles.py`.
Zaflas Agro uses 100 warm pollen-like motes; fallem prince uses 90 silver motes.
Position and brightness are periodic over 24 seconds. Soft Gaussian halos and
reduced brightness behind centered captions preserve readability. The artwork
and camera stay fixed. The app decodes prebuilt H.264 loops at 30 fps.
