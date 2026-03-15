# Issue 70: ER diagram renders too large

## Status: REOPENED — previous fix reduced spacing but result still too large

## Problem

ER diagrams render at an excessively large scale compared to mmdc output.

## Previous Fix (insufficient)

Reduced `_CHAR_WIDTH` from 8.0 to 7.0 and `rank_sep` from 40 to 25, `node_sep` from 30 to 20. Result was 292x240 — user reports still too large.

## Fix Required

- Further reduce entity box padding and margins
- Consider LR layout (more natural for ER diagrams)
- Reduce `_MIN_BOX_WIDTH` from 100 to something smaller
- Make entity boxes tighter around their text

## Acceptance Criteria

- [ ] **MANDATORY PNG CHECK**: Render the diagram below to PNG, read the PNG, and visually confirm it looks compact and well-proportioned
- [ ] Entity boxes should be tight around their text
- [ ] The diagram should look similar in density/proportion to mmdc output
- [ ] All existing tests pass

### Test diagram
```
erDiagram
    CUSTOMER ||--o{ ORDER : places
    ORDER ||--|{ LINE-ITEM : contains
    CUSTOMER }|..|{ DELIVERY-ADDRESS : uses
```
