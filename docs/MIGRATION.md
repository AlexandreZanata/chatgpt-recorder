# Private work-PC migration

The source checkout is public code; browser profiles, credentials, downloaded/generated
media and `.local` history are private. They must be sent through the authenticated
encrypted ZaturoBot file relay, never GitHub or an issue/log attachment. Preserve the
original checkout and every original local file throughout migration.

Restore meaningful `.local/bot`, `.local/ytbot`, user media folders and private workflow
records from a verified manifest. Source overlays and old helper scripts belong in a
separate recovery/quarantine folder; do not overwrite improved Git source with an older
uncommitted file. The local account fast-path fix and generic thumbnail recovery guidance
are already included in this version. Preserve conflicts for review rather than replacing
existing work-PC files, account keys or journals.

Do not copy `.git`, node_modules, virtualenvs, compiled Python caches or downloaded model
caches as if they were portable installations. Rebuild dependencies with `npm ci`, a new
venv and the existing model/narration setup. The supplied voice/background assets remain
in Git. Generated/user-owned audio, images, videos, run records and browser state travel
privately. The source data is not deleted after upload.

A live browser-profile copy is a best-effort snapshot, not a quiesced database backup;
Chrome may write or remove transient cache files during capture. Report exactly which
entries could not be copied and keep source data. Never kill the owner's original browser
just to silence an archival error. Existing Cookies/Local State can be tied to the source
OS keyring and may require fresh interactive Google/ChatGPT login on the destination.

New public code derives project paths from its own module location, normal Chrome paths
from `Path.home()` and runtime paths from the actual user ID/environment. Use the new
`python -m tools.ytbot` CLI rather than executing historical copied `.local/bot` helper
scripts with old absolute paths. `accounts connect` updates only the bot download
preferences; extension registration belongs to Chrome and is not overwritten.
Never globally replace path strings inside cookies/token databases or historical evidence.

This unkeyed Chrome build gets its ID from its absolute installation directory.
[The assisted installer](INSTALL-LINUX.md) loads `dist/chrome` automatically in a managed
browser. Existing system-browser profiles are preserved separately when opting into that
browser; its first use requires fresh sign-in. For manual system-browser setup, load the
current `dist/chrome` folder in each dedicated account profile after moving to a new PC.
The bot derives that local ID rather than reusing the source PC's extension ID.

An existing X11 socket alone does not prove that the hidden display is running; the
runtime checks the local connection. Browser shutdown preserves profile lock files if
the dedicated session cannot be stopped, including when Chrome rewrites its arguments.

After restoration, use the current work-PC ZaturoBot enrollment; do not replace its keys,
identity or execution journal. Confirm the source revision, private directory/file modes,
manifest hashes, profile/run listing and account-manager window before any live generation.
Google consent and actual channel identity must be checked interactively before uploads.
