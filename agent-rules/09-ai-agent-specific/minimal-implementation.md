---
id: ai.minimal
triggers:
  - ponytail
  - yagni
  - minimal
  - simplify
  - over-engineering
  - delete
  - reuse
  - stdlib
alwaysApply: false
---
# Minimal Implementation (Ponytail)

> Inspired by [Ponytail](https://github.com/DietrichGebert/ponytail) (MIT) — static harness rule.  
> Cursor: `.cursor/rules/ponytail.mdc` applies always. Load this file for refactor/review tasks.

## Decision ladder

Stop at the first rung that holds:

| # | Rung | Action |
|---|------|--------|
| 1 | Need exists? | If no → skip (YAGNI) |
| 2 | In codebase? | Reuse existing helper/pattern |
| 3 | Stdlib? | Use standard library |
| 4 | Native platform? | Use built-in feature (`<input type="date">`, etc.) |
| 5 | Installed dep? | Use existing dependency |
| 6 | One line? | One line |
| 7 | Else | Minimum that works |

Climb **after** reading affected code and tracing real flow.

## Agent MUST

- Prefer deletion over addition.
- Fix root cause at shared function — not symptom at one caller.
- Ask when request sounds over-engineered.
- Use `ponytail:` comment on intentional shortcuts (name ceiling + upgrade).

## Agent NEVER

- Add dependency for one-liner stdlib/native solution.
- Skip trust-boundary validation, authz, or error handling for data loss.
- Golf code below harness security or domain invariants.
- Replace harness TDD gates with "one assert only" on domain/business logic.

## Review prompts

- Can this file be deleted instead of extended?
- Is there an existing util doing 80% of this?
- Would a native/HTML/stdlib API replace a component?

## Harness precedence

`AGENT-CORE-PRINCIPLES.md`, OWASP rules, and TDD pyramid **override** Ponytail when they require more structure (layers, tests, security).
