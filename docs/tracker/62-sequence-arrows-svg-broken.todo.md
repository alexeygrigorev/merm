# Issue 62: Sequence diagram arrows.svg rendering broken

## Problem

`docs/examples/sequence/arrows.svg` renders incorrectly — needs investigation.

## Reproduction

```
tests/fixtures/corpus/sequence/arrows.mmd
```

## Expected behavior

- All arrow types render correctly
- Arrow markers are properly sized

## Acceptance criteria

- [ ] arrows.mmd renders with all arrow types visible and correct
- [ ] Arrow markers properly sized (not too large, not missing)
- [ ] Visual verification via PNG rendering
