"""Tests for issue 59: Sequence diagram long message label clipping.

Verifies that participant spacing adapts dynamically to message label widths,
preventing text clipping and note/message overlap.
"""

from pathlib import Path

import pytest

from merm.ir.sequence import (
    Message,
    MessageType,
    Participant,
    SequenceDiagram,
)
from merm.layout.sequence import (
    _FONT_SIZE,
    _PARTICIPANT_GAP,
    SequenceLayout,
    layout_sequence,
)
from merm.parser.sequence import parse_sequence
from merm.render.sequence import render_sequence_svg

FIXTURES = Path(__file__).parent / "fixtures" / "github"


class TestDynamicParticipantSpacing:
    """Participant gap adapts to the longest message label between each pair."""

    def test_long_label_widens_gap(self):
        """A long message label between A and B should produce a wider gap
        than the default _PARTICIPANT_GAP."""
        long_text = "This is a very long message label that should widen the gap"
        d = SequenceDiagram(
            participants=(
                Participant(id="A", label="A"),
                Participant(id="B", label="B"),
            ),
            items=(
                Message(
                    sender="A", receiver="B", text=long_text,
                    msg_type=MessageType.SOLID_ARROW,
                ),
            ),
        )
        layout = layout_sequence(d)
        gap = layout.participants[1].cx - layout.participants[0].cx
        # The gap must be at least as wide as the label text.
        label_w = len(long_text) * _FONT_SIZE * 0.6
        assert gap >= label_w, (
            f"Gap {gap} is narrower than label width {label_w}"
        )

    def test_short_label_uses_default_gap(self):
        """Short labels should not blow up spacing -- gap stays near default."""
        d = SequenceDiagram(
            participants=(
                Participant(id="A", label="A"),
                Participant(id="B", label="B"),
            ),
            items=(
                Message(
                    sender="A", receiver="B", text="Hi",
                    msg_type=MessageType.SOLID_ARROW,
                ),
            ),
        )
        layout = layout_sequence(d)
        gap = layout.participants[1].cx - layout.participants[0].cx
        assert gap == pytest.approx(_PARTICIPANT_GAP, abs=1.0), (
            f"Short message gap {gap} should be close to default {_PARTICIPANT_GAP}"
        )

    def test_multi_hop_message_distributes_width(self):
        """A message spanning A->C (skipping B) should widen the gaps
        between A-B and B-C proportionally."""
        long_text = "X" * 60  # Very long label.
        d = SequenceDiagram(
            participants=(
                Participant(id="A", label="A"),
                Participant(id="B", label="B"),
                Participant(id="C", label="C"),
            ),
            items=(
                Message(
                    sender="A", receiver="C", text=long_text,
                    msg_type=MessageType.SOLID_ARROW,
                ),
            ),
        )
        layout = layout_sequence(d)
        total_span = layout.participants[2].cx - layout.participants[0].cx
        label_w = len(long_text) * _FONT_SIZE * 0.6
        assert total_span >= label_w, (
            f"Total span {total_span} is narrower than label width {label_w}"
        )

    def test_different_gaps_per_pair(self):
        """Different message widths between different pairs should produce
        different gap sizes."""
        d = SequenceDiagram(
            participants=(
                Participant(id="A", label="A"),
                Participant(id="B", label="B"),
                Participant(id="C", label="C"),
            ),
            items=(
                Message(
                    sender="A", receiver="B", text="short",
                    msg_type=MessageType.SOLID_ARROW,
                ),
                Message(
                    sender="B", receiver="C",
                    text="This is a much longer message label for B to C",
                    msg_type=MessageType.SOLID_ARROW,
                ),
            ),
        )
        layout = layout_sequence(d)
        gap_ab = layout.participants[1].cx - layout.participants[0].cx
        gap_bc = layout.participants[2].cx - layout.participants[1].cx
        # B-C gap should be wider than A-B gap.
        assert gap_bc > gap_ab, (
            f"B-C gap {gap_bc} should be wider than A-B gap {gap_ab}"
        )


class TestFlinkFixtures:
    """Test that the flink fixtures render with adequate spacing."""

    @pytest.fixture()
    def flink_late_event_layout(self) -> SequenceLayout:
        text = (FIXTURES / "flink_late_event.mmd").read_text()
        d = parse_sequence(text)
        return layout_sequence(d)

    @pytest.fixture()
    def flink_late_upsert_layout(self) -> SequenceLayout:
        text = (FIXTURES / "flink_late_upsert.mmd").read_text()
        d = parse_sequence(text)
        return layout_sequence(d)

    def test_flink_late_event_message_labels_fit(self, flink_late_event_layout):
        """All message labels in flink_late_event should fit between their
        sender and receiver participants."""
        layout = flink_late_event_layout
        for ml in layout.messages:
            if not ml.text or ml.is_self:
                continue
            msg_lines = ml.text.split("<br/>")
            line_widths = [len(line) * _FONT_SIZE * 0.6 for line in msg_lines]
            label_w = max(line_widths)
            available = abs(ml.receiver_x - ml.sender_x)
            assert available >= label_w, (
                f"Message '{ml.text}' label width {label_w:.0f} exceeds "
                f"available space {available:.0f}"
            )

    def test_flink_late_upsert_message_labels_fit(self, flink_late_upsert_layout):
        """All message labels in flink_late_upsert should fit between their
        sender and receiver participants."""
        layout = flink_late_upsert_layout
        for ml in layout.messages:
            if not ml.text or ml.is_self:
                continue
            msg_lines = ml.text.split("<br/>")
            line_widths = [len(line) * _FONT_SIZE * 0.6 for line in msg_lines]
            label_w = max(line_widths)
            available = abs(ml.receiver_x - ml.sender_x)
            assert available >= label_w, (
                f"Message '{ml.text}' label width {label_w:.0f} exceeds "
                f"available space {available:.0f}"
            )

    def test_flink_late_event_participants_spaced(self, flink_late_event_layout):
        """Adjacent participants should have enough horizontal distance
        for the longest message label between them."""
        layout = flink_late_event_layout
        for i in range(len(layout.participants) - 1):
            gap = layout.participants[i + 1].cx - layout.participants[i].cx
            assert gap >= _PARTICIPANT_GAP, (
                f"Gap between {layout.participants[i].id} and "
                f"{layout.participants[i + 1].id} is {gap:.0f}, "
                f"less than minimum {_PARTICIPANT_GAP}"
            )

    def test_flink_late_upsert_participants_spaced(self, flink_late_upsert_layout):
        layout = flink_late_upsert_layout
        for i in range(len(layout.participants) - 1):
            gap = layout.participants[i + 1].cx - layout.participants[i].cx
            assert gap >= _PARTICIPANT_GAP


