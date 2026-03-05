"""Layout engine for sequence diagrams.

Positions participants horizontally and messages vertically on a timeline.
Computes bounding boxes for activations, notes, and fragments.
"""

from dataclasses import dataclass, field
from typing import Callable

from pymermaid.ir.sequence import (
    Fragment,
    Message,
    Note,
    NotePosition,
    SequenceDiagram,
)

# Type alias for text measurement function: (text, font_size) -> (width, height)
MeasureFn = Callable[[str, float], tuple[float, float]]

# Layout constants.
_PARTICIPANT_GAP = 150.0
_PARTICIPANT_BOX_W = 100.0
_PARTICIPANT_BOX_H = 40.0
_ACTOR_H = 60.0  # Stick figure is taller than a box.
_TOP_MARGIN = 20.0
_MSG_GAP = 40.0
_ACTIVATION_WIDTH = 10.0
_NOTE_WIDTH = 120.0
_NOTE_HEIGHT = 30.0
_NOTE_PAD = 5.0
_FRAGMENT_PAD = 10.0
_FRAGMENT_HEADER_H = 25.0
_FONT_SIZE = 14.0
_BOTTOM_MARGIN = 20.0

@dataclass
class ParticipantLayout:
    """Positioned participant."""

    id: str
    label: str
    is_actor: bool
    cx: float  # Center x of lifeline.
    box_x: float
    box_y: float
    box_w: float
    box_h: float

@dataclass
class MessageLayout:
    """Positioned message arrow."""

    sender_x: float
    receiver_x: float
    y: float
    text: str
    msg_type: str  # MessageType value string.
    is_self: bool = False

@dataclass
class ActivationLayout:
    """An activation rectangle on a lifeline."""

    participant_cx: float
    y_start: float
    y_end: float
    width: float = _ACTIVATION_WIDTH
    offset: int = 0  # For stacked activations.

@dataclass
class NoteLayout:
    """Positioned note box."""

    x: float
    y: float
    width: float
    height: float
    text: str

@dataclass
class FragmentLayout:
    """Positioned fragment (loop/alt/opt) box."""

    frag_type: str
    label: str
    x: float
    y: float
    width: float
    height: float
    sections: list["FragmentSection"] = field(default_factory=list)

@dataclass
class FragmentSection:
    """A section within a fragment (e.g. else clause in alt)."""

    label: str
    y: float  # Y position of section divider line.

@dataclass
class SequenceLayout:
    """Complete layout result for a sequence diagram."""

    width: float
    height: float
    participants: list[ParticipantLayout]
    messages: list[MessageLayout]
    activations: list[ActivationLayout]
    notes: list[NoteLayout]
    fragments: list[FragmentLayout]
    lifeline_bottom: float  # Y coordinate where lifelines end.
    origin_x: float = 0.0  # Leftmost x coordinate of content.

