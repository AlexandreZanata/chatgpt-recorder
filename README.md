# ChatGPT Audio Capture — Firefox Extension (MV3)

A high-performance Firefox extension (Manifest V3) designed to automatically capture and save text-to-speech (TTS) audio generated on `chatgpt.com` directly to your local machine in real-time.

---

## 🌟 Key Features

- **Multi-Layer Audio Interception**:
  1. **Network Interception**: Intercepts raw audio stream chunks via `webRequest.filterResponseData()`.
  2. **WebAudio API Hooking**: Taps into `AudioDestinationNode` connections (`AudioNode.prototype.connect`) to capture WebSocket speech streams.
  3. **MediaElement Capture**: Automatically captures `<audio>` streams using `captureStream()` or blob fetching.
  4. **Main-World Fetch Cloning**: Clones audio response payloads in page context.
- **Zero-Latency Downloads**: Saves audio files instantly without re-encoding delays.
- **Dynamic File Naming & Templates**: Fully customizable templates supporting `{prefix}`, `{date}`, `{time}`, and `{title}` variables (e.g. `chatgpt-tts_2026-08-11_my-chat.mp3`).
- **Interactive Popup UI**: Modern glassmorphism UI displaying real-time status badges, recent capture history, preview audio player, and settings export/import.
- **Quality Gate Enforced**: 100% compliant with strict code quality limits (file ≤200 lines, function ≤80 lines, cyclomatic complexity ≤10).

---

## 🚀 Quick Installation Guide (Firefox)

1. Clone or download this repository.
2. Open Firefox and navigate to:
   ```text
   about:debugging#/runtime/this-firefox
   ```
3. Click **Load Temporary Add-on...**.
4. Select `manifest.json` from the repository root directory.
5. Open [chatgpt.com](https://chatgpt.com) and click **"Read Aloud"** on any response. Audio will download automatically to your default `Downloads` folder!

---

## ⚙️ Build & Quality Verification

### Google Chrome version

Run `npm run build:chrome`, then open `chrome://extensions`, enable
**Developer mode**, click **Load unpacked**, and select `dist/chrome`.
Reload existing ChatGPT tabs before using Read aloud.
The Chrome build preserves the popup/settings and uses Chrome-compatible
audio capture. Firefox's manifest and response filter remain unchanged.
See [the Chrome guide](docs/CHROME-EXTENSION.md) for details and limitations.

To verify code quality and generate the production distribution archive:

```bash
# Verify code quality gates (Size/Complexity, Lint, System, Tests, Package Integrity)
npm run verify

# Build distribution ZIP package
npm run build
```
The output package will be generated at `dist/chatgpt-audio-capture-v0.1.0.zip`.

---

## 📄 Technical Architecture

### Desktop text-to-speech narration

The video desktop app supports pasted narration text with the fixed Uncle_Fu voice,
fixed English narration and recognition, short voice auditions, and full WAV generation
in both video modes. Existing audio-file input remains available.
Classic mode, text narration, and subtitles are enabled on launch. Long Classic
exports use bounded four-worker rendering. The Base narrator builds one full acoustic
prompt from the approved original Uncle_Fu sample and reuses it for every passage.
Eligible 0.6B narration uses CUDA graphs and a fixed seed, without changing the voice
reference or applying free-form delivery overrides. Subtitle/encoding quality settings
are preserved; GPU fallbacks keep the same Base model and reference, never another preset.
Run `bash scripts/setup-local-tts.sh` once to install the isolated speech engine,
then restart the desktop app and use **Test voice** or **Generate full narration**.
The first voice test downloads Base model weights; Qwen3-TTS Base 0.6B with Uncle_Fu is the
user-selected default and the only selectable voice. The 1.7B model remains optional.
See [local narration setup and limitations](docs/LOCAL-NARRATION.md).

```text
┌─────────────────────────────────────────────────────────────┐
│  chatgpt.com (Firefox Tab)                                  │
│                                                             │
│  ┌───────────────────────┐   postMessage   ┌──────────────┐ │
│  │ page-injector.js      │────────────────▶│ content-     │ │
│  │ (WebAudio / Fetch /   │                 │ script.js    │ │
│  │  HTMLAudioElement)    │                 └──────┬───────┘ │
│  └───────────────────────┘                        │         │
└───────────────────────────────────────────────────┼─────────┘
                                                    ▼ sendMessage
                              ┌───────────────────────────────┐
                              │ background.js                 │
                              │ - webRequest.filterResponseData
                              │ - Filename Template Engine    │
                              │ - browser.downloads.download()│
                              └───────────────────────────────┘
```

For detailed user instructions and configuration guide, see [`docs/USER-GUIDE.md`](docs/USER-GUIDE.md).

---

## 📜 License

Apache 2.0 License.
