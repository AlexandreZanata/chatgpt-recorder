# YoutubeBot

A local Linux video workflow with three existing surfaces: the Firefox/Chrome ChatGPT
audio-capture extension, the Python/PySide6 video studio, and the resumable YouTube
production/upload/scheduling bot. Extension behavior, video engines, voices, prompts,
subtitles, metadata, end screens and scheduling stay unchanged. The account manager and
ZaturoBot adapter are additive.

For coding agents: start with [AGENTS.md](AGENTS.md), then [the component map](docs/ARCHITECTURE.md).
There is no agent harness, dynamic rule tree or required Git-hook framework.

## Install on Ubuntu/Debian

From the permanent project folder, run `bash scripts/install-linux.sh`. This prepares the
desktop app and a dedicated browser that loads the Chrome extension automatically, keeps
existing accounts, and opens the guided account manager. No folder selection is needed.
See [installation, sign-in and recovery instructions](docs/INSTALL-LINUX.md).

## Existing workflows

Firefox: load `manifest.json` from `about:debugging#/runtime/this-firefox`.
Chrome: `npm ci && npm run build:chrome`, then load `dist/chrome` as an unpacked extension.
Read [the Chrome guide](docs/CHROME-EXTENSION.md) and [extension user guide](docs/USER-GUIDE.md).

Video studio: install the tested Python desktop dependencies in your own virtualenv,
then run `python app_desktop.py` or `bash scripts/launch-desktop-app.sh`. Existing Classic,
Auto AI Story, narration, subtitles, background and rendering controls remain available.
See [video modes](docs/STANDARD-MODE.md) and [local narration](docs/LOCAL-NARRATION.md).
Optional GPU/model engines retain their existing setup; dependencies/caches are not
silently substituted with another model or voice.

```bash
python3 -m venv .venv
# Select the official PyTorch CPU/CUDA wheel appropriate for this PC first.
.venv/bin/python -m pip install -r requirements-desktop.txt
.venv/bin/python app_desktop.py
```

YouTube production keeps its existing command and channel-specific behavior:

```bash
python3 -m tools.ytbot run --channel fallem-prince --count 1
python3 -m tools.ytbot catalog --channel whispers-from-heaven
python3 -m tools.ytbot check "An exact topic" --channel zaflas
```

A channel is always explicit. Uploads remain scheduled, never immediately public, with
the existing 00:00/12:00 slots, audience policy, thumbnail and end-screen elements.
Read [the full pipeline](tools/ytbot/README.md) before running real production.

## Accounts, channels and video history

Click **Contas e canais do YouTube** in the existing video studio, or run:

```bash
python3 -m tools.ytbot accounts ui
python3 -m tools.ytbot accounts add --id work --label "Work account"
python3 -m tools.ytbot accounts connect --account work
python3 -m tools.ytbot accounts bind --account work --channel fallem-prince --verify-browser
python3 -m tools.ytbot run --channel fallem-prince --account work --count 1
```

Sign in yourself in the visible dedicated browser, then close that browser before
starting a batch. Each account has a private separate profile. The window groups channels,
video titles, schedules and run history without renaming original media or rewriting the
pipeline. A selected channel must match its actual YouTube ID; a matching name is not enough.
Optional read-only OAuth discovers channel identity using a Google Desktop client and
system-browser consent with PKCE/state. It does not replace the existing Studio uploader.
See [account setup](docs/ACCOUNTS.md).

## ZaturoBot service and private migration

`python3 -m tools.ytbot.service capabilities` exposes the bounded local adapter.
Reads return channel profiles and local run summaries. Explicit scheduled-batch requests
are durable/idempotent jobs; acceptance is not completion. Status polling reports actual
completion/evidence or uncertainty without repeating an unknown upload. No raw shell,
Google token or browser cookie is exposed. See [service contracts](docs/SERVICE.md).

Private `.local/` state and ignored media must travel encrypted outside Git. Preserve
original files, keep account/browser state private and reauthenticate on the destination
when the OS keyring differs. Rebuild dependencies/model caches rather than copying a
virtualenv. See [migration](docs/MIGRATION.md).

## Verify

```bash
npm ci
npm run verify
```

This runs strict extension lint, Python compilation, existing/new Node and Python tests,
both extension packaging checks and a Git-visible private-path/key guard. Tests use fake
accounts and never publish videos or contact live Google services. GPU/model/physical
Google sign-in acceptance is separate from hermetic tests. See [verification](docs/VERIFICATION.md).


ZaturoBot can also request generation-only batches through the fixed service CLI. The
actor verifies the dedicated Google/ChatGPT sessions before work and returns precise
bounded readiness errors. Generation does not upload or schedule. See
[service contracts](docs/SERVICE.md); existing extension/studio/upload commands are unchanged.
