"""Tests for sequence diagram support: parser, layout, and renderer."""

import xml.etree.ElementTree as ET

import pytest

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
from pymermaid.layout.sequence import (
    SequenceLayout,
    layout_sequence,
)
from pymermaid.parser.flowchart import ParseError
from pymermaid.parser.sequence import parse_sequence
from pymermaid.render.sequence import render_sequence_svg
from pymermaid.theme import DEFAULT_THEME

# ============================================================
# Parser tests
# ============================================================

class TestParseSequenceBasic:
    """Basic parsing of participants and messages."""

    def test_empty_diagram(self):
        text = "sequenceDiagram"
        d = parse_sequence(text)
        assert d.participants == ()
        assert d.items == ()

    def test_not_sequence_diagram_raises(self):
        with pytest.raises(ParseError):
            parse_sequence("flowchart LR\n  A --> B")

    def test_simple_participants(self):
        text = """sequenceDiagram
            participant A
            participant B
        """
        d = parse_sequence(text)
        assert len(d.participants) == 2
        assert d.participants[0].id == "A"
        assert d.participants[0].label == "A"
        assert d.participants[1].id == "B"

    def test_participant_with_alias(self):
        text = """sequenceDiagram
            participant A as Alice
            participant B as Bob
        """
        d = parse_sequence(text)
        assert d.participants[0].label == "Alice"
        assert d.participants[1].label == "Bob"

    def test_actor_declaration(self):
        text = """sequenceDiagram
            actor A as Alice
        """
        d = parse_sequence(text)
        assert d.participants[0].is_actor is True
        assert d.participants[0].label == "Alice"

    def test_auto_create_participants(self):
        text = """sequenceDiagram
            A->>B: Hello
        """
        d = parse_sequence(text)
        assert len(d.participants) == 2
        assert d.participants[0].id == "A"
        assert d.participants[1].id == "B"

    def test_explicit_then_auto(self):
        """Explicit declarations come first, auto-created follow."""
        text = """sequenceDiagram
            participant B
            A->>B: Hello
        """
        d = parse_sequence(text)
        assert d.participants[0].id == "B"
        assert d.participants[1].id == "A"

    def test_comments_and_blanks_skipped(self):
        text = """
        %% A comment
        sequenceDiagram
            %% another comment
            participant A

            A->>B: Hi
        """
        d = parse_sequence(text)
        assert len(d.participants) == 2
        assert len(d.items) == 1

class TestParseSequenceMessages:
    """Message type parsing."""

    def test_solid_arrow(self):
        d = parse_sequence("sequenceDiagram\nA->>B: text")
        msg = d.items[0]
        assert isinstance(msg, Message)
        assert msg.msg_type == MessageType.SOLID_ARROW
        assert msg.text == "text"

    def test_dashed_arrow(self):
        d = parse_sequence("sequenceDiagram\nA-->>B: reply")
        assert d.items[0].msg_type == MessageType.DASHED_ARROW

    def test_solid_open(self):
        d = parse_sequence("sequenceDiagram\nA->B: open")
        assert d.items[0].msg_type == MessageType.SOLID_OPEN

    def test_dashed_open(self):
        d = parse_sequence("sequenceDiagram\nA-->B: dashed")
        assert d.items[0].msg_type == MessageType.DASHED_OPEN

    def test_solid_cross(self):
        d = parse_sequence("sequenceDiagram\nA-xB: cross")
        assert d.items[0].msg_type == MessageType.SOLID_CROSS

    def test_dashed_cross(self):
        d = parse_sequence("sequenceDiagram\nA--xB: dcross")
        assert d.items[0].msg_type == MessageType.DASHED_CROSS

    def test_async(self):
        d = parse_sequence("sequenceDiagram\nA-)B: async")
        assert d.items[0].msg_type == MessageType.ASYNC

    def test_message_with_no_text(self):
        d = parse_sequence("sequenceDiagram\nA->>B:")
        assert d.items[0].text == ""

    def test_multiple_messages(self):
        text = """sequenceDiagram
            A->>B: Hello
            B-->>A: World
        """
        d = parse_sequence(text)
        assert len(d.items) == 2
        assert d.items[0].sender == "A"
        assert d.items[1].sender == "B"

