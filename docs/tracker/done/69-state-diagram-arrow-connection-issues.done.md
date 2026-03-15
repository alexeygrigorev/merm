# Issue 69: State diagram arrows don't touch circles and arrowheads oversized

## Status: REOPENED — previous layout fix was correct but renderer shortening undoes it

## Problem

1. Arrows to/from `[*]` start/end circles have a visible gap
2. Arrowheads are oversized (same thick/heavy style as flowchart)

## Root Cause

Same as issue 67 — `_MARKER_SHORTEN = 8.0` in `edges.py` creates the gap. Fixing issue 67 will fix this too. State diagrams use the same marker system from `edges.py`.

## Acceptance Criteria

- [ ] **MANDATORY PNG CHECK**: Render the diagram below to PNG, read the PNG, and visually confirm arrows connect to circles with NO gap
- [ ] Arrow from start circle [*] touches the "Still" node
- [ ] Arrow from "Still" touches the end circle [*]
- [ ] Arrow from "Crash" touches the end circle [*]
- [ ] All existing tests pass

### Test diagram
```
stateDiagram-v2
    [*] --> Still
    Still --> [*]
    Still --> Moving
    Moving --> Still
    Moving --> Crash
    Crash --> [*]
```
