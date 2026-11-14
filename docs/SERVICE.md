# ZaturoBot local service contract

Protocol `schema_version: 1`, invoked from the reviewed YoutubeBot root with a trusted
Python executable. No shell or JSON-generated command string is accepted. Read/admission
commands use the standard library; real production execution needs the original browser,
Playwright, renderer and media dependencies. Bind only inside the local worker boundary.
This CLI is not an unauthenticated HTTP service.

```bash
python3 -m tools.ytbot.service capabilities
python3 -m tools.ytbot.service profiles
python3 -m tools.ytbot.service runs --channel fallem-prince --limit 20
python3 -m tools.ytbot.service submit --operation-id CANONICAL-UUID \
  --channel fallem-prince --account legacy --count 1 --approved-schedule
python3 -m tools.ytbot.service status --operation-id CANONICAL-UUID
```

## Requests and output

`capabilities` returns service `youtube`, max_count 10 and fixed capability IDs
`youtube.profiles.list`, `youtube.runs.list`, `youtube.batch.submit`, `youtube.batch.status`.
`profiles` returns `profiles` with `id`, `name`, `channel_id`, `account_id`,
`browser_configured`. Configured browser data does not prove an unexpired Google login.
`runs` requires a known channel and limit 1–100; output contains `channel`, `runs`.
Each run has relative `id`, bounded `title`, `topic`, `state`, `slot`, `video_id` and
`artifacts` basenames. Original metadata/records remain authoritative.

Submission requires a canonical lowercase UUID, known channel, registered account,
count 1–10 and the explicit `--approved-schedule` flag. The worker must additionally
enforce its owner/task/config permission; a text instruction or model proposal is not
such a grant. Preserve the operation UUID on transport retries. Mutating operations are
not inferred from free text. Root process/provider/owner credentials must not be inherited
by the adapter. Its actor also strips TOKEN/PASSWORD/SECRET/API_KEY environment variables.

`submit` and `status` return only `schema_version`, `operation_id`, `state`, `channel`,
`account`, `count`, UTC Unix-second `created_at`/`updated_at`, bounded `summary`,
`error_code` and `result`. Result has `scheduled_count`, `failed_count`, and safe run
summaries. No raw Google token, cookie, account email, absolute file path, ChatGPT URL,
traceback or private provider error is serialized. Output is one JSON document capped
at 65,536 bytes. The caller must further bound results to its task/wire budget.
Rejected operations exit nonzero with `{ "schema_version": 1, "error": "operation_rejected" }`.
Host media capacity is one active job across all accounts/channels. A busy new operation
exits nonzero with `{ "schema_version": 1, "error": "capacity_reached" }`; it creates no
job or waiting unit. Count 1–10 remains a sequential batch in that one actor.

## Durable execution and notifications

States are `accepted`, `running`, `completed`, `failed`, `uncertain`.
Admission is fsynced before actor launch. Repeated operation + same typed request returns
the existing job; a different payload is a collision. A permanent execution marker fences
the same actor identity after a crash. A fsynced project-wide capacity reservation and
admission lock allow only one heavy actor on the 22 GB work PC. An existing operation
still returns its status idempotently. Capacity is reused only when its real PID/start
identity has exited and its systemd unit is positively inactive; an unavailable manager
fails closed. A delayed superseded launcher is fenced before importing the pipeline.
Account and channel locks prevent conflicting
browser/upload control. Completion requires new scheduled-video evidence for the requested
count; merely returning from the pipeline with no exception is insufficient.

An accepted batch has not finished. ZaturoBot must poll `status`, then append its durable
completion/failure event and notify the owner using only whitelisted summaries. The adapter
does not call the hub or receive hub credentials. Existing thumbnail/video files remain
local artifacts; an owner-authorized separate encrypted transfer may attach one to the feed.

Heavy actors run in separate fixed `systemd-run --user` units named from the operation
UUID. They never inherit the coordinator worker's small cgroup. Defaults for the 22 GB
work PC are MemoryHigh 12 GiB, MemoryMax 16 GiB, CPUQuota 200%, TasksMax 256 and a
12-hour RuntimeMaxSec, with no automatic restart and control-group cleanup. The unit
uses `env -i` plus a fixed path/locale/GUI/CUDA allowlist, preserving the configured Python
virtualenv path while excluding credentials even from the user manager environment.
Missing user systemd yields `failed` / `setup_unavailable` before a media actor is launched;
there is no fallback into the 512 MiB worker. An uncertain launch remains fenced. These
jobs run on the work PC, never the small VPS. Direct legacy `ytbot run` is unchanged.

The job records live at `.local/ytbot-service/jobs/`; private logs are capped at 10 MiB.
PID plus Linux process-start identity detects a lost actor without mistaking PID reuse
for liveness. Lost/unstarted actors become `uncertain`, retain admission evidence and
are never automatically re-executed. Reconcile existing run/upload records before a new
explicit operation. Do not delete a job/marker to force a retry of an unknown upload.
`_execute` is an internal fixed actor entry point, not a supported owner command.
