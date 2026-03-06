# Issue 64: Sequence diagram flink examples render incorrectly

## Problem

The flink sequence diagram examples (`flink_late_event.mmd` and `flink_late_upsert.mmd`) render with multiple visual issues: clipped message labels, note-message overlaps, and potentially oversized arrows.

This issue is a composite of problems addressed individually in issues 59 (message clipping), 62 (arrow types), and 63 (oversized arrows). This issue tracks the end-to-end correctness of these specific diagrams after those underlying fixes are applied.

## Reproduction

```
tests/fixtures/github/flink_late_event.mmd
tests/fixtures/github/flink_late_upsert.mmd
```

## Dependencies

- Issue 59 (sequence long message clipping) -- must be done first, as it fixes the participant spacing that causes label clipping
- Issue 63 (oversized arrows) -- should be done first, as it fixes arrow proportions

## Acceptance Criteria

- [ ] `flink_late_event.mmd` renders with ALL message labels fully readable:
  - "Event A (ts=14:00:07, on time)"
  - "Event A"
  - "Event B (ts=14:00:04, 8s late)"
  - "Event B"
  - "INSERT (window=00:00, PU=79, trips=2)"
- [ ] `flink_late_upsert.mmd` renders with ALL message labels fully readable:
  - "Event A (ts=14:00:07, on time)"
  - "Event A"
  - "INSERT (window=00:00, PU=79, trips=1)"
  - "Event B (ts=14:00:04, 20s late)"
  - "Event B"
  - "UPDATE (window=00:00, PU=79, trips=2)"
- [ ] All `Note over` boxes display their full multi-line text without clipping
- [ ] Note boxes do not overlap message arrows or message labels
- [ ] Arrow markers are proportional (not oversized)
- [ ] All 4 participants (Producer, Kafka, Flink, PostgreSQL) are visible with correct labels
- [ ] Existing tests pass (`uv run pytest`)
- [ ] Render both diagrams to PNG with cairosvg and visually verify: all labels readable, no overlaps, proportional arrows, all participants visible

## Test Scenarios

### Integration: flink_late_event.mmd end-to-end
- Parse the diagram, verify 4 participants with aliases (P->Producer, K->Kafka, F->Flink, PG->PostgreSQL)
- Render to SVG, verify all 5 message labels appear as complete text in the SVG source
- Verify no note bounding box overlaps any message label bounding box (compute from layout)

### Integration: flink_late_upsert.mmd end-to-end
- Parse the diagram, verify 4 participants with aliases
- Render to SVG, verify all 6 message labels appear as complete text
- Verify note-message non-overlap

### Visual: PNG verification
- Render `flink_late_event.mmd` to PNG via cairosvg, visually verify complete diagram correctness
- Render `flink_late_upsert.mmd` to PNG via cairosvg, visually verify complete diagram correctness
- Both PNGs should show: readable labels, no clipping, no overlaps, proportional arrows
