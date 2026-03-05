"""Intermediate representation for sequence diagrams.

Defines frozen dataclasses for participants, messages, notes, fragments,
and the top-level SequenceDiagram container.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MessageType(Enum):
    """Sequence diagram message/arrow types."""

    SOLID_ARROW = "solid_arrow"       # ->>
    DASHED_ARROW = "dashed_arrow"     # -->>
    SOLID_OPEN = "solid_open"         # ->
    DASHED_OPEN = "dashed_open"       # -->
    SOLID_CROSS = "solid_cross"       # -x
    DASHED_CROSS = "dashed_cross"     # --x
    ASYNC = "async"                   # -)


class NotePosition(Enum):
    """Position of a note relative to participant lifelines."""

    LEFT = "left"
    RIGHT = "right"
    OVER = "over"


class FragmentType(Enum):
    """Types of combined fragments (boxes around message groups)."""

    LOOP = "loop"
    ALT = "alt"
    ELSE = "else"
    OPT = "opt"


@dataclass(frozen=True)
class Participant:
    """A participant (actor or entity) in a sequence diagram."""

    id: str
    label: str
    is_actor: bool = False


@dataclass(frozen=True)
class Message:
    """A message arrow between two participants."""

    sender: str
    receiver: str
    text: str
    msg_type: MessageType
    activate: bool = False
    deactivate: bool = False


@dataclass(frozen=True)
class Note:
    """A note annotation attached to one or two participants."""

    text: str
    position: NotePosition
    participants: tuple[str, ...]


@dataclass(frozen=True)
class Fragment:
    """A combined fragment (loop, alt, opt) containing diagram items."""

    frag_type: FragmentType
    label: str
    items: tuple  # Message | Note | Fragment


@dataclass(frozen=True)
class SequenceDiagram:
    """Top-level sequence diagram IR container."""

    participants: tuple[Participant, ...]
    items: tuple  # ordered sequence of Message | Note | Fragment
