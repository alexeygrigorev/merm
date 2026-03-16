# Issue 82: Test quality audit — review all existing tests

## Problem

Our test suite has ~2400 tests but repeatedly failed to catch critical visual bugs:
- Arrow markers had wrong `refX` (arrowheads invisible/detached) — no test caught it
- Sequence diagram markers were reduced to 4x3 (barely visible) — no test caught it
- Multiple "fixes" were committed that actually broke rendering — tests passed anyway
- Some tests were actively asserting **wrong behavior** (e.g., `refX=0` was tested as correct when it's the bug)

These tests were written by an untrusted contributor and need thorough review.

## Scope

1. **Audit all rendering tests** — check that they test actual visual correctness, not just "does the code produce the same broken output"
2. **Identify tests asserting wrong behavior** — tests that lock in bugs instead of catching them
3. **Check test coverage gaps** — identify what visual properties are NOT tested
4. **Run mutation testing** — verify tests actually catch regressions when code is mutated
5. **Add missing structural tests** for:
   - Marker refX/refY must match polygon geometry (tip at path endpoint)
   - Marker dimensions must be adequate (>= 6x6 for visibility)
   - Edge paths must reach node boundaries (within marker length)
   - Font sizes must be consistent across diagram types
   - SVG viewBox dimensions must be reasonable
6. **Remove or fix bad tests** that assert implementation details rather than correctness

## Acceptance criteria

- Every rendering test must test a correctness property, not just "output matches snapshot"
- Mutation testing confirms tests catch at least 80% of marker/edge mutations
- No test asserts `refX=0` for arrow markers or other known-wrong values
- Visual regression tests render to PNG and validate key properties
