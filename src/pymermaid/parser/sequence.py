"""Parser for Mermaid sequence diagram syntax.

Converts sequence diagram text into a SequenceDiagram IR.
Line-oriented parser: one statement per line.
"""

from __future__ import annotations

import re

from pymermaid.ir.sequence import (
    Fragment,
    FragmentType,
    Message,
    MessageType,
    Note,
    NotePosition,
    Participant,
    SequenceDiagram,
)
from pymermaid.parser.flowchart import ParseError

# Message arrow patterns, ordered longest-first to avoid partial matches.
_ARROW_PATTERNS: list[tuple[str, MessageType]] = [
    ("-->>", MessageType.DASHED_ARROW),
    ("->>", MessageType.SOLID_ARROW),
    ("--x", MessageType.DASHED_CROSS),
    ("-x", MessageType.SOLID_CROSS),
    ("-->", MessageType.DASHED_OPEN),
    ("->", MessageType.SOLID_OPEN),
    ("-)", MessageType.ASYNC),
]

# Regex for message lines:  sender ARROW receiver : text
# The arrow is matched by trying each pattern.
_MESSAGE_RE = re.compile(
    r"^(?P<sender>[A-Za-z_][\w]*)"
    r"\s*"
    r"(?P<arrow>-->>|->>|--x|-x|-->|->|-\))"
    r"\s*"
    r"(?P<activate>\+?)"
    r"(?P<deactivate>-?)"
    r"\s*"
    r"(?P<receiver>[A-Za-z_][\w]*)"
    r"\s*"
    r"(?::\s*(?P<text>.*))?$"
)

# Alternative: activate/deactivate shorthand after receiver
_MESSAGE_RE2 = re.compile(
    r"^(?P<sender>[A-Za-z_][\w]*)"
    r"\s*"
    r"(?P<arrow>-->>|->>|--x|-x|-->|->|-\))"
    r"\s*"
    r"(?P<receiver>[A-Za-z_][\w]*)"
    r"\s*"
    r"(?P<activate>\+?)"
    r"(?P<deactivate>-?)"
    r"\s*"
    r"(?::\s*(?P<text>.*))?$"
)

_PARTICIPANT_RE = re.compile(
    r"^(?P<kind>participant|actor)\s+(?P<id>[A-Za-z_][\w]*)"
    r"(?:\s+as\s+(?P<label>.+))?\s*$"
)

_NOTE_RE = re.compile(
    r"^Note\s+(?P<pos>left\s+of|right\s+of|over)\s+"
    r"(?P<participants>[A-Za-z_][\w]*(?:\s*,\s*[A-Za-z_][\w]*)?)"
    r"\s*:\s*(?P<text>.+)$",
    re.IGNORECASE,
)

_ACTIVATE_RE = re.compile(r"^activate\s+(?P<id>[A-Za-z_][\w]*)\s*$")
_DEACTIVATE_RE = re.compile(r"^deactivate\s+(?P<id>[A-Za-z_][\w]*)\s*$")

_FRAGMENT_START_RE = re.compile(
    r"^(?P<type>loop|alt|opt|else)\s*(?P<label>.*)$", re.IGNORECASE
)

_ARROW_MAP: dict[str, MessageType] = {
    arrow: mt for arrow, mt in _ARROW_PATTERNS
}


def _detect_sequence(text: str) -> bool:
    """Return True if text declares a sequenceDiagram."""
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped == "" or stripped.startswith("%%"):
            continue
        return stripped.lower().startswith("sequencediagram")
    return False


