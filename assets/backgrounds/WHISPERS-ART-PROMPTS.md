# Whispers From Heaven artwork provenance

Generated with the built-in Imagegen tool on 2026-10-11. The two user-supplied
channel screenshots were visual references only. Artwork is original, with no
copied thumbnails, browser interface, channel lettering, or logos.

Use case: `historical-scene`. The palette is monochromatic brown/sepia, with
fine ink stippling, antique Bible engraving, aged parchment, and quiet space
for centered subtitles. Landscape and portrait are separate compositions.
The existing offline builder overlays muted sepia dust; no generation runs
inside the application or during video export.

Files:
- `whispers_from_heaven_plate.png`: landscape artwork.
- `whispers_from_heaven_shorts_plate.png`: portrait artwork.
- `whispers_from_heaven.mp4` and `whispers_from_heaven_shorts.mp4`: bundled loops.
- Matching `.jpg` files: encoded-loop preview images.

## Landscape prompt

Use case: historical-scene. Asset type: original landscape 16:9 background plate for the biblical storytelling video theme Whispers From Heaven, rendered at 1536x864 or another exact 16:9 resolution. The attached two YouTube channel screenshots are STYLE REFERENCES ONLY; do not reproduce their browser UI, thumbnails, text or channel logo. Create one edge-to-edge atmospheric antique biblical illustration: an ancient Judean valley with layered distant hills, a winding path, a gnarled olive tree framing the left edge, a small robed figure kneeling in prayer low at the far left, and dramatic clouds opening to restrained diagonal shafts of heavenly light from the upper right. Tiny distant ancient stone buildings suggest the Holy Land. Style: dense hand-stippled brown ink pointillism and fine antique Bible copperplate engraving on aged parchment, expressive dots and delicate hatching rather than photorealism or oil painting. Strict monochromatic brown/sepia palette only, from deep umber shadows through tobacco brown to muted parchment tan; no blue, green, red, white-hot yellow, or colorful accents. Calm reverent contemplative mood. Wide cinematic composition with the main figure peripheral; middle 55 percent must remain a quiet softly shaded brown atmospheric valley with low contrast, suitable for large centered white subtitles. Darkened corners, finely detailed edges, soft light, beautiful paper grain. No lettering, typography, borders, panels, watermark, logo, headphones or interface. Do not paint a conspicuous particle overlay; floating dust will be animated separately. Deliver only one complete landscape illustration.

## Portrait prompt

Use case: historical-scene. Asset type: original PORTRAIT 9:16 background plate for the biblical storytelling video theme Whispers From Heaven, render at exact 9:16 portrait dimensions. The immediately preceding generated landscape is a style reference only; create a dedicated vertical composition, not a crop. Antique Bible illustration of a peaceful ancient Judean valley: a gnarled olive tree framing the upper left and left edge; a small robed traveler kneeling in prayer low at the bottom left, below the central subtitle area; winding stone path leading into distant hills and tiny ancient stone buildings at bottom right; tall cloud-filled sky above with restrained shafts of heavenly light descending from upper right. Dense fine hand-stippled brown ink POINTILLISM with minute dots and delicate engraving crosshatching on aged parchment, matching the landscape's antique biblical illustration. Strictly monochromatic brown sepia, deep umber shadows through tobacco brown to muted parchment tan, no other color hues. Reverent, quiet, contemplative atmosphere. Reserve the middle 50 percent of the portrait as soft low-contrast shaded brown distant atmosphere, quiet enough for large white centered subtitles. Put brighter light high in the sky and detail near the edges. Dark vignette and fine paper grain. No text, lettering, border, panels, watermarks, logos, UI or modern objects. Do not paint conspicuous particle overlays, dust is animated separately. Deliver only one complete full-bleed portrait illustration.

## Rebuild only this theme

```bash
python3 - <<'PY'
import runpy
build = runpy.run_path('scripts/build-particle-backgrounds.py')['build_loop']
build('whispers_from_heaven')
build('whispers_from_heaven', portrait=True)
PY
```

This targeted rebuild preserves all existing assets. Each loop is silent H.264,
24 seconds at 30 fps, 1280x720 landscape or 720x1280 portrait.
