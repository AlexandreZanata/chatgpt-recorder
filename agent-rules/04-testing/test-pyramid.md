---
id: test.pyramid
triggers:
  - test-pyramid
  - e2e
  - integration
  - unit-test
alwaysApply: false
---
# Test Pyramid

> **Prerequisite:** read `contract-first-tests.md` before adding any test.
> Agents over-generate E2E — enforce explicit ratio caps. **All layers run in CI.**

## Target ratio (automated)

```text
Unit:        75%  — domain entities, value objects, state machines, pure logic
Integration: 20%  — use cases + real adapter fakes/in-memory DB
E2E:          5%  — critical user journeys only
```

Every test type must be **automated** — no manual-only regression suites.

## What belongs where

| Layer | Test type | Examples | Automation |
|-------|-----------|----------|------------|
| Domain | Unit | `Order.submit()` raises on invalid state | `npm test`, `pytest`, `go test` |
| Application | Integration | `SubmitOrderHandler` persists + publishes event | CI job on every PR |
| Infrastructure | Integration | Repository round-trip with test DB | CI with test container |
| Full stack | E2E | Login → create resource → verify API response | CI (Playwright, Cypress, etc.) |

## E2E tasks

When a task or use case is marked **E2E-required**:

1. Read use case in `docs/use-cases/`
2. Read `contract-first-tests.md`
3. Write E2E asserting **journey outcome** (API response, visible state) — not implementation
4. Register in CI pipeline

## Caps

- **Max 1 E2E test per user story** unless compliance requires more.
- Do not write E2E when integration test suffices.
- Do not hit real external APIs in unit tests.

## Agent action

When asked to "add tests":

1. Load `contract-first-tests.md` first
2. Default to **unit** tests for domain changes
3. Add **integration** for use case wiring
4. Propose **E2E** only for new critical flows — always automated in CI
