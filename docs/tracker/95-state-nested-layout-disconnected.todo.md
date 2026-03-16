# Issue 95: Nested state diagram layout is disconnected

## Problem

State diagrams with nested composite states have a disconnected layout. The outer states (e.g., Stopped) appear in a separate column from the composite state (Active), and edges between outer and inner states don't connect properly. Edge labels ("stop", "resume", "pause") overlap with each other.

Reproduction: `tests/fixtures/corpus/state/nested.mmd`

## Acceptance criteria

- Outer states and composite states should be connected in a coherent layout
- Edges between outer and composite states must be visible and properly routed
- Edge labels must not overlap each other
- Existing tests must continue to pass
