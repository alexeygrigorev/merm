# Issue 63: Sequence diagram basic.svg has oversized arrows

## Problem

`docs/examples/sequence/basic.svg` renders with arrows that are too large/oversized.

## Reproduction

```
tests/fixtures/corpus/sequence/basic.mmd
```

## Expected behavior

- Arrow markers should be proportional to line thickness
- Arrows should look similar in scale to mmdc reference output

## Acceptance criteria

- [ ] basic.mmd renders with properly sized arrows
- [ ] Arrow proportions match expected Mermaid style
- [ ] Other sequence diagrams not negatively affected
- [ ] Visual verification via PNG rendering
