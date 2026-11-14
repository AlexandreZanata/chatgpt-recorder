# YoutubeBot agent guide

This is YoutubeBot: a Firefox/Chrome audio-capture extension, Python/PySide6 video
studio, and resumable Playwright YouTube production/scheduled-upload pipeline.
Read [the component map](docs/ARCHITECTURE.md), then only the relevant module and tests.
English in code, comments, documentation and commits; user-facing UI may use Portuguese.

## Preserve existing behavior

- Extension capture, filename templates and download behavior stay unchanged.
- Keep the existing generation modes, narration, voices, subtitles, backgrounds and rendering.
- `tools/ytbot` keeps channel prompts, deduplication, resumable stage records and sequential
  upload/scheduling. Existing profiles are `fallem-prince`, `whispers-from-heaven`, `zaflas`.
- Require an explicit channel. Verify its YouTube channel ID before mutating Studio.
- Schedule only: 00:00/12:00 slots in America/Cuiaba, at least 60 minutes ahead,
  not made for kids, custom thumbnail and Subscribe + Best for viewer end screen.
- Preserve channel-specific title/description/tags rules and media quality.
- Never blindly retry an uncertain upload or start the same service operation twice.

## Boundaries

Accounts, browser profiles, OAuth tokens, generated media, model caches and run history
are private `.local/` state. Never log tokens/cookies or put them in Git. Google sign-in
uses the owner's visible browser and consent; do not bypass challenges or copy another
profile while in use. Browser automation remains the upload path; optional OAuth only
helps discover and verify account/channel identity. Never silently switch channels.

The service CLI is typed and bounded. Never expose a general shell, arbitrary subprocess
arguments or account secrets to ZaturoBot. Real generation/upload/Google consent tests
are opt-in; CI uses fixtures. Read [accounts](docs/ACCOUNTS.md), [service](docs/SERVICE.md)
and [migration](docs/MIGRATION.md) for those operations.

## Verify and hand off

Use `npm ci`, then `npm run verify` (extension lint/build/package + Node/Python tests).
Keep tests behavioral. Run the smallest useful command during development and the complete
gate before publication. Report actual checks and remaining physical-account/GPU limits.
No harness, dynamic rule resolver or hook framework is required. Keep docs concise and
canonical: README for commands, architecture for ownership, topic docs for contracts.
Never delete the owner's original local media, browser state, credentials or unrelated repos.
