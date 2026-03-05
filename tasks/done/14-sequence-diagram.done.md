# 14 - Sequence Diagram Support

## Goal
Add support for sequence diagrams — the second most popular mermaid diagram type. This requires a completely different layout approach (horizontal participants, vertical timeline) compared to flowcharts.

## Scope (MVP — most common features)
Focus on the most-used sequence diagram features. Defer advanced features to a follow-up task.

### In Scope
- `sequenceDiagram` declaration
- Participants: `participant A`, `participant A as Alice`, `actor B`
- Messages: `A->>B: text` (solid arrow), `A-->>B: text` (dashed arrow), `A-)B: text` (async), `A-xB: text` (cross)
- Activations: `activate A` / `deactivate A`, `+`/`-` shorthand on messages
- Notes: `Note left of A: text`, `Note right of A: text`, `Note over A: text`, `Note over A,B: text`
- Loops: `loop text ... end`
- Conditionals: `alt text ... else text ... end`
- `opt text ... end` blocks

### Deferred (future task)
- `par`, `critical`, `break` blocks
- `rect` background highlights
- `autonumber`
- Participant creation/destruction mid-diagram
- Nested fragments (fragment inside fragment)

## Implementation Plan

### 1. IR Extensions (`src/pymermaid/ir/sequence.py`)
```python
@dataclass(frozen=True)
class Participant:
    id: str
    label: str  # display name (from "as" alias)
    is_actor: bool = False

class MessageType(Enum):
    SOLID_ARROW = "solid_arrow"      # ->>
    DASHED_ARROW = "dashed_arrow"    # -->>
    SOLID_OPEN = "solid_open"        # ->
    DASHED_OPEN = "dashed_open"      # -->
    SOLID_CROSS = "solid_cross"      # -x
    DASHED_CROSS = "dashed_cross"    # --x
    ASYNC = "async"                  # -)

@dataclass(frozen=True)
class Message:
    sender: str       # participant id
    receiver: str     # participant id
    text: str
    msg_type: MessageType
    activate: bool = False    # + shorthand
    deactivate: bool = False  # - shorthand

class NotePosition(Enum):
    LEFT = "left"
    RIGHT = "right"
    OVER = "over"

@dataclass(frozen=True)
class Note:
    text: str
    position: NotePosition
    participants: tuple[str, ...]  # 1 or 2 participant ids

class FragmentType(Enum):
    LOOP = "loop"
    ALT = "alt"
    ELSE = "else"
    OPT = "opt"

@dataclass(frozen=True)
class Fragment:
    frag_type: FragmentType
    label: str
    items: tuple  # Message | Note | Fragment | ActivationChange

@dataclass(frozen=True)
class SequenceDiagram:
    participants: tuple[Participant, ...]
    items: tuple  # ordered sequence of Message | Note | Fragment | ActivationChange
```

### 2. Parser (`src/pymermaid/parser/sequence.py`)
- `parse_sequence(text: str) -> SequenceDiagram`
- Line-oriented parser (sequence diagrams are mostly one-statement-per-line)
- Auto-create participants from first mention if not explicitly declared
- Participant ordering: explicit declarations first, then order of first appearance

### 3. Layout (`src/pymermaid/layout/sequence.py`)
- `layout_sequence(diagram: SequenceDiagram, measure_fn) -> SequenceLayout`
- Horizontal: participants evenly spaced, participant_gap configurable (~150px)
- Vertical: messages stacked with message_gap (~40px), top offset for participant boxes
- Activation tracking: stack-based, track active ranges per participant
- Fragment boxes: compute bounding box from contained items
- Note boxes: positioned relative to participant lifelines
- Returns: `SequenceLayout` with participant positions, message positions, lifeline extents, activation boxes, note boxes, fragment boxes

### 4. Renderer (`src/pymermaid/render/sequence.py`)
- `render_sequence_svg(diagram: SequenceDiagram, layout: SequenceLayout, theme: Theme) -> str`
- Participant boxes at top (rect with label) or actor stick figures
- Dashed lifelines from participant box to bottom
- Message arrows: solid/dashed lines with appropriate markers
- Activation rectangles: thin filled rects on lifelines
- Note boxes: yellow-ish rectangles with text
- Fragment boxes: labeled rectangles with dashed border
- Use theme colors consistently

### 5. Integration
- Add `DiagramType.SEQUENCE` to IR enums
- Update `src/pymermaid/__init__.py` to detect and route sequence diagrams
- Update CLI to handle sequence diagrams
- Add `render_svg()` dispatch or new entry point

## Acceptance Criteria
- [ ] `parse_sequence()` correctly parses participants, messages, notes, activations, loops, alt/else, opt
- [ ] Participants auto-created from first mention when not explicitly declared
- [ ] `layout_sequence()` produces non-overlapping layout with proper spacing
- [ ] Lifelines extend from participant box to bottom of diagram
- [ ] All 7 message types render with correct line style and arrowhead
- [ ] Activations render as thin rectangles on lifelines
- [ ] Notes positioned correctly (left, right, over one or two participants)
- [ ] Loop/alt/opt fragments render as labeled boxes around their content
- [ ] Actor participants render as stick figures (not boxes)
- [ ] Theme colors applied (use same purple/grey scheme)
- [ ] 30+ tests covering parser, layout, and renderer
- [ ] All existing 945 tests still pass
- [ ] Lint passes

## Engineer Notes
- This is a self-contained module — new files only, minimal changes to existing code
- The layout is fundamentally different from Sugiyama (no graph, just ordered timeline)
- Keep the renderer separate from flowchart renderer — `render/sequence.py` not mixed into `render/svg.py`
- For stick figure actors, use simple SVG paths (circle head, line body, angled arms/legs)
- Message arrow markers: reuse existing `arrow` marker from edges.py defs, add new ones as needed

## Dependencies
- Tasks 01-13, 17-19 complete ✅

## Estimated Complexity
Large — new parser, new layout algorithm, new renderer. ~800-1200 lines of new code.
