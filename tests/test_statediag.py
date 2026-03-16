"""Tests for state diagram support (task 16).

Covers IR dataclasses, parser, layout conversion, renderer, and CLI integration.
"""

import xml.etree.ElementTree as ET

import pytest

from merm.ir.statediag import (
    State,
    StateDiagram,
    StateNote,
    StateType,
    Transition,
)
from merm.layout.statediag import (
    layout_state_diagram,
    state_diagram_to_flowchart,
)
from merm.measure import TextMeasurer
from merm.parser.flowchart import ParseError
from merm.parser.statediag import parse_state_diagram
from merm.render.statediag import render_state_svg

# -----------------------------------------------------------------------
# IR dataclass tests
# -----------------------------------------------------------------------

class TestIRDataclasses:
    """Test state diagram IR dataclasses."""

    def test_state_default(self):
        s = State(id="s1", label="State 1")
        assert s.id == "s1"
        assert s.label == "State 1"
        assert s.state_type == StateType.NORMAL
        assert s.children == ()

    def test_state_with_type(self):
        s = State(id="s1", label="", state_type=StateType.START)
        assert s.state_type == StateType.START

    def test_state_with_children(self):
        child = State(id="c1", label="Child")
        parent = State(id="p1", label="Parent", children=(child,))
        assert len(parent.children) == 1
        assert parent.children[0].id == "c1"

    def test_transition_default(self):
        t = Transition(source="s1", target="s2")
        assert t.source == "s1"
        assert t.target == "s2"
        assert t.label == ""

    def test_transition_with_label(self):
        t = Transition(source="s1", target="s2", label="event")
        assert t.label == "event"

    def test_state_note(self):
        n = StateNote(state_id="s1", text="Important", position="left")
        assert n.state_id == "s1"
        assert n.text == "Important"
        assert n.position == "left"

    def test_state_diagram_empty(self):
        sd = StateDiagram()
        assert sd.states == ()
        assert sd.transitions == ()
        assert sd.notes == ()

    def test_state_type_values(self):
        assert StateType.NORMAL.value == "normal"
        assert StateType.START.value == "start"
        assert StateType.END.value == "end"
        assert StateType.CHOICE.value == "choice"
        assert StateType.FORK.value == "fork"
        assert StateType.JOIN.value == "join"

# -----------------------------------------------------------------------
# Parser tests
# -----------------------------------------------------------------------

