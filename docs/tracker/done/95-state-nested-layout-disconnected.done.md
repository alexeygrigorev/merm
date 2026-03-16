# Issue 95: Nested state diagram layout is disconnected

## Problem

State diagrams with nested composite states have a disconnected layout. The outer states (e.g., Stopped) appear in a separate column from the composite state (Active), and edges between outer and inner states do not connect properly. Edge labels ("stop", "resume", "pause") overlap with each other.

### Current behavior (verified via PNG)

- The start circle and the "stop" label edge are in the left column. The Active composite box (containing Running and Paused) is in the right column. They appear side by side with no connecting path between them.
- The edge from Active to Stopped (labeled "stop") appears to originate from the start circle area, not from the Active box.
- Inside Active, the "resume" and "pause" labels between Running and Paused overlap each other (they are both rendered at nearly the same position between the two nodes).

### Reproduction fixture

`tests/fixtures/corpus/state/nested.mmd`

## Scope

This issue covers:
1. Fixing layout so that the composite state (Active) is placed inline with the outer flow, not in a disconnected column
2. Ensuring edges from outer states to/from composite states connect visually to the composite box boundary
3. Fixing edge label overlap for bidirectional edges inside composite states (pause/resume)

This issue does NOT cover:
- Fork/join bar rendering (covered by issue 94)
- General edge label overlap improvements outside state diagrams (already done in issues 28, 43, 53)

## Dependencies

- None (independent of issue 94)

## Acceptance Criteria

- [ ] The composite state "Active" is placed in the same visual flow as outer states (start -> Active -> Stopped -> end), not in a separate column
- [ ] The edge from start to Active connects visually to the Active composite box
- [ ] The edge from Active to Stopped (labeled "stop") originates from the Active composite box boundary
- [ ] The edge from Stopped to end connects properly
- [ ] Inside Active, the "pause" and "resume" labels do not overlap -- they must be visually distinguishable
- [ ] Inside Active, edges between Running and Paused are clearly routed (not on top of each other)
- [ ] Render `nested.mmd` to PNG with cairosvg and visually verify: (a) connected flow from start through Active to Stopped to end, (b) "pause" and "resume" labels are both readable and non-overlapping, (c) composite box contains Running and Paused properly
- [ ] Existing state diagram tests continue to pass (`uv run pytest tests/ -k state`)
- [ ] Other composite state fixtures (if any) still render correctly

## Test Scenarios

### Unit: Layout connectivity
- Render `nested.mmd` and verify that the Active composite state has edges connecting to it from the outer start state
- Verify that the Active composite state has an edge to Stopped
- Verify Stopped has an edge to the outer end state

### Unit: Composite state placement
- Parse and layout `nested.mmd`, check that the Active composite box x-coordinate overlaps with (or is close to) the outer state x-coordinates -- i.e., they are in the same visual column, not displaced to a separate column

### Unit: Edge label non-overlap
- Render `nested.mmd` to SVG, extract the "pause" and "resume" label positions
- Verify the label positions differ by at least 15px in either x or y (they are not overlapping)

### Integration: Full diagram connectivity
- Render `nested.mmd` to SVG and verify all expected edges are present: start->Active (or start->Running), Active->Stopped (with "stop" label), Stopped->end, Running->Paused (with "pause" label), Paused->Running (with "resume" label)

### Visual: PNG verification
- Render `nested.mmd` to PNG via cairosvg at scale=2
- Verify the diagram shows a connected flow (not two disconnected columns)
- Verify "pause" and "resume" labels are both visible and readable (not overlapping)
- Verify the Active composite box visually contains Running and Paused
- Verify no text clipping or elements outside the viewport
