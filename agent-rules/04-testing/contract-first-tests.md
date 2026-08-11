---
id: test.contract-first
triggers:
  - test
  - tests
  - unit
  - e2e
  - integration
  - contract
  - tdd
  - automated
  - regression
alwaysApply: false
---
# Contract-First Tests (Mandatory Before Any Test)

> **READ THIS FILE BEFORE WRITING, EDITING, OR DELETING ANY TEST.**
> Applies to unit, integration, E2E, and automated/CI tests — every language.

## Core law

A test is a **frozen logical contract**, not a mirror of the implementation.

| Test MUST | Test MUST NOT |
|-----------|---------------|
| Assert **observable behavior** from spec, API contract, or GIVEN/WHEN/THEN | Copy production logic into the test |
| **Fail** when code violates the contract | Be changed to match broken code |
| Encode **one business rule or error** per focused case | Pass because mock returns what code expects |
| Stay **immutable** unless the **contract** changes (user/product decision) | Be "fixed" to green a wrong implementation |

**If the test and the code disagree, the code is wrong — not the test** (unless the contract itself was wrong and was formally updated).

## Forbidden patterns (reject immediately)

- **Mirror test:** `expect(service.calculate(x)).toBe(sameFormulaAsProduction(x))` duplicated in test body.
- **Implementation coupling:** asserting private methods, internal state shape, or call order without contract need.
- **Assertion drift:** weakening expectations (`toBe(200)` → `toBeDefined()`) to make CI pass.
- **Snapshot of implementation:** golden files that only echo current output with no spec link.
- **Test that cannot fail:** no assertion, tautology, or always-true condition.

## Required patterns

### 1. Contract source (pick before writing)

Document in test name or comment (one line):

- Business rule: `GIVEN/WHEN/THEN` from domain doc
- API contract: `docs/API-CONTRACT.md` or OpenAPI response schema
- Error contract: status code + error code + message shape
- E2E journey: use case from `docs/use-cases/` — user-visible outcome only

### 2. One failure mode per test

Each test proves **one** contract clause. Name format:

```text
given_[context]_when_[action]_then_[outcome]
regression_[issueId]_given_[context]_when_[action]_then_[outcome]
contract_[resource]_when_[violation]_then_[error]
```

### 3. Test types (pyramid — all automated in CI)

| Type | Share | What it proves | Runs |
|------|-------|----------------|------|
| **Unit** | ~75% | Domain rules, VOs, state machines, pure logic | Every commit / CI |
| **Integration** | ~20% | Use cases + adapters (in-memory/fake DB) | Every commit / CI |
| **E2E** | ~5% | Critical user journeys end-to-end | CI + optional nightly |

**All three layers are automated.** No manual-only test suites for regressions.

### 4. E2E rules

- Max **1 E2E per user story** unless compliance requires more.
- Assert **user-visible or API contract outcomes** — not DOM implementation details.
- E2E must fail if the journey breaks — not if CSS class names change.

### 5. Changing a test

Allowed only when:

1. **Contract changed** — product/domain/API doc updated first.
2. Test updated to match **new** contract — in same PR as doc change.
3. PR description states: `Contract change: [what changed]`.

**NEVER** change test expectations because "implementation changed" without contract change.

## Agent protocol (before any test work)

```text
1. READ this file (contract-first-tests.md)
2. READ contract source (GIVEN/WHEN/THEN, API-CONTRACT, use case)
3. WRITE failing test for the contract clause
4. IMPLEMENT minimum code to satisfy contract
5. RUN full automated suite for touched layer (unit → integration → E2E if applicable)
6. NEVER weaken assertions to pass
```

## Agent MUST

- Run `resolve-rules.sh test contract` when task involves tests.
- Add **unit** tests for domain; **integration** for use cases; **E2E** only for new critical flows.
- Wire new tests into CI (project test command must include them).
- For bug fixes: failing regression test **before** fix (`regression-safety.md`).

## Agent NEVER

- Create tests without reading contract source.
- Align test expectations with current code output without spec.
- Skip automated run before claiming done.
- Delete failing contract tests — fix code or escalate contract change to user.

## Related rules

- `04-testing/test-pyramid.md` — ratios and layer placement
- `04-testing/tdd.md` — red-green-refactor workflow
- `04-testing/regression-safety.md` — bug fix tests
- `04-testing/coverage-gates.md` — thresholds
- `04-testing/mocking-boundaries.md` — what to mock
