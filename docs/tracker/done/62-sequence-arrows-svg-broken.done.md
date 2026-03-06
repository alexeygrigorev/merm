# Issue 62: Sequence diagram arrows.svg rendering broken

## Problem

`arrows.mmd` defines 6 arrow types but only 5 are rendered. The `B--)A: Dotted with open arrow` line is silently dropped because the parser does not recognize the `--)`  arrow syntax.

Additionally, `A-)B` (solid async) is mapped to `MessageType.ASYNC` but is functionally the same as `SOLID_OPEN` in Mermaid's rendering. The arrow type taxonomy may need review.

## Reproduction

```
tests/fixtures/corpus/sequence/arrows.mmd
```

```
sequenceDiagram
    participant A
    participant B
    A->>B: Solid with arrowhead
    B-->>A: Dotted with arrowhead
    A-xB: Solid with cross
    B--xA: Dotted with cross
    A-)B: Solid with open arrow
    B--)A: Dotted with open arrow
```

## Root Cause Analysis

In `src/merm/parser/sequence.py`:

1. `_ARROW_PATTERNS` does not include `--)` (dotted async/open arrow). The patterns list has `-)` for async but no `--)`  variant.
2. The regex `_MESSAGE_RE2` arrow group also lacks `--)`.
3. Since `--)` is not recognized, line 9 (`B--)A: Dotted with open arrow`) falls through all patterns and is silently skipped.

The fix requires:
- Adding `--)` to `_ARROW_PATTERNS` (ordered before `-->` and `-)` to avoid partial matches)
- Adding a corresponding `DASHED_ASYNC` variant to `MessageType` enum (or reusing `DASHED_OPEN` if appropriate)
- Adding `--)` to the regex arrow group
- Adding a marker definition in the renderer for the new type

Note: This issue shares root cause with issue 63 (oversized arrows in basic.mmd) in that the arrow marker sizing in the renderer (`src/merm/render/sequence.py`) also needs review. However, this issue specifically focuses on the missing `--)`  arrow type.

## Dependencies

- None

## Acceptance Criteria

- [ ] `parse_sequence()` on `arrows.mmd` returns 6 messages (not 5)
- [ ] The 6th message (B--)A) has the correct dotted/dashed arrow type
- [ ] `arrows.mmd` renders an SVG with 6 distinct message arrows, all visible
- [ ] Each arrow type is visually distinguishable: solid vs dotted line, filled vs open vs cross marker
- [ ] Other sequence diagrams still parse correctly (basic.mmd, activations.mmd)
- [ ] Existing tests pass (`uv run pytest`)
- [ ] Render `arrows.mmd` to PNG with cairosvg and visually verify all 6 arrow types render distinctly and correctly

## Test Scenarios

### Unit: Parser recognizes --)
- Parse `B--)A: Dotted with open arrow` -- verify it produces a Message with a dashed/dotted open arrow type
- Parse all 6 lines from arrows.mmd -- verify 6 Messages returned with distinct msg_type values

### Unit: Arrow pattern ordering
- Verify `--)`  does not partially match `-->` or `-)` (ordering matters in regex alternation)
- Verify `--)` is tried before `-->` and `-)` in the pattern list

### Integration: Full arrows.mmd render
- Render arrows.mmd to SVG, count `<g class="seq-message">` groups -- must be 6
- Verify each message group has a marker-end attribute

### Visual: PNG verification
- Render `arrows.mmd` to PNG via cairosvg, visually verify 6 arrows with correct styles (solid/dotted lines, filled/open/cross heads)
