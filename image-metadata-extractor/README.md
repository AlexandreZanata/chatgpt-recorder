# ChatGPT Image & Metadata Extractor

A dedicated module and browser extension (Manifest V3) for automatically extracting generated images and their full metadata (prompts, revised prompts, seeds, generation IDs, dimensions, asset pointers, and conversation context) directly from ChatGPT into your `Downloads` folder while generating.

---

## Key Features

1. **Automatic Image & Metadata Capture**:
   - Captures generated image streams (`PNG`, `WebP`, `JPEG`) from ChatGPT / DALL-E.
   - Captures SSE conversation stream events and DOM metadata.
   - Pairs the raw image with a structured `*_metadata.json` file.

2. **Automatic Downloads**:
   - Saves both files simultaneously to `Downloads/chatgpt-images/`:
     - `chatgpt-img_YYYY-MM-DD_HH-MM-SS_title.png`
     - `chatgpt-img_YYYY-MM-DD_HH-MM-SS_title_metadata.json`

3. **Isolated & Non-Interfering**:
   - Completely independent from the ChatGPT Audio Capture module.
   - Runs side-by-side or standalone.

4. **Python Metadata Inspector CLI**:
   - Includes `inspector.py` to inspect, list, validate, and parse extracted metadata JSON files.

---

## Installation in Firefox

### Method 1: Load as Temporary Extension
1. Open Firefox and navigate to `about:debugging#/runtime/this-firefox`.
2. Click **"Load Temporary Add-on..."**.
3. Select `image-metadata-extractor/manifest.json`.

### Method 2: Permanent Enterprise Policy (Linux)
Run the automated installation script:
```bash
bash image-metadata-extractor/install-firefox-policy.sh
```
Restart Firefox and check `about:addons`.

---

## Python Inspector Usage

To inspect downloaded image metadata in your Downloads folder:
```bash
python3 image-metadata-extractor/inspector.py ~/Downloads/chatgpt-images/
```

To inspect a specific metadata file:
```bash
python3 image-metadata-extractor/inspector.py ~/Downloads/chatgpt-images/chatgpt-img_example_metadata.json
```
