# Verification and preserved behavior

`npm run verify` is the single explicit quality command. It runs extension ESLint with
zero warnings, Python compilation, Node tests, Python unittest discovery, existing
Firefox/Chrome packaging and a Git-visible private-path/key check. Ignored credentials
are never opened by the publication check. Its heuristic is not a general secret audit.
No agent harness, rule generator, size-cap framework or Lefthook dependency remains.

The existing extension capture files, video engines, channel prompts, upload/schedule
implementation and pipeline algorithms are preserved. The existing video studio only
adds an account-management button. Runtime/account changes add portability, explicit
profile isolation and exact channel identity checks; ordinary existing `run` commands
retain the legacy account by default unless an explicit binding/account is selected.

Local verification passed the complete existing and new suites: 153 Python tests and
30 Node extension tests, strict extension lint and both distribution packages. New
behavioral tests cover independent accounts, private modes/symlinks, competing ownership,
exact channel ID, process-profile prefixes/CDP conflicts, existing preferences, title/run
index, OAuth PKCE/state/loopback/readonly scope, durable/concurrent idempotent submission,
permission denials, actual fake-actor lifecycle, missing scheduled evidence and lost-actor
uncertainty, bounded separate systemd units, clean actor environments and missing-manager
denial. Global media admission tests cover competing accounts/channels, terminal actors
still alive, missing manager evidence, upgrade reconciliation and a superseded late launcher.
OAuth tests use synthetic values and a loopback fixture; no Google account
or real upload is used. The account window was rendered offscreen with all three profiles; a Qt interaction
test verifies account creation, case-insensitive title search and read-only history.

Real acceptance still needs the owner to sign in on the work PC, optionally supply their
Google Desktop OAuth client, verify accessible channels and run an explicitly authorized
production batch with the target GPU/browser. Tests do not claim that a physical account
is connected or that a real video was published. Optional Qwen/GPU engines retain their
existing setup and model downloads; fixture checks do not validate their installed weights.

The CI installs the official CPU PyTorch wheel for the existing studio's eager torch
import; this is a test dependency, not a GPU/model substitution. The canonical scheduling
timezone is applied by CLI/service entry points and test execution, preserving Cuiaba
slots on a work PC whose OS timezone differs. The global OS timezone is never changed.
