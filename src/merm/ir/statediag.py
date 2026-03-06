"""Intermediate representation for state diagrams.

Defines StateType, State, Transition, StateNote, and StateDiagram dataclasses
used by the state diagram parser, layout, and renderer.
"""

from dataclasses import dataclass
from enum import Enum

class StateType(Enum):
    """Type of state node."""

    NORMAL = "normal"
    START = "start"
    END = "end"
    CHOICE = "choice"
    FORK = "fork"
    JOIN = "join"

@dataclass(frozen=True)
class State:
    """A state in the state diagram."""

    id: str
    label: str
    state_type: StateType = StateType.NORMAL
    children: tuple["State", ...] = ()

@dataclass(frozen=True)
class Transition:
    """A transition between two states."""

    source: str
    target: str
    label: str = ""

@dataclass(frozen=True)
class StateNote:
    """A note attached to a state."""

    state_id: str
    text: str
    position: str = "right"  # "left" or "right"

@dataclass(frozen=True)
class StateDiagram:
    """Top-level state diagram representation."""

    states: tuple[State, ...] = ()
    transitions: tuple[Transition, ...] = ()
    notes: tuple[StateNote, ...] = ()

__all__ = [
    "State",
    "StateDiagram",
    "StateNote",
    "StateType",
    "Transition",
]
