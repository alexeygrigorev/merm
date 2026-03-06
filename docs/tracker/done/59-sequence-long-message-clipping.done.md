# Issue 59: Sequence diagram long message label clipping

## Problem

In sequence diagrams, long message labels get truncated or overlap with other elements:

- Message text like `Event B (ts=14:00:04, 8s late)` renders as just `late)` -- the beginning is clipped by the note box to the left
- Message text like `INSERT (window=00:00, PU=79, trips=2)` is cut off on the right, only showing `PU=79, trips=2)`
- `Note over` boxes can overlap with message arrows on the same vertical position

The root cause is in `src/merm/layout/sequence.py`: participant spacing uses a fixed `_PARTICIPANT_GAP = 150.0` regardless of message label width. When message labels are longer than the gap between participants, they overflow and get clipped by adjacent notes or the viewport edge.

## Reproduction

```
tests/fixtures/github/flink_late_event.mmd
tests/fixtures/github/flink_late_upsert.mmd
```

## Root Cause Analysis

In `layout_sequence()`, participants are placed with fixed spacing:
```python
cx = _TOP_MARGIN + _PARTICIPANT_BOX_W / 2 + i * _PARTICIPANT_GAP
```

This does not account for message label widths between participant pairs. The viewport expansion at the bottom of `layout_sequence()` handles total width but does not reposition participants to create adequate spacing.

## Dependencies

- None (this is an independent layout fix)

## Acceptance Criteria

- [ ] All message labels in `flink_late_event.mmd` are fully readable in the rendered SVG -- no text clipped by notes or viewport
- [ ] All message labels in `flink_late_upsert.mmd` are fully readable
- [ ] Note boxes do not visually overlap with message arrows or message labels
- [ ] Participant horizontal spacing adapts to the longest message label between each participant pair
- [ ] Existing sequence diagram tests still pass (`uv run pytest`)
- [ ] Render `flink_late_event.mmd` and `flink_late_upsert.mmd` to PNG with cairosvg and visually verify that all message labels are fully visible, notes do not overlap arrows, and the diagram is properly spaced

## Test Scenarios

### Unit: Message label width drives participant spacing
- Parse `flink_late_event.mmd`, compute layout, verify that the horizontal distance between adjacent participants is at least as wide as the longest message label between them (plus padding)
- Parse `flink_late_upsert.mmd`, verify same property

### Unit: Note-message non-overlap
- For each note in flink_late_event layout, verify its bounding box does not overlap any message label bounding box at the same y-range

### Regression: Existing diagrams unchanged
- Render `basic.mmd`, `arrows.mmd` and verify layout dimensions are reasonable (no massive blowup from the spacing fix)

### Visual: PNG verification
- Render `flink_late_event.mmd` to PNG via cairosvg, visually verify all labels readable
- Render `flink_late_upsert.mmd` to PNG via cairosvg, visually verify all labels readable
