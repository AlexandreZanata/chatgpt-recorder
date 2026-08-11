---
id: test.tdd
triggers:
  - tdd
  - test-first
  - given-when-then
alwaysApply: false
---
# TDD

> **Prerequisite:** read `contract-first-tests.md` before writing any test.

## Workflow

1. Read contract source (business rule, API contract, use case).
2. Write **failing** test expressing contract — not current code behavior.
3. Implement minimum code to pass.
4. Refactor with tests green.

## Test naming

```text
given_[context]_when_[action]_then_[outcome]
```

Example: `given_draftOrder_when_submit_then_statusIsSubmittedAndEventRaised`

## Domain first

- Business rules and state machines get unit tests **before** Application/Infrastructure wiring.
- One contract clause per test — fail for one reason.

## Agent rules

- NEVER skip tests for domain logic "to save time".
- NEVER change test expectations to match wrong implementation — see `contract-first-tests.md`.
- NEVER write tests by copying production logic.
- Run automated tests before claiming completion.