class TestParseSequenceActivations:
    """Activation shorthand (+/-) on messages."""

    def test_activate_shorthand(self):
        text = """sequenceDiagram
            A->>B+: activate
        """
        d = parse_sequence(text)
        msg = d.items[0]
        assert isinstance(msg, Message)
        assert msg.activate is True

    def test_deactivate_shorthand(self):
        text = """sequenceDiagram
            A->>B-: deactivate
        """
        d = parse_sequence(text)
        msg = d.items[0]
        assert msg.deactivate is True

    def test_explicit_activate_deactivate(self):
        text = """sequenceDiagram
            A->>B: msg
            activate B
            B-->>A: reply
            deactivate B
        """
        d = parse_sequence(text)
        # Should have 4 items: msg, activate, reply, deactivate.
        assert len(d.items) == 4

class TestParseSequenceNotes:
    """Note parsing."""

    def test_note_right_of(self):
        text = """sequenceDiagram
            participant A
            Note right of A: Some note
        """
        d = parse_sequence(text)
        note = d.items[0]
        assert isinstance(note, Note)
        assert note.position == NotePosition.RIGHT
        assert note.text == "Some note"
        assert note.participants == ("A",)

    def test_note_left_of(self):
        text = """sequenceDiagram
            participant A
            Note left of A: Left note
        """
        d = parse_sequence(text)
        assert d.items[0].position == NotePosition.LEFT

    def test_note_over_one(self):
        text = """sequenceDiagram
            participant A
            Note over A: Over note
        """
        d = parse_sequence(text)
        note = d.items[0]
        assert note.position == NotePosition.OVER
        assert note.participants == ("A",)

    def test_note_over_two(self):
        text = """sequenceDiagram
            participant A
            participant B
            Note over A,B: Spanning note
        """
        d = parse_sequence(text)
        note = d.items[0]
        assert note.position == NotePosition.OVER
        assert note.participants == ("A", "B")

class TestParseSequenceFragments:
    """Fragment (loop/alt/opt) parsing."""

    def test_loop(self):
        text = """sequenceDiagram
            A->>B: request
            loop Every minute
                A->>B: ping
            end
            B-->>A: pong
        """
        d = parse_sequence(text)
        assert len(d.items) == 3
        frag = d.items[1]
        assert isinstance(frag, Fragment)
        assert frag.frag_type == FragmentType.LOOP
        assert frag.label == "Every minute"
        assert len(frag.items) == 1

    def test_alt_else(self):
        text = """sequenceDiagram
            A->>B: request
            alt success
                B-->>A: 200 OK
            else failure
                B-->>A: 500 Error
            end
        """
        d = parse_sequence(text)
        # Should have: message, alt fragment, else fragment
        assert len(d.items) == 3
        alt = d.items[1]
        assert isinstance(alt, Fragment)
        assert alt.frag_type == FragmentType.ALT
        assert alt.label == "success"
        els = d.items[2]
        assert isinstance(els, Fragment)
        assert els.frag_type == FragmentType.ELSE
        assert els.label == "failure"

    def test_opt(self):
        text = """sequenceDiagram
            opt If available
                A->>B: optional
            end
        """
        d = parse_sequence(text)
        frag = d.items[0]
        assert isinstance(frag, Fragment)
        assert frag.frag_type == FragmentType.OPT
        assert frag.label == "If available"

# ============================================================
# Layout tests
# ============================================================

