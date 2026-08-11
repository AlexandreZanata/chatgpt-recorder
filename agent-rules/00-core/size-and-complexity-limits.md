---
id: core.size-complexity
triggers:
  - size
  - complexity
  - cyclomatic
  - function
  - file
  - lint
  - typecheck
  - lines
alwaysApply: false
---
# Size and Complexity Limits (Universal)

> **Required on every project, every language.** Hard caps — never exceed.
> Full reference: this file is always loaded. Detail: `01-clean-code/functions.md`, `01-clean-code/complexity.md`.

## Hard caps (never exceed)

| Scope | Hard cap | Count |
|-------|----------|-------|
| **Function / method** | **80 lines** | Non-blank lines in body (exclude signature-only wrappers if language splits declaration) |
| **File / module** | **200 lines** | Total lines including imports and exports |
| **Cyclomatic complexity** | **10 per function** | Every branch path (`if`, `else`, `switch` case, `catch`, `&&`, `\|\|`, `?:`, loop) |

Applies to: TypeScript, JavaScript, Python, Java, Kotlin, Go, Rust, C#, PHP, Ruby, Scala, Swift, and any other language in the repo.

## Verification is mandatory

Before claiming work is done, the agent **MUST** verify changed code against these caps:

1. **Run project tooling** when present — typecheck, lint, complexity plugins (e.g. ESLint `complexity`, Pylint, `gocyclo`, Sonar, Biome).
2. **Self-check** when no tool is configured — count lines and estimate branches on every new or edited function.
3. **Fail the change** if any cap is exceeded — split or extract **in the same PR**, not "later".

## Agent MUST

- Split functions approaching 80 lines **before** submitting.
- Split files approaching 200 lines by responsibility (see `01-clean-code/classes-and-modules.md`).
- Refactor when cyclomatic complexity reaches **8** — treat **10** as a build-breaking ceiling.
- Configure or recommend linter rules matching these caps when bootstrapping a new project.

## Agent NEVER

- Submit a function > 80 lines or file > 200 lines without explicit user waiver.
- Add nested branches to stay under line count — extract instead.
- Skip verification because "this language doesn't have a linter" — manual count is required.
- Use generated/boilerplate blocks to evade limits without user request.

## When limits conflict with harness architecture

Domain richness and security rules still apply. If a use case truly needs more structure:

1. **ASK** the user before exceeding caps.
2. Prefer **more files** over **larger files**.
3. Prefer **more small functions** over **one large function**.

## Quick self-check (any language)

```text
function lines  = count from opening brace/body to closing (or logical equivalent)
file lines      = wc -l on the file
cyclomatic      = 1 + branches + loops + catch + boolean short-circuit paths
```

If any metric fails → refactor before commit.
