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
