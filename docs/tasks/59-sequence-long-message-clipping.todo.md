# Task 59: Sequence diagram long message label clipping

## Problem

In sequence diagrams, long message labels get truncated or overlap with other elements:

- Message text like `Event B (ts=14:00:04, 8s late)` renders as just `late)` — the beginning is clipped by the note box to the left
- Message text like `INSERT (window=00:00, PU=79, trips=2)` is cut off on the right, only showing `PU=79, trips=2)`
- `Note over` boxes can overlap with message arrows on the same vertical position

## Reproduction

```
tests/fixtures/github/flink_late_event.mmd
tests/fixtures/github/flink_late_upsert.mmd
```

## Expected behavior

- Message labels should be fully visible without clipping
- Participant spacing should expand to fit the longest message label between two participants
- Notes should not overlap with message arrows

## Acceptance criteria

- [ ] All message labels in flink_late_event.mmd are fully readable
- [ ] All message labels in flink_late_upsert.mmd are fully readable
- [ ] Note boxes do not overlap message arrows
- [ ] Existing sequence diagram tests still pass
- [ ] Visual verification via PNG rendering
