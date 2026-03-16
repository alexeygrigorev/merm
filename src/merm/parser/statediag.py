"""State diagram parser: Mermaid stateDiagram syntax -> StateDiagram IR.

Supports stateDiagram and stateDiagram-v2 declarations.
"""

import re
from dataclasses import dataclass, field

from merm.ir.statediag import (
    State,
    StateDiagram,
    StateNote,
    StateType,
    Transition,
)
from merm.parser.flowchart import ParseError


def _strip_comment(line: str) -> str:
    """Remove %% comments from a line."""
    idx = line.find("%%")
    if idx >= 0:
        return line[:idx].rstrip()
    return line

def _preprocess(text: str) -> list[tuple[int, str]]:
    """Return list of (line_number, stripped_line)."""
    result: list[tuple[int, str]] = []
    for lineno, raw in enumerate(text.split("\n"), start=1):
        stripped = _strip_comment(raw).strip()
        if stripped:
            result.append((lineno, stripped))
    return result

# Regex for transitions: s1 --> s2 or s1 --> s2 : label
_TRANSITION_RE = re.compile(
    r"^(\S+)\s*-->\s*(\S+)(?:\s*:\s*(.+))?$"
)

# Regex for state alias: state "Long name" as s1
_STATE_ALIAS_RE = re.compile(
    r'^state\s+"([^"]+)"\s+as\s+(\S+)\s*$'
)

# Regex for state with description: s1 : Description
_STATE_DESC_RE = re.compile(
    r"^(\S+)\s*:\s*(.+)$"
)

# Regex for pseudo-state: state name <<choice>>, <<fork>>, <<join>>
_STATE_PSEUDO_RE = re.compile(
    r"^state\s+(\S+)\s+<<(choice|fork|join)>>\s*$"
)

# Regex for composite state start: state CompositeState {
_COMPOSITE_START_RE = re.compile(
    r"^state\s+(?:\"([^\"]+)\"\s+as\s+)?(\S+)\s*\{\s*$"
)

# Regex for note: note left of s1 : text  or  note right of s1 : text
_NOTE_RE = re.compile(
    r"^note\s+(left|right)\s+of\s+(\S+)\s*:\s*(.+)$"
)

@dataclass
class _StateInfo:
    """Mutable state info accumulated during parsing."""
    id: str
    label: str
    state_type: StateType = StateType.NORMAL
    children: list[State] = field(default_factory=list)

@dataclass
class _ParserState:
    """Mutable parser state."""
    states: dict[str, _StateInfo] = field(default_factory=dict)
    transitions: list[Transition] = field(default_factory=list)
    notes: list[StateNote] = field(default_factory=list)
    # Stack for composite state parsing
    composite_stack: list["_CompositeBuilder"] = field(default_factory=list)
    # Counter for generating unique start/end state IDs
    start_count: int = 0
    end_count: int = 0

@dataclass
class _CompositeBuilder:
    """Builder for a composite state."""
    id: str
    label: str
    states: dict[str, _StateInfo] = field(default_factory=dict)
    transitions: list[Transition] = field(default_factory=list)

def _ensure_state(
    state_id: str, states: dict[str, _StateInfo],
) -> _StateInfo:
    """Ensure a state exists in the states dict, creating if needed."""
    if state_id not in states:
        states[state_id] = _StateInfo(id=state_id, label=state_id)
    return states[state_id]

def _resolve_pseudo_state(
    state_id: str, is_source: bool, pstate: _ParserState,
    states: dict[str, _StateInfo],
) -> str:
    """Resolve [*] pseudo-state references to unique start/end state IDs."""
    if state_id != "[*]":
        return state_id

    if is_source:
        # [*] as source = start state
        real_id = f"__start_{pstate.start_count}"
        pstate.start_count += 1
        if real_id not in states:
            states[real_id] = _StateInfo(
                id=real_id, label="", state_type=StateType.START,
            )
        return real_id
    else:
        # [*] as target = end state
        real_id = f"__end_{pstate.end_count}"
        pstate.end_count += 1
        if real_id not in states:
            states[real_id] = _StateInfo(
                id=real_id, label="", state_type=StateType.END,
            )
        return real_id

