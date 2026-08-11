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
