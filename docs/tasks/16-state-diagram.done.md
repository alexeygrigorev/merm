# 16 - State Diagram Support

## Goal
Add support for state machine diagrams (`stateDiagram-v2`). These reuse the Sugiyama layout since state machines are directed graphs.

## Scope (MVP)

### In Scope
- `stateDiagram-v2` declaration (also accept `stateDiagram`)
- States: `s1`, `s1 : Description`, `state "Long name" as s1`
- Transitions: `s1 --> s2`, `s1 --> s2 : event`
- Start/end pseudo-states: `[*] --> s1`, `s1 --> [*]`
- Composite states: `state CompositeState { s1 --> s2 }`
- Choice pseudo-state: `state choice <<choice>>`
- Fork/join pseudo-state: `state forkState <<fork>>`, `<<join>>`
- Notes: `note left of s1 : text`, `note right of s1`

### Deferred
- Concurrency (`--` divider inside composite states)
- Direction override inside composite states
- Styling directives

## Implementation Plan

### 1. IR (`src/pymermaid/ir/statediag.py`)
```python
class StateType(Enum):
    NORMAL = "normal"
    START = "start"       # [*] as source
    END = "end"           # [*] as target
    CHOICE = "choice"     # <<choice>>
    FORK = "fork"         # <<fork>>
    JOIN = "join"         # <<join>>

@dataclass(frozen=True)
class State:
    id: str
    label: str
    state_type: StateType
    children: tuple  # nested states for composite

@dataclass(frozen=True)
class Transition:
    source: str
    target: str
    label: str = ""

@dataclass(frozen=True)
class StateNote:
    state_id: str
    text: str
    position: str  # "left" or "right"

@dataclass(frozen=True)
class StateDiagram:
    states: tuple[State, ...]
    transitions: tuple[Transition, ...]
    notes: tuple[StateNote, ...]
```

### 2. Parser (`src/pymermaid/parser/statediag.py`)
- `parse_state_diagram(text: str) -> StateDiagram`
- Line-oriented parser
- Handle `[*]` by creating special start/end state nodes
- Composite states: recursive parsing of `state X { ... }` blocks
- Auto-create states from transition references

### 3. Layout
- Reuse Sugiyama layout by converting to flowchart-style IR
- Composite states map to subgraphs
- Fork/join rendered as horizontal bars (wide, thin nodes)

### 4. Renderer (`src/pymermaid/render/statediag.py`)
- Normal states: rounded rectangles (more rounded than flowchart, rx=10+)
- Start `[*]`: filled black circle
- End `[*]`: bull's eye (filled circle inside circle)
- Fork/join: horizontal black bar
- Choice: diamond (reuse from flowchart)
- Composite states: bordered box containing child states (like subgraphs)
- Transition arrows with optional labels
- Notes: yellow boxes positioned beside states

## Acceptance Criteria
- [ ] `parse_state_diagram()` handles states, transitions, start/end, composites, choice, fork/join, notes
- [ ] Start state renders as filled black circle
- [ ] End state renders as bull's eye
- [ ] Normal states render as rounded rectangles
- [ ] Fork/join render as horizontal bars
- [ ] Choice renders as diamond
- [ ] Composite states contain their children (like subgraphs)
- [ ] Transitions have optional labels
- [ ] Notes positioned correctly
- [ ] Layout uses Sugiyama, produces non-overlapping diagram
- [ ] Theme colors applied
- [ ] 25+ tests
- [ ] All existing tests still pass
- [ ] Lint passes

## Dependencies
- Tasks 01-13, 17-19 complete ✅

## Estimated Complexity
Medium — similar to flowcharts with specialized node shapes and composite state handling.
