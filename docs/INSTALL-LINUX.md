# Assisted Linux installation

For Ubuntu/Debian on x86_64, download or clone this repository into a permanent folder,
open a terminal in that folder, and run as the desktop owner (not with `sudo`):

```bash
bash scripts/install-linux.sh
```

The installer requests administrator access only for missing Linux packages, creates or
reuses `.venv`, keeps compatible existing CPU/CUDA PyTorch, installs the desktop requirements,
builds the Chrome extension without Node, downloads official Stable **Chrome for Testing**,
checks that it can start with its sandbox enabled, and adds **YoutubeBot · Contas e configuração**
to the application menu. A new installation gets a `work` account; existing accounts,
channel bindings, private browser profiles and media are preserved. It never starts a video batch.

Use `--no-open` for setup without opening the account window. Use `--skip-system-deps` only
when the OS packages are already installed. Python 3.11+ and an Internet connection are required.
The script installs the tested desktop dependencies; optional generation models and GPU engines
still use their existing setup. Allow several GB for Python/media dependencies and downloads.

## Connect once on this computer

1. Select or add an account in **Contas e canais do YouTube**.
2. Click **Conectar Google / YouTube e ChatGPT**. Both sites open in the same dedicated
   browser window. Complete sign-in yourself, including any Google challenges.
3. Choose the intended YouTube/Brand Account. Click **Concluir login** in the account
   manager or close the browser window when finished. This saves and closes only that session.
4. Select the channel profile, then **Usar esta conta no perfil escolhido**. The bot checks
   the actual channel ID before saving the binding; a matching name is insufficient.
5. Click **Verificar conexão completa**. Channel, capture extension and ChatGPT should each
   show `OK`. These checks do not generate content or upload a video.

The managed browser loads `dist/chrome` automatically on every launch. There is no folder
picker and no need to install the Firefox project root as a Chrome extension. It keeps
working after closing and reopening the browser. Account logins stay in that account's
private profile. Existing named accounts switch to a separate managed profile when
**Conectar** is clicked; the old system-browser profile is kept. This first switch requires
a fresh login. The `legacy` account stays unchanged; add a named account for automatic
setup. The owner's normal Chrome profile is not opened or stopped.

Command-line equivalent for the final check:

```bash
.venv/bin/python -m tools.ytbot accounts check --account work --channel fallem-prince
```

## Reinstall, update or use another computer

Rerun the same installer after updating the source. It reuses an already downloaded current
browser and does not recreate the account registry. Chrome for Testing does not auto-update:
rerun the installer periodically to obtain the current Stable version. Older downloaded
versions remain available for deliberate recovery; accounts are never downgraded automatically.
A profile created by a newer Chrome version is refused until the managed browser is updated.

On a different computer, sign in again. OS keyrings, device checks and expired sessions mean
that copying cookies cannot guarantee a logged-in account. Never put browser profiles,
passwords or tokens into GitHub or an installation ZIP. For private media/account migration,
use [the encrypted migration guide](MIGRATION.md); build a fresh virtualenv on the new PC.
Moving the project changes its unkeyed extension ID; the bot derives the current ID from the
canonical extension path. Rebuild and rerun the installer after moving the source folder.

## Troubleshooting

- **Sandbox check fails on Ubuntu:** install the official Google Chrome `.deb` from
  [Google](https://www.google.com/chrome/) using the normal package installer, then rerun
  this script. Ubuntu may restrict user namespaces for the downloaded testing browser.
  YoutubeBot can reuse the package's root-owned `4755` Chrome sandbox helper; it never uses
  `--no-sandbox`, disables AppArmor, or installs a custom privileged helper. Missing desktop
  libraries are another reason for startup failure; check OS dependencies first.
- **No graphical session:** run account connection from the owner's logged-in Linux desktop,
  not an SSH-only shell. Login is a normal visible browser session, with no automation flags.
- **Account busy:** finish its sign-in or running batch, close that browser, then retry.
  Do not delete Chrome's Singleton files while a browser is alive.
- **Wrong channel or expired login:** reopen **Conectar**, select the correct account/channel,
  close the browser and verify again. A failed binding preserves the previous binding.
- **Two capture extensions:** the Chrome build is `dist/chrome`; the project root is the
  Firefox build. Disable the accidental root copy. The installer never removes other extensions.
- **Manual system Chrome setup:** remains available without the managed installation; see
  [the extension guide](CHROME-EXTENSION.md). Recent branded Chrome versions do not support
  automatic `--load-extension`; use the managed browser to avoid the manual picker.

The browser is downloaded only from the official Google version index and Google storage,
with bounded archive extraction. It lives under ignored `.local/runtime/`; sign-in state
remains under ignored `.local/accounts/`. No account secrets are included in the launcher
or installation report.

References: [Chrome for Testing](https://developer.chrome.com/docs/automation-and-testing/chrome-for-testing),
[Chrome extension loading change](https://developer.chrome.com/blog/extension-news-june-2025),
[sandbox troubleshooting](https://pptr.dev/troubleshooting).
