# AGENTS.md — professional-pdf-generator

> **Read this first** in any new agent session (Cursor, Claude Code, Codex, etc.).

**Language:** 100% English — code, comments, docs, commits, and all agent output.

---

## What this repo is

Secure Document Vault (v2): FastAPI + WeasyPrint PDFs, encrypted SQLite vault,
session + TOTP, optional PAdES. Agent Harness + Lefthook quality gates.

| Is | Is not |
|----|--------|
| Agent Harness rules + Cursor entry points | Permission to skip hooks |
| Lefthook quality gates (local commit block) | Place to commit `.local/` plans |
| Gitignored `.local/` task workspace | License to tick release DoD without evidence |

**v2 docs (read these):** [docs/HANDOVER.md](docs/HANDOVER.md) ·
[docs/OPEN-ITEMS.md](docs/OPEN-ITEMS.md) · [docs/RELEASE-NOTES-v2.md](docs/RELEASE-NOTES-v2.md) ·
[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

**Current phase:** see `.local/README.md` (gitignored). Do not tag `v2.0.0` while
OPEN-ITEMS blockers remain.

---

## YouTube automation bot (`tools/ytbot`)

Local, hidden pipeline for the **fallem prince** channel. It generates the article
in the Simple Deep Dive GPT, captures Read aloud audio, generates metadata and the
Black Ink Void thumbnail, renders the video (Fallem Prince background, no music,
quick outro, subtitles), uploads a draft, adds the Subscribe + Best for viewer end
screen and **schedules** it. It never publishes immediately and never opens
windows in the main desktop workspace.

**Single command**

```bash
python3 -m tools.ytbot run --count N
```

Rules enforced by code:

- 2 videos/day at **00:00** and **12:00**, 12 hours apart.
- If one slot is already scheduled that day, use the missing slot; if both are
  taken, move to the next day. Existing slots come from YouTube Studio
  `list_creator_videos`; start at least 60 minutes in the future.
- Always **"not made for kids"**.
- Description follows the existing channel format: paragraphs, hashtags, then the
  `TAGS:` line. Tags also go in the tags field, comma separated and within the
  YouTube character budget.
- Never add em dash (`—`) or en dash (`–`) to topics, titles, descriptions, tags
  or article text.
- End screen always includes **Inscrever-se** and a Video element set to
  **Melhor para o espectador** (YouTube chooses the best video).
- Every stage is recorded in `.local/ytbot/records/records.jsonl`,
  `.local/ytbot/records/RECORDS.md` and `.local/ytbot/runs/<slug>/record.json`.

Runtime and data:

- Hidden Chrome runs on Xvfb `:99`, CDP port `9300`, using the already signed-in
  profile at `.local/bot/profile` (gitignored). Do not touch the normal Chrome
  profile.
- `python3 -m tools.ytbot setup` prepares/uses the profile.
- Topic queue: `.local/ytbot/topics.txt`. If it has fewer topics than `--count`,
  the bot asks ChatGPT for new topics and filters them against the catalog.
- Catalog: `.local/ytbot/catalog.json` (refresh with
  `python3 -m tools.ytbot catalog`); duplicate check:
  `python3 -m tools.ytbot check "topic"`.
- Speed: article generation is sequential (concurrency 4 produced short
  articles below 35 minutes); audio capture is serialized; metadata/thumbnail
  run in parallel; rendering and uploads stay serialized. Use
  `--parallel 4 --upload-cdp <port>` when the signed-in main profile is running
  on Xvfb.
- Full process map: `tools/ytbot/README.md`.

If an upload opens the Google account chooser, the bot profile session expired:
sign in once in `.local/bot/profile`, or finish the uploads with the already
signed-in main Chrome profile launched on Xvfb. Do not use the main profile while
the normal Chrome is open.

Agent workflow for **"faça N vídeos e poste"**:

1. Run the command detached:
   `setsid python3 -m tools.ytbot run --count N > /tmp/ytbot-run.log 2>&1 < /dev/null &`
2. Poll the log and `.local/ytbot/records/records.jsonl`.
3. Intervene only if the process exits non-zero or a stage is recorded as
   `error`. Completed stages are resumable.
4. Report the final summary and scheduled slots. Do not publish manually.

Verification: `python3 -m unittest tests.test_ytbot_logic` and the size/complexity
gate on the new files.

When rules conflict with existing code, **rules prevail** — unless the user explicitly overrides for a task.

---

## Rules path (resolve first)

```bash
pip install -r agent-harness/requirements.txt   # once per machine
./agent-harness/rules-path.sh                   # → agent-rules/
./agent-harness/resolve-rules.sh <keywords>
```

Config: `agent-harness/harness.config.yaml` → `rules_dir: agent-rules`.

### Always load (base context)

1. `agent-rules/AGENT-CORE-PRINCIPLES.md`
2. `agent-rules/00-core/size-and-complexity-limits.md` — **80 lines/function, 200 lines/file, cyclomatic ≤10**
3. `agent-rules/04-testing/contract-first-tests.md` — before ANY test
4. `agent-rules/09-ai-agent-specific/token-economy.md`
5. `agent-rules/09-ai-agent-specific/anti-hallucination.md`

Cursor: `.cursor/rules/*.mdc` applies automatically (incl. Ponytail YAGNI + `quality-gates.mdc`).

### Conditional load

```bash
./agent-harness/resolve-rules.sh <keywords from task>
./agent-harness/generate-task-rules.sh <keywords>
./agent-harness/generate-task-rules.sh --clean
```

Load **2–6** task files only — not the entire tree.

---

## Quality gates (Lefthook — blocks commit)

Every commit (local included) MUST pass:

| Gate | Cap |
|------|-----|
| File lines | ≤ **200** |
| Function / method lines | ≤ **80** |
| Cyclomatic complexity | ≤ **10** |
| Lint | **0 errors, 0 warnings** |
| Compile / system check | **0 errors** when tooling exists |

```bash
lefthook install            # wire git hooks (CLI on PATH)
npm run verify              # run all gates manually
npm run hooks:install       # same as lefthook install
```

Details: [docs/QUALITY-GATES.md](docs/QUALITY-GATES.md).

**Never** use `--no-verify` unless the user explicitly asks.

---

## Local workspace (gitignored)

Implementation plans live in `.local/` and **must not** be committed.

| Path | Purpose |
|------|---------|
| `.local/README.md` | Index of phases |
| `.local/IMPLEMENTATION-PLAN.md` | Master roadmap |
| `.local/phases/<id>/` | Per-task: `README.md`, `TASKS.md`, `OFFICIAL-REFERENCE.md` |
| `.local/reference/` | Cached official links for agents |
| `.local/overrides/` | Optional local rule overrides |
| `.local/tmp/` | Scratch notes |

Pattern: small steps + validation commands in `TASKS.md`; cite official URLs in `OFFICIAL-REFERENCE.md`.

---

## Before coding

1. Read [docs/OPEN-ITEMS.md](docs/OPEN-ITEMS.md) and the current `.local/phases/*` README.
2. Complete [docs/NEW-PROJECT-CHECKLIST.md](docs/NEW-PROJECT-CHECKLIST.md) when starting greenfield work.
3. Resolve harness rules for the task keywords (`./agent-harness/resolve-rules.sh …`).
4. Implement in small steps; run `npm run verify` after each block.
5. Release gate evidence lives under `docs/evidence/release-v2/`.
