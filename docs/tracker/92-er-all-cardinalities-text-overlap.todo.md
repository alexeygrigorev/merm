# Issue 92: ER diagram "all cardinalities" has overlapping text

## Problem

In the ER `all_cardinalities.mmd` fixture, relationship labels and cardinality markers overlap each other, making text unreadable.

Reproduction: `tests/fixtures/corpus/er/all_cardinalities.mmd`

## Acceptance criteria

- Relationship labels must not overlap with cardinality markers
- All text must be readable without zooming
- Labels must have adequate spacing from entity boxes and from each other
- Existing tests must continue to pass
