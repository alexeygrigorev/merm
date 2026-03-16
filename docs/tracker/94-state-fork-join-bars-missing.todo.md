# Issue 94: State diagram fork/join bars missing

## Problem

State diagrams with composite states that have parallel entry (`[*] --> TaskA` and `[*] --> TaskB` inside a substate) should render fork/join bars (thick horizontal bars) to visually represent the parallel split and merge. Currently these are rendered as regular start/end markers without fork/join bars.

Also, the composite state "Processing" appears disconnected from the outer flow (Ready → Processing → Done).

Reproduction: `tests/fixtures/corpus/state/fork_join.mmd`

## Acceptance criteria

- Fork bars render as thick horizontal bars when a composite state has multiple parallel entries
- Join bars render when multiple parallel flows merge back
- Edges from outer states to composite states connect properly
- Existing tests must continue to pass
