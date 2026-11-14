# Accounts and channels

The manager is an additive window in the existing Python video app. Open it with the
**Contas e canais do YouTube** button or `python3 -m tools.ytbot accounts ui`.
The existing video-generation controls and upload pipeline are retained.

## Browser connection

Create a short lowercase account ID and label. Click **Abrir janela para conectar
Google / Studio**. This opens ordinary Chrome/Chromium using only that dedicated profile.
Complete Google and, for article/audio generation, ChatGPT sign-in yourself. Close the
browser window before running a batch. The account lock prevents a new managed batch
from competing with interactive sign-in. No passwords, challenge bypass or embedded
Google webview are implemented.

Select a channel profile and click **Usar esta conta no perfil escolhido**. Without OAuth,
the manager starts a separate verification command, observes the actual Studio channel
ID and saves the binding only after it matches the selected profile. It never uploads
a video during connection/verification. A same-name channel with a different ID is refused.
If login has expired or the channel is inaccessible, sign in to the correct account;
the previous binding is preserved. The default `legacy` session remains available.

```bash
python3 -m tools.ytbot accounts list
python3 -m tools.ytbot accounts add --id work --label "Work account"
python3 -m tools.ytbot accounts connect --account work
python3 -m tools.ytbot accounts bind --account work --channel zaflas --verify-browser
python3 -m tools.ytbot run --channel zaflas --account work --count 1
```

The channel binding supplies the default account. `run --account` chooses one explicitly.
Per-channel prompts/media settings/data stay in their existing locations; switching an
account does not rewrite titles, channel IDs, narration, video quality or schedules.
The UI reads original run metadata and shows title, state, slot and video ID.

## Optional API connection

Google OAuth is optional for account/channel discovery, not the existing browser uploader.
Create a Desktop OAuth client in your own Google Cloud project, enable YouTube Data API
and save its JSON outside Git with mode 0600. The manager's optional API button opens the
system browser for Google consent. It uses `youtube.readonly`, random state, PKCE S256,
a loopback-only ephemeral callback and a three-minute deadline. No upload permission is
requested. `channels.list(mine=true)` returns the channels accessible to that particular
consent; it is not a promise to enumerate every Brand Account. Authorize the intended
Brand Account separately when required by Google's account selection/permissions.

```bash
chmod 600 /private/path/google-desktop-client.json
python3 -m tools.ytbot accounts oauth --account work --client /private/path/google-desktop-client.json
python3 -m tools.ytbot accounts bind --account work --channel zaflas --channel-id UCi2aftoK7vlS3A6OozMHXKg
```

API consent and the browser's Studio session are separate. Connecting one does not claim
the other is logged in. Actual channel ID is checked again before upload. OAuth tokens
and client settings are private 0600 files; no token is returned by the service API.
Disconnect/revoke API access through your Google account when desired; removing a local
profile is never an automatic cleanup action. Existing browser profiles/media are preserved.

## Private layout and limits

- `.local/accounts/registry.json`: account labels, allocated CDP ports, explicit channel bindings.
- `.local/accounts/browser/<account-id>/`: dedicated browser profile, mode 0700.
- `.local/accounts/oauth/<account-id>.json`: optional tokens/client settings, mode 0600.
- `.local/accounts/locks/`: mutual exclusion for interactive access and batches.
- Legacy profile: `.local/bot/profile` when present, otherwise `.local/ytbot/profile`.

Up to 20 new accounts use separate allocated loopback CDP ports (9301–9320); legacy stays
9300. Process selection matches exact profile arguments. A debug port belonging to a
different browser profile is refused; the manager never reuses that session silently.
The normal Chrome directory is not opened or stopped by managed sign-in. Existing legacy
setup behavior is retained, but new accounts start clean rather than copying normal cookies.

References: [Google desktop OAuth](https://developers.google.com/identity/protocols/oauth2/native-app),
[YouTube authentication](https://developers.google.com/youtube/v3/guides/authentication),
[channel listing](https://developers.google.com/youtube/v3/docs/channels/list).