def _get_current_states(pstate: _ParserState) -> dict[str, _StateInfo]:
    """Get the states dict for the current context (top-level or composite)."""
    if pstate.composite_stack:
        return pstate.composite_stack[-1].states
    return pstate.states

def _get_current_transitions(pstate: _ParserState) -> list[Transition]:
    """Get the transitions list for the current context."""
    if pstate.composite_stack:
        return pstate.composite_stack[-1].transitions
    return pstate.transitions

def _merge_parallel_pseudo_states(builder: _CompositeBuilder) -> None:
    """Merge multiple start/end pseudo-states into fork/join bars.

    When a composite state has multiple ``[*] --> X`` transitions (parallel
    entries), the separate start pseudo-states are replaced by a single fork
    bar. Similarly, multiple ``X --> [*]`` transitions are replaced by a
    single join bar.
    """
    states = builder.states
    transitions = builder.transitions

    # Collect start and end pseudo-state IDs
    start_ids = [
        sid for sid, si in states.items() if si.state_type == StateType.START
    ]
    end_ids = [
        sid for sid, si in states.items() if si.state_type == StateType.END
    ]

    # Merge multiple starts into a fork
    if len(start_ids) >= 2:
        fork_id = f"__fork_{builder.id}"
        states[fork_id] = _StateInfo(
            id=fork_id, label="", state_type=StateType.FORK,
        )
        new_transitions: list[Transition] = []
        for t in transitions:
            if t.source in start_ids:
                # Replace start->target with fork->target
                new_transitions.append(
                    Transition(source=fork_id, target=t.target, label=t.label)
                )
            else:
                new_transitions.append(t)
        # Remove old start states
        for sid in start_ids:
            del states[sid]
        transitions.clear()
        transitions.extend(new_transitions)

    # Merge multiple ends into a join
    if len(end_ids) >= 2:
        join_id = f"__join_{builder.id}"
        states[join_id] = _StateInfo(
            id=join_id, label="", state_type=StateType.JOIN,
        )
        new_transitions2: list[Transition] = []
        for t in transitions:
            if t.target in end_ids:
                # Replace source->end with source->join
                new_transitions2.append(
                    Transition(source=t.source, target=join_id, label=t.label)
                )
            else:
                new_transitions2.append(t)
        # Remove old end states
        for eid in end_ids:
            del states[eid]
        transitions.clear()
        transitions.extend(new_transitions2)