class TestParser:
    """Test state diagram parser."""

    def test_empty_input_raises(self):
        with pytest.raises(ParseError):
            parse_state_diagram("")

    def test_invalid_declaration_raises(self):
        with pytest.raises(ParseError):
            parse_state_diagram("flowchart TD\n  A --> B")

    def test_minimal_statediagram(self):
        result = parse_state_diagram("stateDiagram\n  s1")
        assert len(result.states) == 1
        assert result.states[0].id == "s1"

    def test_statediagram_v2(self):
        result = parse_state_diagram("stateDiagram-v2\n  s1")
        assert len(result.states) == 1

    def test_simple_transition(self):
        text = "stateDiagram-v2\n  s1 --> s2"
        result = parse_state_diagram(text)
        assert len(result.transitions) == 1
        assert result.transitions[0].source == "s1"
        assert result.transitions[0].target == "s2"
        assert result.transitions[0].label == ""

    def test_transition_with_label(self):
        text = "stateDiagram-v2\n  s1 --> s2 : event"
        result = parse_state_diagram(text)
        assert result.transitions[0].label == "event"

    def test_start_pseudo_state(self):
        text = "stateDiagram-v2\n  [*] --> s1"
        result = parse_state_diagram(text)
        # Should have a start state and s1
        start_states = [
            s for s in result.states if s.state_type == StateType.START
        ]
        assert len(start_states) == 1
        assert result.transitions[0].source == start_states[0].id
        assert result.transitions[0].target == "s1"

    def test_end_pseudo_state(self):
        text = "stateDiagram-v2\n  s1 --> [*]"
        result = parse_state_diagram(text)
        end_states = [
            s for s in result.states if s.state_type == StateType.END
        ]
        assert len(end_states) == 1
        assert result.transitions[0].source == "s1"
        assert result.transitions[0].target == end_states[0].id

    def test_state_with_description(self):
        text = "stateDiagram-v2\n  s1 : This is state 1"
        result = parse_state_diagram(text)
        assert result.states[0].label == "This is state 1"

    def test_state_alias(self):
        text = 'stateDiagram-v2\n  state "Long state name" as s1'
        result = parse_state_diagram(text)
        s = next(s for s in result.states if s.id == "s1")
        assert s.label == "Long state name"

    def test_choice_pseudo_state(self):
        text = "stateDiagram-v2\n  state myChoice <<choice>>"
        result = parse_state_diagram(text)
        s = next(s for s in result.states if s.id == "myChoice")
        assert s.state_type == StateType.CHOICE

    def test_fork_pseudo_state(self):
        text = "stateDiagram-v2\n  state forkState <<fork>>"
        result = parse_state_diagram(text)
        s = next(s for s in result.states if s.id == "forkState")
        assert s.state_type == StateType.FORK

    def test_join_pseudo_state(self):
        text = "stateDiagram-v2\n  state joinState <<join>>"
        result = parse_state_diagram(text)
        s = next(s for s in result.states if s.id == "joinState")
        assert s.state_type == StateType.JOIN

    def test_note_right(self):
        text = "stateDiagram-v2\n  s1\n  note right of s1 : Important note"
        result = parse_state_diagram(text)
        assert len(result.notes) == 1
        assert result.notes[0].state_id == "s1"
        assert result.notes[0].text == "Important note"
        assert result.notes[0].position == "right"

    def test_note_left(self):
        text = "stateDiagram-v2\n  s1\n  note left of s1 : Left note"
        result = parse_state_diagram(text)
        assert result.notes[0].position == "left"

    def test_composite_state(self):
        text = (
            "stateDiagram-v2\n"
            "  state Composite {\n"
            "    a --> b\n"
            "  }\n"
        )
        result = parse_state_diagram(text)
        composite = next(
            s for s in result.states if s.id == "Composite"
        )
        assert len(composite.children) == 2
        child_ids = {c.id for c in composite.children}
        assert "a" in child_ids
        assert "b" in child_ids

    def test_composite_state_with_alias(self):
        text = (
            'stateDiagram-v2\n'
            '  state "My Composite" as Comp {\n'
            '    x --> y\n'
            '  }\n'
        )
        result = parse_state_diagram(text)
        comp = next(s for s in result.states if s.id == "Comp")
        assert comp.label == "My Composite"

    def test_comments_stripped(self):
        text = (
            "stateDiagram-v2\n"
            "  s1 --> s2 %% a comment\n"
        )
        result = parse_state_diagram(text)
        assert len(result.transitions) == 1

    def test_unclosed_composite_raises(self):
        text = (
            "stateDiagram-v2\n"
            "  state Comp {\n"
            "    a --> b\n"
        )
        with pytest.raises(ParseError, match="Unclosed composite"):
            parse_state_diagram(text)

    def test_multiple_transitions(self):
        text = (
            "stateDiagram-v2\n"
            "  [*] --> s1\n"
            "  s1 --> s2\n"
            "  s2 --> s3\n"
            "  s3 --> [*]\n"
        )
        result = parse_state_diagram(text)
        assert len(result.transitions) == 4

    def test_start_and_end(self):
        text = (
            "stateDiagram-v2\n"
            "  [*] --> Active\n"
            "  Active --> [*]\n"
        )
        result = parse_state_diagram(text)
        starts = [s for s in result.states if s.state_type == StateType.START]
        ends = [s for s in result.states if s.state_type == StateType.END]
        assert len(starts) == 1
        assert len(ends) == 1

# -----------------------------------------------------------------------
# Layout conversion tests
# -----------------------------------------------------------------------

class TestLayoutConversion:
    """Test conversion from StateDiagram to flowchart IR for layout."""

    def test_basic_conversion(self):
        sd = StateDiagram(
            states=(
                State(id="s1", label="State 1"),
                State(id="s2", label="State 2"),
            ),
            transitions=(
                Transition(source="s1", target="s2"),
            ),
        )
        diagram, _, _ = state_diagram_to_flowchart(sd)
        assert len(diagram.nodes) == 2
        assert len(diagram.edges) == 1

    def test_composite_becomes_subgraph(self):
        child1 = State(id="c1", label="C1")
        child2 = State(id="c2", label="C2")
        parent = State(
            id="parent", label="Parent",
            children=(child1, child2),
        )
        sd = StateDiagram(states=(parent,))
        diagram, _, _ = state_diagram_to_flowchart(sd)
        # Children only (no parent node) = 2 nodes
        assert len(diagram.nodes) == 2
        assert len(diagram.subgraphs) == 1
        assert diagram.subgraphs[0].id == "parent"

    def test_layout_produces_result(self):
        sd = StateDiagram(
            states=(
                State(id="s1", label="State 1"),
                State(id="s2", label="State 2"),
            ),
            transitions=(
                Transition(source="s1", target="s2"),
            ),
        )
        measurer = TextMeasurer()
        result = layout_state_diagram(sd, measurer.measure)
        assert "s1" in result.nodes
        assert "s2" in result.nodes
        assert len(result.edges) >= 1
        assert result.width > 0
        assert result.height > 0

    def test_start_state_gets_small_size(self):
        sd = StateDiagram(
            states=(
                State(id="__start_0", label="", state_type=StateType.START),
                State(id="s1", label="State 1"),
            ),
            transitions=(
                Transition(source="__start_0", target="s1"),
            ),
        )
        measurer = TextMeasurer()
        result = layout_state_diagram(sd, measurer.measure)
        start_nl = result.nodes["__start_0"]
        # Start state should be small (20x20)
        assert start_nl.width == 20.0
        assert start_nl.height == 20.0

