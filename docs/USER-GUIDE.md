# ChatGPT Audio Capture — User Guide

Welcome to the **ChatGPT Audio Capture** Firefox extension guide.

---

## 1. Quick Installation (Firefox)

1. Open Firefox and navigate to `about:debugging#/runtime/this-firefox`.
2. Click **Load Temporary Add-on...**.
3. Select the `manifest.json` file inside the `chatgpt-recorder` project directory (or unzipped release).
4. The extension icon will appear in your Firefox toolbar.

---

## 2. Usage & Audio Capture

1. Open [chatgpt.com](https://chatgpt.com) and sign in.
2. In any chat prompt response, click **"Read Aloud"** / **"Ouvir"**.
3. **Instant Capture (Strategy A)**: The extension intercepts TTS response bytes directly from the network.
4. As soon as audio finishes, the file is automatically saved to your local downloads folder.
5. The extension icon reflects current state:
   - **Idle (Gray)**: Ready for audio capture.
   - **Recording (Red)**: Audio stream being captured.
   - **Saved (Green)**: File saved successfully to disk.

---

## 3. Keyboard Shortcuts

- `Ctrl+Shift+U` (or `Cmd+Shift+U` on macOS): Toggle / open extension popup settings.

---

## 4. Configuration & Nomenclatures

Click the extension icon to customize settings:

- **Auto Download**: Automatically saves audio files upon capture.
- **Filename Prefix**: Custom prefix string (default: `chatgpt-tts`).
- **Filename Pattern**: Customize file template with placeholders:
  - `{prefix}` — Custom prefix
  - `{date}` — Date string (`YYYY-MM-DD`)
  - `{time}` — Time string (`HH-MM-SS`)
  - `{title}` — Slugified conversation title from DOM
- **Subfolder**: Optional subfolder inside Downloads (e.g., `chatgpt-audio`).
- **Export / Import Settings**: Backup settings and capture history to JSON files.

---

## 5. Quality Verification & Build

Run verification suite:
```bash
npm run verify
npm run build
```
The output zip package will be generated at `dist/chatgpt-audio-capture-v0.1.0.zip`.
