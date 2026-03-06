# Issue 61: Sequence diagram activation syntax produces empty SVG

## Problem

Sequence diagrams using Mermaid's `+`/`-` activation shorthand render as completely empty SVGs -- no participants, lifelines, messages, or activations appear. Only the defs/styles are output.

## Reproduction

```
tests/fixtures/corpus/sequence/activations.mmd
```

```
sequenceDiagram
    Alice->>+Bob: Hello Bob
    Bob->>+Charlie: Hi Charlie
    Charlie-->>-Bob: Reply
    Bob-->>-Alice: All done
```

## Root Cause Analysis

The parser in `src/merm/parser/sequence.py` uses `_MESSAGE_RE2` which expects the `+`/`-` activation markers AFTER the receiver name. However, Mermaid's syntax puts `+`/`-` BEFORE the receiver name (e.g., `->>+Bob`). The regex:

```python
r"(?P<arrow>-->>|->>|...)" + r"(?P<receiver>[A-Za-z_][\w]*)" + r"(?P<activate>\+?)"
```

does not match `->>+Bob` because `+Bob` fails to match `[A-Za-z_][\w]*` as the receiver.

Confirmed: `parse_sequence()` on this input returns `participants=()` and `items=()`.

The fix needs to adjust the regex to allow `+` or `-` between the arrow and the receiver name:

```python
r"(?P<arrow>...)" + r"\s*" + r"(?P<activate>\+?)(?P<deactivate>-?)" + r"(?P<receiver>[A-Za-z_][\w]*)"
```

Note: `_MESSAGE_RE` (the first regex) already has `activate`/`deactivate` groups in the right position, but the code only uses `_MESSAGE_RE2`. The fix should make `_MESSAGE_RE2` (or whichever regex is used) put `+`/`-` before the receiver.

## Dependencies

- None

## Acceptance Criteria

- [ ] `parse_sequence()` on `activations.mmd` returns 3 participants (Alice, Bob, Charlie)
- [ ] `parse_sequence()` on `activations.mmd` returns 4 messages with correct activate/deactivate flags
- [ ] `activations.mmd` renders an SVG with all 3 participant boxes visible
- [ ] All 4 messages render with arrows and labels
- [ ] Activation boxes appear on lifelines (Bob and Charlie each have an activation rectangle)
- [ ] Other sequence diagrams still parse and render correctly (basic.mmd, arrows.mmd)
- [ ] Existing tests pass (`uv run pytest`)
- [ ] Render `activations.mmd` to PNG with cairosvg and visually verify: 3 participants visible, 4 arrows with labels, activation boxes on Bob and Charlie lifelines

## Test Scenarios

### Unit: Parser activation handling
- Parse `Alice->>+Bob: Hello Bob` -- verify sender=Alice, receiver=Bob, activate=True, deactivate=False
- Parse `Bob-->>-Alice: All done` -- verify sender=Bob, receiver=Alice, activate=False, deactivate=True
- Parse `Alice->>Bob: Hello` (no +/-) -- verify activate=False, deactivate=False (regression)

### Unit: Full diagram parse
- Parse `activations.mmd`, verify 3 participants and 4 messages
- Verify activate flag on messages 1 and 2, deactivate flag on messages 3 and 4

### Unit: Layout activation boxes
- Compute layout for `activations.mmd`, verify activation_layout list is non-empty
- Verify activation boxes have correct participant_cx values

### Integration: SVG rendering
- Render `activations.mmd` to SVG, verify SVG contains participant boxes, lifelines, messages, and activation rectangles (via element counting)

### Visual: PNG verification
- Render `activations.mmd` to PNG via cairosvg, visually verify participants, messages, and activation boxes are all visible
