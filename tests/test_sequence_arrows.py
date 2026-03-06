"""Tests for issue #62: Sequence diagram --) arrow type support."""

from pathlib import Path

from merm.ir.sequence import MessageType
from merm.parser.sequence import (
    _ARROW_PATTERNS,
    _MESSAGE_RE,
    parse_sequence,
)


class TestParserRecognizesDashedAsync:
    """Verify the parser handles the --) arrow syntax."""

    def test_parse_single_dashed_async_message(self):
        """Parse B--)A produces correct Message."""
        text = "sequenceDiagram\n    B--)A: Dotted with open arrow"
        diagram = parse_sequence(text)
        messages = [item for item in diagram.items]
        assert len(messages) == 1
        msg = messages[0]
        assert msg.sender == "B"
        assert msg.receiver == "A"
        assert msg.text == "Dotted with open arrow"
        assert msg.msg_type == MessageType.DASHED_ASYNC

    def test_parse_arrows_mmd_returns_six_messages(self):
        """Parse all 6 arrow lines -- verify 6 Messages."""
        text = """\
sequenceDiagram
    participant A
    participant B
    A->>B: Solid with arrowhead
    B-->>A: Dotted with arrowhead
    A-xB: Solid with cross
    B--xA: Dotted with cross
    A-)B: Solid with open arrow
    B--)A: Dotted with open arrow
"""
        diagram = parse_sequence(text)
        messages = [item for item in diagram.items]
        assert len(messages) == 6

        expected_types = [
            MessageType.SOLID_ARROW,
            MessageType.DASHED_ARROW,
            MessageType.SOLID_CROSS,
            MessageType.DASHED_CROSS,
            MessageType.ASYNC,
            MessageType.DASHED_ASYNC,
        ]
        actual_types = [m.msg_type for m in messages]
        assert actual_types == expected_types

    def test_all_six_types_are_distinct(self):
        """Each arrow type maps to a distinct MessageType."""
        text = """\
sequenceDiagram
    participant A
    participant B
    A->>B: msg1
    B-->>A: msg2
    A-xB: msg3
    B--xA: msg4
    A-)B: msg5
    B--)A: msg6
"""
        diagram = parse_sequence(text)
        messages = list(diagram.items)
        types = [m.msg_type for m in messages]
        assert len(set(types)) == 6


class TestArrowPatternOrdering:
    """Verify --) does not partially match --> or -)."""

    def test_dashed_async_before_dashed_open_in_patterns(self):
        """--) before --> in _ARROW_PATTERNS."""
        arrows = [pat for pat, _ in _ARROW_PATTERNS]
        idx_dashed_async = arrows.index("--)")
        idx_dashed_open = arrows.index("-->")
        assert idx_dashed_async < idx_dashed_open

    def test_dashed_async_before_async_in_patterns(self):
        """--) before -) in _ARROW_PATTERNS."""
        arrows = [pat for pat, _ in _ARROW_PATTERNS]
        idx_dashed_async = arrows.index("--)")
        idx_async = arrows.index("-)")
        assert idx_dashed_async < idx_async

    def test_regex_matches_dashed_async(self):
        """The message regex must match --) arrow syntax."""
        m = _MESSAGE_RE.match("B--)A: Dotted with open arrow")
        assert m is not None
        assert m.group("arrow") == "--)"

    def test_regex_does_not_confuse_with_dashed_open(self):
        """--) must not match as --> with leftover ')'."""
        m = _MESSAGE_RE.match("B--)A: test")
        assert m is not None
        assert m.group("arrow") == "--)"
        assert m.group("receiver") == "A"


class TestIntegrationArrowsRendering:
    """Integration: Full arrows.mmd render produces 6 groups."""

    def test_render_arrows_mmd_has_six_messages(self):
        """Render arrows.mmd to SVG, count seq-message groups."""
        from merm import render_diagram

        text = """\
sequenceDiagram
    participant A
    participant B
    A->>B: Solid with arrowhead
    B-->>A: Dotted with arrowhead
    A-xB: Solid with cross
    B--xA: Dotted with cross
    A-)B: Solid with open arrow
    B--)A: Dotted with open arrow
"""
        svg = render_diagram(text)
        count = svg.count('class="seq-message"')
        assert count == 6

    def test_all_messages_have_marker_end(self):
        """Every message group has a marker-end attribute."""
        from merm import render_diagram

        text = """\
sequenceDiagram
    participant A
    participant B
    A->>B: Solid with arrowhead
    B-->>A: Dotted with arrowhead
    A-xB: Solid with cross
    B--xA: Dotted with cross
    A-)B: Solid with open arrow
    B--)A: Dotted with open arrow
"""
        svg = render_diagram(text)
        assert svg.count("marker-end") >= 6

    def test_dashed_async_renders_with_dash_array(self):
        """--) arrow renders with stroke-dasharray."""
        from merm import render_diagram

        text = """\
sequenceDiagram
    participant A
    participant B
    B--)A: Dotted with open arrow
"""
        svg = render_diagram(text)
        assert "stroke-dasharray" in svg


class TestExistingDiagramsStillParse:
    """Ensure other sequence diagrams still parse correctly."""

    def test_basic_mmd(self):
        """basic.mmd should still parse without errors."""
        basic_path = (
            Path(__file__).parent
            / "fixtures" / "corpus" / "sequence" / "basic.mmd"
        )
        if basic_path.exists():
            text = basic_path.read_text()
            diagram = parse_sequence(text)
            assert len(diagram.participants) > 0
            assert len(diagram.items) > 0

    def test_activations_mmd(self):
        """activations.mmd should still parse without errors."""
        act_path = (
            Path(__file__).parent
            / "fixtures" / "corpus" / "sequence"
            / "activations.mmd"
        )
        if act_path.exists():
            text = act_path.read_text()
            diagram = parse_sequence(text)
            assert len(diagram.participants) > 0
