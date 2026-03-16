# Issue 83: Edge labels overlap diamond (decision) node borders

## Problem

In flowcharts with diamond-shaped decision nodes, edge labels ("Yes", "No", etc.) with their gray background rectangles partially overlap the diamond node borders. The label backgrounds clip into the node edges.

Reproduction: `tests/fixtures/corpus/flowchart/coffee_machine.mmd`

## Acceptance criteria

- Edge labels on edges leaving a diamond node must not overlap the diamond border
- The label background rectangle must be fully outside the node boundary
- Labels must remain readable and positioned near the midpoint of the edge
- Existing tests must continue to pass
- Visual check at 2x zoom shows clean separation between labels and diamond borders