class TestNoteMessageNonOverlap:
    """Notes should not overlap message labels at the same y-range."""

    def test_flink_late_event_no_note_message_overlap(self):
        """For each note in flink_late_event, its bounding box should not
        overlap any message label bounding box at the same y-range."""
        text = (FIXTURES / "flink_late_event.mmd").read_text()
        d = parse_sequence(text)
        layout = layout_sequence(d)

        for note in layout.notes:
            note_left = note.x
            note_right = note.x + note.width
            note_top = note.y
            note_bottom = note.y + note.height

            for ml in layout.messages:
                if not ml.text or ml.is_self:
                    continue
                # Message label is centered between sender and receiver.
                msg_lines = ml.text.split("<br/>")
                line_widths = [len(line) * _FONT_SIZE * 0.6 for line in msg_lines]
                label_w = max(line_widths)
                mid_x = (ml.sender_x + ml.receiver_x) / 2
                label_left = mid_x - label_w / 2
                label_right = mid_x + label_w / 2
                label_top = ml.y - _FONT_SIZE
                label_bottom = ml.y + 5

                # Check for overlap: rectangles overlap if they overlap
                # in both x and y dimensions.
                x_overlap = note_left < label_right and note_right > label_left
                y_overlap = note_top < label_bottom and note_bottom > label_top

                if x_overlap and y_overlap:
                    pytest.fail(
                        f"Note '{note.text[:30]}...' at x=[{note_left:.0f}, "
                        f"{note_right:.0f}] y=[{note_top:.0f}, {note_bottom:.0f}] "
                        f"overlaps message '{ml.text}' label at "
                        f"x=[{label_left:.0f}, {label_right:.0f}] "
                        f"y=[{label_top:.0f}, {label_bottom:.0f}]"
                    )


class TestRegressionNoBloat:
    """Existing simple diagrams should not have massively inflated dimensions."""

    def test_basic_diagram_reasonable_width(self):
        """A simple 2-participant diagram should not be excessively wide."""
        d = SequenceDiagram(
            participants=(
                Participant(id="A", label="Alice"),
                Participant(id="B", label="Bob"),
            ),
            items=(
                Message(
                    sender="A", receiver="B", text="Hello",
                    msg_type=MessageType.SOLID_ARROW,
                ),
                Message(
                    sender="B", receiver="A", text="Hi",
                    msg_type=MessageType.DASHED_ARROW,
                ),
            ),
        )
        layout = layout_sequence(d)
        # Width should be reasonable -- under 500px for a simple diagram.
        assert layout.width < 500, (
            f"Width {layout.width} is too large for basic diagram"
        )

    def test_three_participants_reasonable(self):
        """A simple 3-participant diagram should have reasonable dimensions."""
        d = SequenceDiagram(
            participants=(
                Participant(id="A", label="A"),
                Participant(id="B", label="B"),
                Participant(id="C", label="C"),
            ),
            items=(
                Message(
                    sender="A", receiver="B", text="msg1",
                    msg_type=MessageType.SOLID_ARROW,
                ),
                Message(
                    sender="B", receiver="C", text="msg2",
                    msg_type=MessageType.SOLID_ARROW,
                ),
            ),
        )
        layout = layout_sequence(d)
        assert layout.width < 600, f"Width {layout.width} is too large"


class TestFlinkSvgRendering:
    """Verify SVG output contains all message labels (no clipping at SVG level)."""

    def test_flink_late_event_all_labels_in_svg(self):
        text = (FIXTURES / "flink_late_event.mmd").read_text()
        d = parse_sequence(text)
        layout = layout_sequence(d)
        svg = render_sequence_svg(d, layout)

        # All message texts should appear in the SVG.
        expected_labels = [
            "Event A (ts=14:00:07, on time)",
            "Event A",
            "Event B (ts=14:00:04, 8s late)",
            "Event B",
            "INSERT (window=00:00, PU=79, trips=2)",
        ]
        for label in expected_labels:
            assert label in svg, f"Label '{label}' not found in SVG"

    def test_flink_late_upsert_all_labels_in_svg(self):
        text = (FIXTURES / "flink_late_upsert.mmd").read_text()
        d = parse_sequence(text)
        layout = layout_sequence(d)
        svg = render_sequence_svg(d, layout)

        expected_labels = [
            "Event A (ts=14:00:07, on time)",
            "Event B (ts=14:00:04, 20s late)",
            "INSERT (window=00:00, PU=79, trips=1)",
            "UPDATE (window=00:00, PU=79, trips=2)",
        ]
        for label in expected_labels:
            assert label in svg, f"Label '{label}' not found in SVG"