def layout_sequence(
    diagram: SequenceDiagram,
    measure_fn: MeasureFn | None = None,
) -> SequenceLayout:
    """Compute layout positions for all sequence diagram elements.

    Args:
        diagram: The parsed SequenceDiagram IR.
        measure_fn: Optional text measurement function (text, font_size) -> (w, h).

    Returns:
        A SequenceLayout with all positioned elements.
    """
    if measure_fn is None:
        def measure_fn(text: str, size: float) -> tuple[float, float]:
            return (len(text) * size * 0.6, size * 1.2)

    # --- 1. Position participants horizontally ---
    participants_layout: list[ParticipantLayout] = []
    participant_cx: dict[str, float] = {}

    for i, p in enumerate(diagram.participants):
        text_w, text_h = measure_fn(p.label, _FONT_SIZE)
        box_w = max(_PARTICIPANT_BOX_W, text_w + 20)
        box_h = _ACTOR_H if p.is_actor else _PARTICIPANT_BOX_H
        cx = _TOP_MARGIN + box_w / 2 + i * (_PARTICIPANT_GAP + box_w)
        # Adjust: use fixed gap between centers for simplicity.
        cx = _TOP_MARGIN + _PARTICIPANT_BOX_W / 2 + i * _PARTICIPANT_GAP

        participant_cx[p.id] = cx
        participants_layout.append(ParticipantLayout(
            id=p.id,
            label=p.label,
            is_actor=p.is_actor,
            cx=cx,
            box_x=cx - box_w / 2,
            box_y=_TOP_MARGIN,
            box_w=box_w,
            box_h=box_h,
        ))

    # Y cursor starts below participant boxes.
    max_box_bottom = max(
        (pl.box_y + pl.box_h for pl in participants_layout),
        default=_TOP_MARGIN + _PARTICIPANT_BOX_H,
    )
    y_cursor = max_box_bottom + _MSG_GAP

    # --- 2. Process items sequentially ---
    messages_layout: list[MessageLayout] = []
    notes_layout: list[NoteLayout] = []
    fragments_layout: list[FragmentLayout] = []

    # Activation tracking: stack per participant.
    activation_stacks: dict[str, list[float]] = {
        p.id: [] for p in diagram.participants
    }
    activations_layout: list[ActivationLayout] = []

    def _process_items(
        items: tuple, y_start: float,
    ) -> float:
        """Process a list of items, returning the final y_cursor."""
        nonlocal messages_layout, notes_layout, fragments_layout
        y = y_start

        for item in items:
            if isinstance(item, Message):
                y = _process_message(item, y)
            elif isinstance(item, Note):
                y = _process_note(item, y)
            elif isinstance(item, Fragment):
                y = _process_fragment(item, y)

        return y

    def _process_message(msg: Message, y: float) -> float:
        """Layout a message and return next y."""
        # Self-messages (activate/deactivate commands) don't draw arrows.
        if msg.sender == msg.receiver and msg.text == "":
            # Pure activation/deactivation command.
            if msg.activate:
                activation_stacks[msg.sender].append(y)
            if msg.deactivate and activation_stacks.get(msg.receiver):
                y_start_act = activation_stacks[msg.receiver].pop()
                offset = len(activation_stacks[msg.receiver])
                activations_layout.append(ActivationLayout(
                    participant_cx=participant_cx[msg.receiver],
                    y_start=y_start_act,
                    y_end=y,
                    offset=offset,
                ))
            return y

        sx = participant_cx.get(msg.sender, 0)
        rx = participant_cx.get(msg.receiver, 0)
        is_self = msg.sender == msg.receiver

        messages_layout.append(MessageLayout(
            sender_x=sx,
            receiver_x=rx,
            y=y,
            text=msg.text,
            msg_type=msg.msg_type.value,
            is_self=is_self,
        ))

        # Handle activation shorthand.
        if msg.activate:
            activation_stacks.setdefault(msg.receiver, []).append(y)
        if msg.deactivate:
            stk = activation_stacks.get(msg.receiver, [])
            if stk:
                y_start_act = stk.pop()
                offset = len(stk)
                activations_layout.append(ActivationLayout(
                    participant_cx=participant_cx[msg.receiver],
                    y_start=y_start_act,
                    y_end=y,
                    offset=offset,
                ))

        step = _MSG_GAP * 1.5 if is_self else _MSG_GAP
        return y + step

    def _process_note(note: Note, y: float) -> float:
        """Layout a note and return next y."""
        # Compute note position based on participants and position.
        # Split on <br/> to measure each line independently.
        lines = note.text.split("<br/>")
        line_widths = [measure_fn(line, _FONT_SIZE)[0] for line in lines]
        text_w = max(line_widths) if line_widths else 0
        single_h = measure_fn("X", _FONT_SIZE)[1]
        text_h = len(lines) * single_h
        nw = max(_NOTE_WIDTH, text_w + 2 * _NOTE_PAD)
        nh = max(_NOTE_HEIGHT, text_h + 2 * _NOTE_PAD)

        if note.position == NotePosition.OVER:
            if len(note.participants) == 2:
                cx1 = participant_cx.get(note.participants[0], 0)
                cx2 = participant_cx.get(note.participants[1], 0)
                center = (cx1 + cx2) / 2
                nw = max(nw, abs(cx2 - cx1) + 20)
            else:
                center = participant_cx.get(note.participants[0], 0)
            nx = center - nw / 2
        elif note.position == NotePosition.LEFT:
            cx = participant_cx.get(note.participants[0], 0)
            nx = cx - nw - 10
        else:  # RIGHT
            cx = participant_cx.get(note.participants[0], 0)
            nx = cx + 10

        notes_layout.append(NoteLayout(
            x=nx, y=y, width=nw, height=nh, text=note.text,
        ))
        return y + nh + _NOTE_PAD

    def _process_fragment(frag: Fragment, y: float) -> float:
        """Layout a fragment box and return next y."""
        # Compute fragment bounding box.
        frag_y_start = y
        y += _FRAGMENT_HEADER_H

        # Process items inside the fragment.
        y = _process_items(frag.items, y)

        # Determine x bounds: span all participants.
        all_cx = list(participant_cx.values())
        if all_cx:
            frag_x = min(all_cx) - _PARTICIPANT_BOX_W / 2 - _FRAGMENT_PAD
            frag_w = (
                max(all_cx) - min(all_cx)
                + _PARTICIPANT_BOX_W
                + 2 * _FRAGMENT_PAD
            )
        else:
            frag_x = 0
            frag_w = 200

        frag_h = y - frag_y_start + _FRAGMENT_PAD

        fl = FragmentLayout(
            frag_type=frag.frag_type.value,
            label=frag.label,
            x=frag_x,
            y=frag_y_start,
            width=frag_w,
            height=frag_h,
        )

        fragments_layout.append(fl)
        return y + _FRAGMENT_PAD

    y_cursor = _process_items(diagram.items, y_cursor)

    # Close any remaining activations.
    for pid, stack in activation_stacks.items():
        while stack:
            y_start_act = stack.pop()
            activations_layout.append(ActivationLayout(
                participant_cx=participant_cx[pid],
                y_start=y_start_act,
                y_end=y_cursor,
                offset=len(stack),
            ))

    lifeline_bottom = y_cursor + _BOTTOM_MARGIN

    # Total diagram dimensions.
    if participants_layout:
        total_w = max(
            pl.cx + _PARTICIPANT_BOX_W / 2 + _TOP_MARGIN
            for pl in participants_layout
        )
    else:
        total_w = 200.0

    # Track bounding box to encompass all content.
    min_left = 0.0

    # Expand to encompass notes that extend beyond participant positions.
    for nl in notes_layout:
        right = nl.x + nl.width
        if right > total_w:
            total_w = right + _TOP_MARGIN
        if nl.x < min_left:
            min_left = nl.x

    # Expand to encompass message label text widths.
    for ml in messages_layout:
        if ml.text:
            msg_lines = ml.text.split("<br/>")
            longest_line = max(msg_lines, key=len) if msg_lines else ml.text
            label_w = len(longest_line) * _FONT_SIZE * 0.6
            mid_x = (ml.sender_x + ml.receiver_x) / 2
            if ml.is_self:
                mid_x = ml.sender_x + 25
            label_right = mid_x + label_w / 2
            label_left = mid_x - label_w / 2
            if label_right > total_w:
                total_w = label_right + _TOP_MARGIN
            if label_left < min_left:
                min_left = label_left

    # Adjust total width to account for negative origin.
    total_w = total_w - min_left
    total_h = lifeline_bottom + _BOTTOM_MARGIN

    return SequenceLayout(
        width=total_w,
        height=total_h,
        participants=participants_layout,
        messages=messages_layout,
        activations=activations_layout,
        notes=notes_layout,
        fragments=fragments_layout,
        lifeline_bottom=lifeline_bottom,
        origin_x=min_left,
    )
