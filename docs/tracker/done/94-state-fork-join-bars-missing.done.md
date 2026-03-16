# Issue 94: State diagram fork/join bars missing

## Problem

State diagrams with composite states that have parallel entry (`[*] --> TaskA` and `[*] --> TaskB` inside a substate) should render fork/join bars (thick horizontal bars) to visually represent the parallel split and merge. Currently these are rendered as regular start/end markers (filled circles and bull's-eye circles) without fork/join bars.

Additionally, the composite state "Processing" appears visually disconnected from the outer flow (Ready and Done are in a separate column with no visible edge connecting to the Processing box).

### Current behavior (verified via PNG)

- Inside "Processing", two separate start circles lead to TaskA and TaskB, and two separate end circles appear below them. There are no fork or join bars.
- The outer flow (start -> Ready -> Done -> end) is in the left column. The Processing composite box is in the right column. The edge from Ready to Processing does not visually connect to the Processing box.

### Reproduction fixture

`tests/fixtures/corpus/state/fork_join.mmd`

## Scope

This issue covers:
1. Detecting parallel entry/exit patterns inside composite states (multiple `[*] --> X` transitions = fork, multiple `X --> [*]` transitions = join)
2. Generating fork/join bar pseudo-states in the IR when these patterns are detected
3. Rendering fork/join bars as thick horizontal black bars (the renderer `_render_fork_join_state` already exists but is never triggered for this case)
4. Connecting outer edges (Ready -> Processing, Processing -> Done) so the composite state is part of the main flow visually

This issue does NOT cover:
- General nested state layout improvements (covered by issue 95)
- Explicit `<<fork>>`/`<<join>>` pseudo-state syntax (already supported by the parser)

## Dependencies

- None (all prerequisites are done)

## Acceptance Criteria

- [ ] When a composite state has 2+ `[*] --> X` transitions inside it, a fork bar (StateType.FORK) is generated instead of multiple separate start circles
- [ ] When a composite state has 2+ `X --> [*]` transitions inside it, a join bar (StateType.JOIN) is generated instead of multiple separate end circles
- [ ] Fork bars render as thick horizontal black bars (using existing `_render_fork_join_state`)
- [ ] Join bars render as thick horizontal black bars
- [ ] The fork bar has edges fanning out to each parallel child state (TaskA, TaskB)
- [ ] The join bar has edges converging from each parallel child state
- [ ] The outer flow edge from Ready to Processing visually connects to the composite state box
- [ ] The outer flow edge from Processing to Done visually connects from the composite state box
- [ ] `tests/fixtures/corpus/state/fork_join.mmd` renders with fork/join bars visible in PNG output
- [ ] Render `fork_join.mmd` to PNG with cairosvg and visually verify: (a) fork bar visible as thick black horizontal bar with edges fanning to TaskA and TaskB, (b) join bar visible with edges converging from TaskA and TaskB, (c) outer flow is connected through the composite state
- [ ] Existing state diagram tests continue to pass (`uv run pytest tests/ -k state`)
- [ ] Explicit `<<fork>>`/`<<join>>` syntax still works (no regression)

## Test Scenarios

### Unit: Fork detection in composite states
- Parse `fork_join.mmd` and verify a FORK state is generated inside Processing when there are 2+ `[*] --> X` transitions
- Parse a composite state with only 1 `[*] --> X` transition and verify NO fork bar is generated (regular start circle)
- Parse a composite state with 3 `[*] --> X` transitions and verify a fork bar is generated

### Unit: Join detection in composite states
- Parse `fork_join.mmd` and verify a JOIN state is generated inside Processing when there are 2+ `X --> [*]` transitions
- Parse a composite state with only 1 `X --> [*]` transition and verify NO join bar is generated (regular end circle)

### Unit: Fork/join bar transitions
- Verify the fork bar has outgoing transitions to each parallel child (TaskA, TaskB)
- Verify the join bar has incoming transitions from each parallel child

### Integration: Outer flow connectivity
- Render `fork_join.mmd` to SVG and verify edges exist connecting Ready to the Processing composite state boundary
- Verify edges exist connecting the Processing composite state boundary to Done

### Visual: PNG verification
- Render `fork_join.mmd` to PNG via cairosvg at scale=2
- Verify fork bar is visible as a thick horizontal black bar inside the Processing box
- Verify join bar is visible as a thick horizontal black bar inside the Processing box
- Verify the outer flow (start -> Ready -> Processing -> Done -> end) forms a connected path
- Verify no overlapping elements or clipped text
