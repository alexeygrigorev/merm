# 16 - State Diagram Support (Phase 3)

## Goal
Add support for state machine diagrams.

## Tasks

### Parser
- [ ] Parse `stateDiagram-v2` declaration
- [ ] Parse states: `s1: Description`
- [ ] Parse transitions: `s1 --> s2: event`
- [ ] Parse start/end: `[*] --> s1`, `s1 --> [*]`
- [ ] Parse composite states: `state "name" as s1 { ... }`
- [ ] Parse forks/joins: `state fork_state <<fork>>`
- [ ] Parse choice: `state choice_state <<choice>>`
- [ ] Parse notes: `note left of s1: text`
- [ ] Parse concurrency: `--`

### IR Extensions
- [ ] `State` with type enum (normal, start, end, fork, join, choice)
- [ ] `Transition` with event label

### Layout & Rendering
- [ ] Reuse Sugiyama layout
- [ ] Rounded rectangle states
- [ ] Filled circle for start, bull's eye for end
- [ ] Horizontal bar for fork/join
- [ ] Diamond for choice
- [ ] Composite state boxes (similar to subgraphs)

## Dependencies
- Phase 1 complete

## Estimated Complexity
Medium - similar to flowcharts with specialized node types.