def _parse_line(
    line: str, lineno: int, pstate: _ParserState,
) -> None:
    """Parse a single logical line."""
    states = _get_current_states(pstate)
    transitions = _get_current_transitions(pstate)

    # Closing brace for composite state
    if line == "}":
        if not pstate.composite_stack:
            raise ParseError("Unexpected '}'", lineno)
        builder = pstate.composite_stack.pop()

        # Merge multiple start pseudo-states into a single fork bar,
        # and multiple end pseudo-states into a single join bar.
        _merge_parallel_pseudo_states(builder)

        # Build child states
        children = tuple(
            State(
                id=si.id,
                label=si.label,
                state_type=si.state_type,
            )
            for si in builder.states.values()
        )
        # Register the composite state in the parent context
        parent_states = _get_current_states(pstate)
        parent_states[builder.id] = _StateInfo(
            id=builder.id,
            label=builder.label,
            state_type=StateType.NORMAL,
            children=list(children),
        )
        # Add child transitions to parent
        parent_transitions = _get_current_transitions(pstate)
        parent_transitions.extend(builder.transitions)
        return

    # Composite state start: state Name { or state "Label" as Name {
    m = _COMPOSITE_START_RE.match(line)
    if m:
        label = m.group(1) or m.group(2)
        state_id = m.group(2)
        builder = _CompositeBuilder(id=state_id, label=label)
        pstate.composite_stack.append(builder)
        return

    # Pseudo-state declaration: state name <<choice>>
    m = _STATE_PSEUDO_RE.match(line)
    if m:
        state_id = m.group(1)
        pseudo_type = m.group(2)
        type_map = {
            "choice": StateType.CHOICE,
            "fork": StateType.FORK,
            "join": StateType.JOIN,
        }
        states[state_id] = _StateInfo(
            id=state_id,
            label=state_id,
            state_type=type_map[pseudo_type],
        )
        return

    # State alias: state "Long name" as s1
    m = _STATE_ALIAS_RE.match(line)
    if m:
        label = m.group(1)
        state_id = m.group(2)
        info = _ensure_state(state_id, states)
        info.label = label
        return

    # Note: note left of s1 : text
    m = _NOTE_RE.match(line)
    if m:
        position = m.group(1)
        state_id = m.group(2)
        text = m.group(3).strip()
        _ensure_state(state_id, states)
        pstate.notes.append(StateNote(
            state_id=state_id, text=text, position=position,
        ))
        return

    # Transition: s1 --> s2 or s1 --> s2 : label
    m = _TRANSITION_RE.match(line)
    if m:
        src_raw = m.group(1)
        tgt_raw = m.group(2)
        label = (m.group(3) or "").strip()

        src = _resolve_pseudo_state(src_raw, True, pstate, states)
        tgt = _resolve_pseudo_state(tgt_raw, False, pstate, states)

        _ensure_state(src, states)
        _ensure_state(tgt, states)

        transitions.append(Transition(source=src, target=tgt, label=label))
        return

    # State with description: s1 : Description
    m = _STATE_DESC_RE.match(line)
    if m:
        state_id = m.group(1)
        desc = m.group(2).strip()
        # Avoid matching if it looks like a note or other directive
        if state_id.lower() in ("note",):
            return
        info = _ensure_state(state_id, states)
        info.label = desc
        return

    # Bare state name (single word)
    if re.match(r"^[A-Za-z_]\w*$", line):
        _ensure_state(line, states)
        return

    # Ignore unknown lines silently (direction, etc.)

def parse_state_diagram(text: str) -> StateDiagram:
    """Parse Mermaid state diagram syntax into a StateDiagram.

    Parameters
    ----------
    text:
        Complete Mermaid stateDiagram source, including the declaration line.

    Returns
    -------
    StateDiagram

    Raises
    ------
    ParseError
        On invalid syntax.
    """
    lines = _preprocess(text)
    if not lines:
        raise ParseError("Empty input")

    # First line must be the declaration
    first_lineno, first_line = lines[0]
    if not re.match(r"^stateDiagram(-v2)?\s*$", first_line, re.IGNORECASE):
        raise ParseError(
            f"Expected 'stateDiagram' or 'stateDiagram-v2' declaration, "
            f"got: {first_line!r}",
            first_lineno,
        )

    pstate = _ParserState()

    for lineno, line in lines[1:]:
        _parse_line(line, lineno, pstate)

    # Check for unclosed composite states
    if pstate.composite_stack:
        raise ParseError(
            f"Unclosed composite state '{pstate.composite_stack[-1].id}'",
        )

    # Build State objects from _StateInfo
    def _build_state(si: _StateInfo) -> State:
        children = tuple(si.children) if si.children else ()
        return State(
            id=si.id,
            label=si.label,
            state_type=si.state_type,
            children=children,
        )

    all_states = tuple(_build_state(si) for si in pstate.states.values())

    return StateDiagram(
        states=all_states,
        transitions=tuple(pstate.transitions),
        notes=tuple(pstate.notes),
    )

__all__ = ["parse_state_diagram"]
