# Issue 64: Sequence diagram flink examples render incorrectly

## Problem

`docs/examples/sequence/flink_late_event.svg` and `docs/examples/sequence/flink_late_upsert.svg` render incorrectly — likely related to long message label clipping (see also issue 59).

## Reproduction

```
tests/fixtures/github/flink_late_event.mmd
tests/fixtures/github/flink_late_upsert.mmd
```

## Expected behavior

- All message labels fully visible without clipping
- Participant spacing expands to fit longest message label
- Notes don't overlap message arrows

## Acceptance criteria

- [ ] flink_late_event.svg renders with all labels fully readable
- [ ] flink_late_upsert.svg renders with all labels fully readable
- [ ] Note boxes don't overlap message arrows
- [ ] Visual verification via PNG rendering