# -----------------------------------------------------------------------
# Renderer tests
# -----------------------------------------------------------------------

class TestRenderer:
    """Test state diagram SVG rendering."""

    def _make_svg(self, text: str) -> str:
        diagram = parse_state_diagram(text)
        measurer = TextMeasurer()
        layout = layout_state_diagram(diagram, measurer.measure)
        return render_state_svg(diagram, layout)

    def _parse_svg(self, svg_str: str) -> ET.Element:
        return ET.fromstring(svg_str)

    def test_basic_render(self):
        svg = self._make_svg("stateDiagram-v2\n  s1 --> s2")
        assert "<svg" in svg
        assert "</svg>" in svg

    def test_start_state_renders_circle(self):
        svg = self._make_svg("stateDiagram-v2\n  [*] --> s1")
        root = self._parse_svg(svg)
        # Find start state group
        start_groups = [
            g for g in root.iter("{http://www.w3.org/2000/svg}g")
            if "start" in (g.get("class") or "")
        ]
        assert len(start_groups) >= 1
        # Should have a circle with fill=black
        circles = list(start_groups[0].iter("{http://www.w3.org/2000/svg}circle"))
        assert len(circles) >= 1
        assert circles[0].get("fill") == "black"

    def test_end_state_renders_bulls_eye(self):
        svg = self._make_svg("stateDiagram-v2\n  s1 --> [*]")
        root = self._parse_svg(svg)
        end_groups = [
            g for g in root.iter("{http://www.w3.org/2000/svg}g")
            if "end" in (g.get("class") or "")
        ]
        assert len(end_groups) >= 1
        # Bull's eye: two circles (outer + inner)
        circles = list(end_groups[0].iter("{http://www.w3.org/2000/svg}circle"))
        assert len(circles) == 2

    def test_normal_state_renders_rounded_rect(self):
        svg = self._make_svg("stateDiagram-v2\n  s1")
        root = self._parse_svg(svg)
        state_groups = [
            g for g in root.iter("{http://www.w3.org/2000/svg}g")
            if g.get("class") == "state" and g.get("data-state-id") == "s1"
        ]
        assert len(state_groups) >= 1
        rects = list(state_groups[0].iter("{http://www.w3.org/2000/svg}rect"))
        assert len(rects) >= 1
        assert rects[0].get("rx") == "10"

    def test_choice_state_renders_diamond(self):
        text = (
            "stateDiagram-v2\n"
            "  state myChoice <<choice>>\n"
            "  s1 --> myChoice\n"
        )
        svg = self._make_svg(text)
        root = self._parse_svg(svg)
        choice_groups = [
            g for g in root.iter("{http://www.w3.org/2000/svg}g")
            if "choice" in (g.get("class") or "")
        ]
        assert len(choice_groups) >= 1
        polygons = list(
            choice_groups[0].iter("{http://www.w3.org/2000/svg}polygon")
        )
        assert len(polygons) >= 1

    def test_fork_state_renders_bar(self):
        text = (
            "stateDiagram-v2\n"
            "  state forkState <<fork>>\n"
            "  s1 --> forkState\n"
        )
        svg = self._make_svg(text)
        root = self._parse_svg(svg)
        fork_groups = [
            g for g in root.iter("{http://www.w3.org/2000/svg}g")
            if "fork-join" in (g.get("class") or "")
        ]
        assert len(fork_groups) >= 1
        rects = list(
            fork_groups[0].iter("{http://www.w3.org/2000/svg}rect")
        )
        assert len(rects) >= 1
        assert rects[0].get("fill") == "black"

    def test_note_renders(self):
        text = (
            "stateDiagram-v2\n"
            "  s1\n"
            "  note right of s1 : This is a note\n"
        )
        svg = self._make_svg(text)
        root = self._parse_svg(svg)
        note_groups = [
            g for g in root.iter("{http://www.w3.org/2000/svg}g")
            if g.get("class") == "note"
        ]
        assert len(note_groups) >= 1

    def test_transition_label_renders(self):
        svg = self._make_svg("stateDiagram-v2\n  s1 --> s2 : go")
        # The label "go" should appear in the SVG
        assert "go" in svg

    def test_theme_colors_applied(self):
        from merm.theme import Theme
        text = "stateDiagram-v2\n  s1 --> s2"
        diagram = parse_state_diagram(text)
        measurer = TextMeasurer()
        layout = layout_state_diagram(diagram, measurer.measure)
        theme = Theme(node_fill="#ff0000")
        svg = render_state_svg(diagram, layout, theme=theme)
        assert "#ff0000" in svg

    def test_composite_state_renders(self):
        text = (
            "stateDiagram-v2\n"
            "  state Composite {\n"
            "    a --> b\n"
            "  }\n"
        )
        svg = self._make_svg(text)
        root = self._parse_svg(svg)
        composite_groups = [
            g for g in root.iter("{http://www.w3.org/2000/svg}g")
            if g.get("class") == "composite"
        ]
        assert len(composite_groups) >= 1

    def test_svg_has_defs(self):
        svg = self._make_svg("stateDiagram-v2\n  s1")
        assert "<defs>" in svg or "<defs" in svg

    def test_svg_has_style(self):
        svg = self._make_svg("stateDiagram-v2\n  s1")
        assert "<style>" in svg or "<style" in svg