def parse_sequence(text: str) -> SequenceDiagram:
    """Parse Mermaid sequence diagram text into a SequenceDiagram IR.

    Args:
        text: Mermaid sequence diagram source text.

    Returns:
        A SequenceDiagram instance.

    Raises:
        ParseError: If the text is not a valid sequence diagram.
    """
    lines = text.strip().split("\n")
    lines = [ln.strip() for ln in lines]

    # Skip leading comments/blanks, then expect sequenceDiagram header.
    idx = 0
    while idx < len(lines) and (lines[idx] == "" or lines[idx].startswith("%%")):
        idx += 1

    if idx >= len(lines) or not lines[idx].lower().startswith("sequencediagram"):
        raise ParseError("Expected 'sequenceDiagram' header")
    idx += 1

    # Track participants in declaration order, auto-create from messages.
    participant_order: list[str] = []
    participant_map: dict[str, Participant] = {}

    def _ensure_participant(pid: str) -> None:
        """Auto-create participant if not already declared."""
        if pid not in participant_map:
            participant_map[pid] = Participant(id=pid, label=pid)
            participant_order.append(pid)

    def _parse_block(start: int) -> tuple[list, int]:
        """Parse a block of items until 'end' or EOF.

        Returns (items, next_index).
        """
        items: list = []
        i = start
        while i < len(lines):
            line = lines[i]

            # Skip blanks and comments.
            if line == "" or line.startswith("%%"):
                i += 1
                continue

            # End of fragment block.
            if line.lower() == "end":
                return items, i + 1

            # Else clause within alt fragment -- signals end of current block.
            m_frag = _FRAGMENT_START_RE.match(line)
            if m_frag and m_frag.group("type").lower() == "else":
                # Don't consume this line; let the caller handle it.
                return items, i

            # Fragment start (loop / alt / opt).
            if m_frag and m_frag.group("type").lower() in ("loop", "alt", "opt"):
                ftype = FragmentType(m_frag.group("type").lower())
                label = m_frag.group("label").strip()
                sub_items, i = _parse_fragment(ftype, label, i + 1)
                items.extend(sub_items)
                continue

            # Participant / actor declaration.
            m_part = _PARTICIPANT_RE.match(line)
            if m_part:
                pid = m_part.group("id")
                plabel = m_part.group("label") or pid
                is_actor = m_part.group("kind").lower() == "actor"
                if pid not in participant_map:
                    participant_order.append(pid)
                participant_map[pid] = Participant(
                    id=pid, label=plabel.strip(), is_actor=is_actor,
                )
                i += 1
                continue

            # Note.
            m_note = _NOTE_RE.match(line)
            if m_note:
                pos_str = m_note.group("pos").lower().replace(" ", "_")
                if "left" in pos_str:
                    pos = NotePosition.LEFT
                elif "right" in pos_str:
                    pos = NotePosition.RIGHT
                else:
                    pos = NotePosition.OVER
                parts = [
                    p.strip()
                    for p in m_note.group("participants").split(",")
                ]
                for p in parts:
                    _ensure_participant(p)
                items.append(Note(
                    text=m_note.group("text").strip(),
                    position=pos,
                    participants=tuple(parts),
                ))
                i += 1
                continue

            # Activate / deactivate.
            m_act = _ACTIVATE_RE.match(line)
            if m_act:
                _ensure_participant(m_act.group("id"))
                # Activation commands don't create items in our simple IR;
                # they are tracked during layout. But we need to pass them
                # through for layout to see. We encode them as messages
                # to self with empty text? Actually, let's just skip them
                # and track activation via +/- on messages and explicit
                # activate/deactivate. We need a representation.
                # Let's use Message to self with activate/deactivate flags.
                # Actually, let's store them as Note-like markers. Simpler:
                # add them to items as special messages.
                # For now, we store activation info in the items list using
                # a convention: Message from participant to self with empty text.
                pid = m_act.group("id")
                items.append(Message(
                    sender=pid, receiver=pid, text="",
                    msg_type=MessageType.SOLID_ARROW,
                    activate=True, deactivate=False,
                ))
                i += 1
                continue

            m_deact = _DEACTIVATE_RE.match(line)
            if m_deact:
                _ensure_participant(m_deact.group("id"))
                pid = m_deact.group("id")
                items.append(Message(
                    sender=pid, receiver=pid, text="",
                    msg_type=MessageType.SOLID_ARROW,
                    activate=False, deactivate=True,
                ))
                i += 1
                continue

            # Message.
            m_msg = _MESSAGE_RE2.match(line)
            if m_msg:
                sender = m_msg.group("sender")
                receiver = m_msg.group("receiver")
                arrow = m_msg.group("arrow")
                msg_text = (m_msg.group("text") or "").strip()
                activate = m_msg.group("activate") == "+"
                deactivate = m_msg.group("deactivate") == "-"
                _ensure_participant(sender)
                _ensure_participant(receiver)
                msg_type = _ARROW_MAP[arrow]
                items.append(Message(
                    sender=sender,
                    receiver=receiver,
                    text=msg_text,
                    msg_type=msg_type,
                    activate=activate,
                    deactivate=deactivate,
                ))
                i += 1
                continue

            # Unknown line -- skip with warning (be lenient).
            i += 1

        return items, i

    def _parse_fragment(
        ftype: FragmentType, label: str, start: int,
    ) -> tuple[list, int]:
        """Parse a fragment block, handling alt/else specially."""
        if ftype == FragmentType.ALT:
            # Parse the alt body.
            alt_items, i = _parse_block(start)
            fragments = [Fragment(
                frag_type=FragmentType.ALT,
                label=label,
                items=tuple(alt_items),
            )]

            # Handle else clauses.
            while i < len(lines):
                line = lines[i]
                m = _FRAGMENT_START_RE.match(line)
                if m and m.group("type").lower() == "else":
                    else_label = m.group("label").strip()
                    else_items, i = _parse_block(i + 1)
                    fragments.append(Fragment(
                        frag_type=FragmentType.ELSE,
                        label=else_label,
                        items=tuple(else_items),
                    ))
                else:
                    break

            # Expect 'end'.
            if i < len(lines) and lines[i].lower() == "end":
                i += 1

            return fragments, i
        else:
            # Simple fragment (loop, opt).
            block_items, i = _parse_block(start)
            return [Fragment(
                frag_type=ftype,
                label=label,
                items=tuple(block_items),
            )], i

    items, _ = _parse_block(idx)

    return SequenceDiagram(
        participants=tuple(participant_map[pid] for pid in participant_order),
        items=tuple(items),
    )
