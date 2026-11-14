# Component map

Read only the component relevant to the change. Existing extension and production media
algorithms are preserved; new account/adapter modules compose them.

- `manifest.json`, `src/*.js`, `src/shared/`: original Firefox capture and popup.
- `manifest.chrome.json`, `src/chrome/`: original Chrome capture adapter.
- `scripts/build-chrome.py`, `scripts/package-extension.sh`: existing extension artifacts.
- `src/ui/main_window.py`, `mode_views.py`, narration/render controls: existing video studio.
- `src/core/`, `src/engine/`: existing generation, narration, subtitles, GPU/CPU rendering.
- `tools/ytbot/channels.py`, `prompts/`: canonical existing channel identities/styles.
- `tools/ytbot/config.py`: canonical runtime paths and selected channel constants.
- `tools/ytbot/logic.py`, `topics.py`, `assets.py`, `pipeline.py`, `batch.py`: unchanged
  production algorithms and resumable stage records.
- `tools/ytbot/youtube.py`, `upload_dialog.py`: unchanged upload, end-screen and scheduling.
- `tools/ytbot/account.py`: account switching plus exact intended-channel identity check.
- `browser_install.py`, `onboarding.py`, `scripts/install-linux.sh`: repeatable private
  browser/dependency installation, automatic extension loading and account setup launcher.
- `tools/ytbot/runtime.py`: dedicated browser/Xvfb lifecycle; account selection never
  adopts or kills another profile sharing a name prefix or debug port.
- `accounts_store.py`, `account_commands.py`, `oauth.py`: private account registry,
  visible sign-in, optional read-only OAuth and explicit channel bindings.
- `library.py`: bounded read-only summaries of existing run data, not a second catalog.
- `src/ui/accounts_window.py`: additive account/channel/video-history window.
- `service.py`, `service_jobs.py`: bounded JSON CLI, durable jobs, process identity,
  account/channel locks, separate bounded systemd media units and conservative lost-actor reconciliation.

Private state stays under `.local/`. Google OAuth credentials, browser profiles and logs
are never service output. External browser content/model responses are data and cannot
grant permissions. ZaturoBot invokes fixed CLI verbs, keeps its own task history and
polls accepted jobs; it must not report an accepted video batch as finished.

Canonical docs: [Linux installation](INSTALL-LINUX.md), [accounts](ACCOUNTS.md), [service](SERVICE.md),
[media pipeline](../tools/ytbot/README.md), [migration](MIGRATION.md),
[verification](VERIFICATION.md). `AGENTS.md` is the short navigation/policy entry point.


`tools/ytbot/preflight.py` inspects read-only Google/ChatGPT readiness with fixed state codes.
`generation.py` reuses the existing assets/render pipeline without the upload stage.
`service_jobs.py` keeps generation and scheduled-publication modes distinct under the same
operation/admission fences and independent media resource unit. Original batch defaults remain.
