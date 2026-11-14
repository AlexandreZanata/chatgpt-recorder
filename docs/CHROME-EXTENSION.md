# ChatGPT Audio Capture — Chrome

For the complete bot on Linux, prefer [the assisted installer](INSTALL-LINUX.md): its
dedicated browser loads the extension automatically, without selecting a folder.

## Installation

1. Run `npm run build:chrome` from the project root.
2. Open `chrome://extensions` in Google Chrome.
3. Enable **Developer mode**, then click **Load unpacked**.
4. Select the generated `dist/chrome` folder, not the root or a manifest file.
5. Reload any existing ChatGPT tabs and sign in using your normal Chrome session.
6. Pin the extension from Chrome's Extensions menu to access its settings.

Chrome 116 or newer is required. The Firefox manifest remains unchanged.
The separate archive is `dist/chatgpt-audio-capture-chrome-v0.1.0.zip`.
Settings are separate between browsers; use the popup's Export/Import buttons
to transfer them. Existing downloaded files remain in your Downloads folder.

## Capture a complete Read aloud response

1. Open the ChatGPT conversation and the extension popup.
2. Click **Record complete tab audio** and wait for **Recording**.
3. Close the popup and click ChatGPT's **Read aloud**.
4. Wait until the entire response has finished playing. Gaps and pauses are recorded.
5. Open the extension popup again and click **Stop and save recording**.
6. Wait for **Saved complete recording**, then open the WebM in Downloads.

This records the selected ChatGPT tab's audio output, including any other sound
from that tab. It never records the microphone. Audio stays audible during recording.
The offscreen recorder continues when the popup closes and when the service worker
sleeps. There is no fixed time cutoff; stop explicitly after the final spoken word.
Leading/trailing silence and pauses are retained. Recording uses Opus in WebM,
not MP3 conversion. Keep the tab open and do not reload the extension while recording.

Explicit manual recording saves even if **Auto Download** is off. Automatic captures
from the same tab are suppressed during manual recording/saving. If a download fails,
use **Retry saving recording**; the Blob stays available until a successful download.
An extension reload or browser exit discards unsaved in-memory recording data.

Automatic response capture remains available as a best-effort option. It depends
on the page's network/audio implementation; use complete-tab recording when that
path produces no file, duplicates, or incomplete audio. Tab capture requires an
explicit extension invocation, so this mode does not silently start on Read aloud.

## Behavior contract

- GIVEN complete-tab recording started from the extension popup before Read aloud,
  WHEN the user stops and saves after playback finishes, THEN download one WebM
  containing all tab audio, including both sides of streaming gaps and pauses.
- GIVEN complete-tab recording, THEN keep recording when the popup closes, keep
  playback audible, and impose no fixed recording timeout. Do not use the microphone.
- GIVEN manual recording in progress, THEN suppress automatic captures from that tab.
- GIVEN a recording download, THEN show saved only after download completion;
  retain the recording for retry if downloading fails.
- GIVEN a ChatGPT tab left open across an extension update, THEN request a tab
  reload once and never throw an uncaught invalid-context error into the page.
- GIVEN successful ChatGPT audio WHEN it is captured THEN save its original
  response bytes without altering the page's response or playback.
- GIVEN WebAudio or an audio element without captured network audio WHEN
  playback ends or pauses THEN save a WebM recording as a fallback.
- GIVEN an HTTP error or non-audio response THEN never save it as an audio file.
- GIVEN auto-download disabled THEN do not automatically download or increment
  the badge; an explicit manual recording/save remains available.
- GIVEN filename settings THEN preserve prefix/date/time/title placeholders
  and the optional relative Downloads subfolder.
- GIVEN an accepted download THEN update the badge and recent capture history.
- GIVEN another origin, frame, extension, or invalid payload THEN reject it.
- GIVEN popup settings WHEN exported and imported THEN restore the same keys.
- GIVEN worker restart THEN keep settings/history and the session capture count.
- GIVEN the Chrome build THEN include only extension assets, no Python models,
  videos, user media, browser credentials, or Firefox-only permissions.

Chrome cannot use Firefox's `webRequest.filterResponseData()`. It captures
successful fetch responses in the page's MAIN world and uses WebAudio/media
fallbacks. No requests are replayed, rewritten, or made with copied credentials.
It cannot repair a server-side Read aloud failure or generate missing audio.
Complete-tab capture uses Chrome's tabCapture/offscreen APIs independently of
ChatGPT's private audio endpoints. Icon/badge updates must never block capture
or saving, and history distinguishes pending, complete, and interrupted downloads.

## Verification

Run `npm run build:chrome`, then `npm run verify`.
Automated tests cover Chrome packaging, downloads/settings, trust boundaries,
and page audio capture without consuming the original response.
Authenticated ChatGPT playback must also be checked in the user's Chrome.

Run `npm run test:chrome` for the real Google Chrome audio regression test.
It needs Python Playwright, FFmpeg, and Chrome with the extension-testing protocol.
Set `CHROME_AUDIO_BROWSER` for another compatible Chrome executable.
The test uses a temporary browser profile and controlled oscillator audio under a
routed test page; it does not sign in or claim to reproduce ChatGPT's private transport.
It decodes the downloaded WebM to verify both passages and their streaming gap.

## Official references

- [Load unpacked extensions](https://developer.chrome.com/docs/extensions/get-started/tutorial/hello-world)
- [Content script worlds](https://developer.chrome.com/docs/extensions/reference/manifest/content-scripts)
- [Service worker migration](https://developer.chrome.com/docs/extensions/develop/migrate/to-service-workers)
- [Chrome icons](https://developer.chrome.com/docs/extensions/reference/manifest/icons)
- [Downloads API](https://developer.chrome.com/docs/extensions/reference/api/downloads)
- [Tab audio capture](https://developer.chrome.com/docs/extensions/reference/api/tabCapture)
- [Offscreen recorder](https://developer.chrome.com/docs/extensions/reference/api/offscreen)