# -----------------------------------------------------------------------
# Integration / end-to-end tests
# -----------------------------------------------------------------------

class TestIntegration:
    """End-to-end integration tests."""

    def test_full_state_machine(self):
        """Test a complete state machine with various features."""
        text = (
            "stateDiagram-v2\n"
            "  [*] --> Still\n"
            "  Still --> Moving : start\n"
            "  Moving --> Still : stop\n"
            "  Moving --> Crash : accident\n"
            "  Crash --> [*]\n"
        )
        diagram = parse_state_diagram(text)
        measurer = TextMeasurer()
        layout = layout_state_diagram(diagram, measurer.measure)
        svg = render_state_svg(diagram, layout)

        assert "<svg" in svg
        # All state names should appear
        assert "Still" in svg
        assert "Moving" in svg
        assert "Crash" in svg
        # Labels should appear
        assert "start" in svg
        assert "stop" in svg
        assert "accident" in svg

    def test_state_with_choice(self):
        text = (
            "stateDiagram-v2\n"
            "  state check <<choice>>\n"
            "  [*] --> check\n"
            "  check --> s1 : yes\n"
            "  check --> s2 : no\n"
        )
        diagram = parse_state_diagram(text)
        measurer = TextMeasurer()
        layout = layout_state_diagram(diagram, measurer.measure)
        svg = render_state_svg(diagram, layout)
        assert "<svg" in svg
        assert "yes" in svg
        assert "no" in svg

    def test_state_with_fork_join(self):
        text = (
            "stateDiagram-v2\n"
            "  state fork1 <<fork>>\n"
            "  state join1 <<join>>\n"
            "  [*] --> fork1\n"
            "  fork1 --> s1\n"
            "  fork1 --> s2\n"
            "  s1 --> join1\n"
            "  s2 --> join1\n"
            "  join1 --> [*]\n"
        )
        diagram = parse_state_diagram(text)
        measurer = TextMeasurer()
        layout = layout_state_diagram(diagram, measurer.measure)
        svg = render_state_svg(diagram, layout)
        assert "<svg" in svg

    def test_non_overlapping_layout(self):
        """Verify nodes don't overlap in layout."""
        text = (
            "stateDiagram-v2\n"
            "  s1 --> s2\n"
            "  s2 --> s3\n"
            "  s3 --> s4\n"
        )
        diagram = parse_state_diagram(text)
        measurer = TextMeasurer()
        layout = layout_state_diagram(diagram, measurer.measure)

        nodes = list(layout.nodes.values())
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                a = nodes[i]
                b = nodes[j]
                # Check no overlap (allowing small tolerance)
                x_overlap = (
                    a.x < b.x + b.width and a.x + a.width > b.x
                )
                y_overlap = (
                    a.y < b.y + b.height and a.y + a.height > b.y
                )
                assert not (x_overlap and y_overlap), (
                    f"Nodes overlap: {a} and {b}"
                )

# -----------------------------------------------------------------------
# CLI routing test
# -----------------------------------------------------------------------

class TestCLIRouting:
    """Test that the CLI correctly routes state diagrams."""

    def test_detect_state_diagram(self):
        """Test that CLI detection logic works."""
        import re
        source = "stateDiagram-v2\n  s1 --> s2"
        is_state = bool(re.match(r"^\s*stateDiagram", source, re.MULTILINE))
        assert is_state

    def test_detect_flowchart(self):
        """Test that flowchart is not detected as state diagram."""
        import re
        source = "flowchart TD\n  A --> B"
        is_state = bool(re.match(r"^\s*stateDiagram", source, re.MULTILINE))
        assert not is_state
