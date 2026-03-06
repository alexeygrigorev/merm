"""Tests for issue 61: Sequence diagram activation syntax produces empty SVG.

Verifies that Mermaid's +/- activation shorthand (e.g., ->>+Bob) is parsed
correctly and renders activation boxes in SVG output.
"""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from merm.ir.sequence import Message, MessageType
from merm.layout.sequence import layout_sequence
from merm.parser.sequence import parse_sequence
from merm.render.sequence import render_sequence_svg

ACTIVATIONS_MMD = Path("tests/fixtures/corpus/sequence/activations.mmd")


class TestParserActivationSyntax:
    """Unit tests for parser handling of +/- activation markers."""

    def test_activate_before_receiver(self):
        """Parse 'Alice->>+Bob: Hello Bob' -- activate=True, deactivate=False."""
        text = "sequenceDiagram\n    Alice->>+Bob: Hello Bob"
        d = parse_sequence(text)
        assert len(d.items) == 1
        msg = d.items[0]
        assert isinstance(msg, Message)
        assert msg.sender == "Alice"
        assert msg.receiver == "Bob"
        assert msg.text == "Hello Bob"
        assert msg.activate is True
        assert msg.deactivate is False
        assert msg.msg_type == MessageType.SOLID_ARROW

    def test_deactivate_before_receiver(self):
        """Parse 'Bob-->>-Alice: All done' -- activate=False, deactivate=True."""
        text = "sequenceDiagram\n    Bob-->>-Alice: All done"
        d = parse_sequence(text)
        assert len(d.items) == 1
        msg = d.items[0]
        assert isinstance(msg, Message)
        assert msg.sender == "Bob"
        assert msg.receiver == "Alice"
        assert msg.activate is False
        assert msg.deactivate is True
        assert msg.msg_type == MessageType.DASHED_ARROW

    def test_no_activation_marker(self):
        """Parse 'Alice->>Bob: Hello' -- no +/-, both flags False (regression)."""
        text = "sequenceDiagram\n    Alice->>Bob: Hello"
        d = parse_sequence(text)
        msg = d.items[0]
        assert msg.activate is False
        assert msg.deactivate is False


class TestFullDiagramParse:
    """Parse the activations.mmd fixture and verify structure."""

    @pytest.fixture()
    def diagram(self):
        text = ACTIVATIONS_MMD.read_text()
        return parse_sequence(text)

    def test_three_participants(self, diagram):
        assert len(diagram.participants) == 3
        ids = [p.id for p in diagram.participants]
        assert ids == ["Alice", "Bob", "Charlie"]

    def test_four_messages(self, diagram):
        assert len(diagram.items) == 4
        for item in diagram.items:
            assert isinstance(item, Message)

    def test_activation_flags(self, diagram):
        msgs = diagram.items
        # Message 1: Alice->>+Bob -- activate
        assert msgs[0].activate is True
        assert msgs[0].deactivate is False
        # Message 2: Bob->>+Charlie -- activate
        assert msgs[1].activate is True
        assert msgs[1].deactivate is False
        # Message 3: Charlie-->>-Bob -- deactivate
        assert msgs[2].activate is False
        assert msgs[2].deactivate is True
        # Message 4: Bob-->>-Alice -- deactivate
        assert msgs[3].activate is False
        assert msgs[3].deactivate is True


class TestLayoutActivationBoxes:
    """Verify layout produces activation boxes for activations.mmd."""

    def test_activation_layout_nonempty(self):
        text = ACTIVATIONS_MMD.read_text()
        d = parse_sequence(text)
        layout = layout_sequence(d)
        assert len(layout.activations) > 0, "Expected activation boxes in layout"

    def test_activation_boxes_have_correct_cx(self):
        text = ACTIVATIONS_MMD.read_text()
        d = parse_sequence(text)
        layout = layout_sequence(d)
        # Build map of participant cx values from layout
        participant_cx_set = {p.cx for p in layout.participants}
        # Each activation box cx should correspond to a participant
        for act in layout.activations:
            assert act.participant_cx in participant_cx_set


class TestSVGRendering:
    """Integration: verify SVG output contains expected elements."""

    def test_svg_contains_participants_and_messages(self):
        text = ACTIVATIONS_MMD.read_text()
        d = parse_sequence(text)
        layout = layout_sequence(d)
        svg = render_sequence_svg(d, layout)
        root = ET.fromstring(svg)
        # SVG must be valid XML
        assert root.tag.endswith("svg")
        # All participant names must appear
        assert "Alice" in svg
        assert "Bob" in svg
        assert "Charlie" in svg
        # All message labels must appear
        assert "Hello Bob" in svg
        assert "Hi Charlie" in svg
        assert "Reply" in svg
        assert "All done" in svg

    def test_svg_has_activation_rectangles(self):
        text = ACTIVATIONS_MMD.read_text()
        d = parse_sequence(text)
        layout = layout_sequence(d)
        svg = render_sequence_svg(d, layout)
        # Activation boxes are rendered as rects with class seq-activation
        assert "seq-activation" in svg