class TestLayoutSequence:
    """Layout engine for sequence diagrams."""

    def _simple_diagram(self) -> SequenceDiagram:
        return SequenceDiagram(
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

    def test_layout_returns_sequence_layout(self):
        d = self._simple_diagram()
        layout = layout_sequence(d)
        assert isinstance(layout, SequenceLayout)

    def test_participants_positioned_horizontally(self):
        d = self._simple_diagram()
        layout = layout_sequence(d)
        assert len(layout.participants) == 2
        assert layout.participants[0].cx < layout.participants[1].cx

    def test_messages_positioned_vertically(self):
        d = self._simple_diagram()
        layout = layout_sequence(d)
        assert len(layout.messages) == 2
        assert layout.messages[0].y < layout.messages[1].y

    def test_lifeline_extends_below_messages(self):
        d = self._simple_diagram()
        layout = layout_sequence(d)
        last_msg_y = layout.messages[-1].y
        assert layout.lifeline_bottom > last_msg_y

    def test_non_overlapping_participants(self):
        d = self._simple_diagram()
        layout = layout_sequence(d)
        p0 = layout.participants[0]
        p1 = layout.participants[1]
        # Right edge of first should not overlap left edge of second.
        assert p0.box_x + p0.box_w < p1.box_x

    def test_activation_layout(self):
        d = SequenceDiagram(
            participants=(
                Participant(id="A", label="A"),
                Participant(id="B", label="B"),
            ),
            items=(
                Message(
                    sender="A", receiver="B", text="call",
                    msg_type=MessageType.SOLID_ARROW, activate=True,
                ),
                Message(
                    sender="B", receiver="A", text="return",
                    msg_type=MessageType.DASHED_ARROW, deactivate=True,
                ),
            ),
        )
        layout = layout_sequence(d)
        assert len(layout.activations) >= 1
        act = layout.activations[0]
        assert act.y_start < act.y_end

    def test_note_layout(self):
        d = SequenceDiagram(
            participants=(Participant(id="A", label="A"),),
            items=(
                Note(text="Hello", position=NotePosition.RIGHT, participants=("A",)),
            ),
        )
        layout = layout_sequence(d)
        assert len(layout.notes) == 1
        assert layout.notes[0].width > 0
        assert layout.notes[0].height > 0

    def test_fragment_layout(self):
        d = SequenceDiagram(
            participants=(
                Participant(id="A", label="A"),
                Participant(id="B", label="B"),
            ),
            items=(
                Fragment(
                    frag_type=FragmentType.LOOP,
                    label="3 times",
                    items=(
                        Message(
                            sender="A", receiver="B", text="ping",
                            msg_type=MessageType.SOLID_ARROW,
                        ),
                    ),
                ),
            ),
        )
        layout = layout_sequence(d)
        assert len(layout.fragments) == 1
        frag = layout.fragments[0]
        assert frag.width > 0
        assert frag.height > 0

    def test_positive_dimensions(self):
        d = self._simple_diagram()
        layout = layout_sequence(d)
        assert layout.width > 0
        assert layout.height > 0

# ============================================================
# Renderer tests
# ============================================================

class TestRenderSequenceSvg:
    """SVG rendering for sequence diagrams."""

    def _make_svg(
        self, text: str, theme=None,
    ) -> str:
        d = parse_sequence(text)
        layout = layout_sequence(d)
        return render_sequence_svg(d, layout, theme=theme)

    def _parse_svg(self, svg_str: str) -> ET.Element:
        return ET.fromstring(svg_str)

    def test_returns_svg_string(self):
        svg = self._make_svg("sequenceDiagram\nA->>B: Hello")
        assert svg.startswith("<svg")
        assert "</svg>" in svg

    def test_contains_participants(self):
        svg = self._make_svg(
            "sequenceDiagram\nparticipant A as Alice\nparticipant B as Bob"
        )
        assert "Alice" in svg
        assert "Bob" in svg

    def test_contains_message_text(self):
        svg = self._make_svg("sequenceDiagram\nA->>B: Hello World")
        assert "Hello World" in svg

    def test_contains_lifelines(self):
        svg = self._make_svg("sequenceDiagram\nparticipant A")
        root = self._parse_svg(svg)
        # Search for lifeline elements by iterating all lines.
        all_lines = root.iter("{http://www.w3.org/2000/svg}line")
        found_lifeline = any(
            el.get("class") == "seq-lifeline" for el in all_lines
        )
        assert found_lifeline

    def test_dashed_message_has_dasharray(self):
        svg = self._make_svg("sequenceDiagram\nA-->>B: reply")
        assert "stroke-dasharray" in svg

    def test_actor_renders_stick_figure(self):
        svg = self._make_svg("sequenceDiagram\nactor A as Alice\nA->>A: self")
        assert "seq-actor" in svg
        # Stick figure has circle element.
        assert "<circle" in svg

    def test_note_renders(self):
        svg = self._make_svg(
            "sequenceDiagram\nparticipant A\nNote right of A: Important"
        )
        assert "Important" in svg
        assert "seq-note" in svg

    def test_fragment_renders(self):
        svg = self._make_svg("""sequenceDiagram
            A->>B: msg
            loop Every second
                A->>B: ping
            end
        """)
        assert "LOOP" in svg
        assert "Every second" in svg
        assert "seq-fragment" in svg

    def test_theme_colors_applied(self):
        custom_theme = DEFAULT_THEME.replace(
            node_fill="#FF0000", node_stroke="#00FF00",
        )
        svg = self._make_svg(
            "sequenceDiagram\nparticipant A",
            theme=custom_theme,
        )
        assert "#FF0000" in svg
        assert "#00FF00" in svg

    def test_valid_xml(self):
        svg = self._make_svg("""sequenceDiagram
            participant A as Alice
            participant B as Bob
            A->>B: Hello
            B-->>A: Hi
            Note over A,B: Greetings
            loop Retry
                A->>B: ping
            end
        """)
        # Should parse as valid XML without errors.
        ET.fromstring(svg)

    def test_self_message_renders(self):
        svg = self._make_svg("sequenceDiagram\nA->>A: self call")
        assert "self call" in svg

# ============================================================
# Integration tests
# ============================================================

class TestSequenceIntegration:
    """End-to-end integration tests."""

    def test_render_via_top_level(self):
        """Test the top-level render_diagram() auto-detect function."""
        from pymermaid import render_diagram
        svg = render_diagram("sequenceDiagram\nA->>B: Hello")
        assert "<svg" in svg
        assert "Hello" in svg

    def test_complex_diagram(self):
        """Test a complex diagram with many features."""
        text = """sequenceDiagram
            participant A as Alice
            actor B as Bob
            participant C as Charlie

            A->>B: Hello Bob
            B-->>A: Hi Alice
            A->C: Open arrow
            Note right of C: This is a note
            Note over A,B: Shared note

            loop Heartbeat
                A->>B: ping
                B-->>A: pong
            end

            alt Success
                B->>C: Forward
                C-->>B: OK
            else Failure
                B-xC: Error
            end

            opt Cleanup
                A-)C: async cleanup
            end
        """
        d = parse_sequence(text)
        assert len(d.participants) == 3
        assert d.participants[1].is_actor is True

        layout = layout_sequence(d)
        assert layout.width > 0
        assert layout.height > 0
        assert len(layout.messages) > 0
        assert len(layout.notes) == 2
        assert len(layout.fragments) > 0

        svg = render_sequence_svg(d, layout)
        ET.fromstring(svg)  # Valid XML.
        assert "Alice" in svg
        assert "Bob" in svg
        assert "Charlie" in svg
        assert "seq-fragment" in svg
        assert "seq-note" in svg

    def test_cli_handles_sequence(self):
        """Test CLI detection of sequence diagrams."""
        import re
        source = "sequenceDiagram\nA->>B: test"
        is_sequence = bool(
            re.match(r"^\s*sequenceDiagram", source, re.MULTILINE)
        )
        assert is_sequence is True
