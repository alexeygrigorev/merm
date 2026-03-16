"""Tests for state diagram bug fixes:

1. Multiple [*] end targets should merge into a single END node
2. Start circle should render as solid black fill (not overridden by CSS)
"""

import xml.etree.ElementTree as ET

from merm.ir.statediag import StateType
from merm.parser.statediag import parse_state_diagram

_NS = "{http://www.w3.org/2000/svg}"


class TestMergedEndNodes:
    """Bug fix: multiple transitions to [*] produce one END node."""

    DIAGRAM = """\
stateDiagram-v2
    [*] --> Still
    Still --> [*]
    Still --> Moving
    Moving --> Still
    Moving --> Crash
    Crash --> [*]
"""

    def test_single_start_node(self):
        """There should be exactly one START state."""
        ir = parse_state_diagram(self.DIAGRAM)
        starts = [
            s for s in ir.states
            if s.state_type == StateType.START
        ]
        assert len(starts) == 1, (
            f"Expected 1 START, got {len(starts)}: {starts}"
        )

    def test_single_end_node(self):
        """One END state even with multiple [*] targets."""
        ir = parse_state_diagram(self.DIAGRAM)
        ends = [
            s for s in ir.states
            if s.state_type == StateType.END
        ]
        assert len(ends) == 1, (
            f"Expected 1 END, got {len(ends)}: {ends}"
        )

    def test_both_transitions_point_to_same_end(self):
        """Still-->[*] and Crash-->[*] target same END."""
        ir = parse_state_diagram(self.DIAGRAM)
        ends = [
            s for s in ir.states
            if s.state_type == StateType.END
        ]
        assert len(ends) == 1
        end_id = ends[0].id
        to_end = [
            t for t in ir.transitions if t.target == end_id
        ]
        assert len(to_end) == 2, (
            f"Expected 2 transitions to END, got {len(to_end)}"
        )
        sources = {t.source for t in to_end}
        assert "Still" in sources
        assert "Crash" in sources

    def test_single_start_with_multiple_starts(self):
        """Multiple [*]-->X merge into one START."""
        text = """\
stateDiagram-v2
    [*] --> A
    [*] --> B
    A --> [*]
"""
        ir = parse_state_diagram(text)
        starts = [
            s for s in ir.states
            if s.state_type == StateType.START
        ]
        assert len(starts) == 1, (
            f"Expected 1 START, got {len(starts)}: {starts}"
        )


class TestStartCircleRendering:
    """Start circle must render as solid black."""

    def _render_svg(self, mermaid_text: str) -> str:
        from merm import render_diagram
        return render_diagram(mermaid_text)

    def test_start_circle_has_black_fill(self):
        """Start circle uses inline style fill:black."""
        svg = self._render_svg(
            "stateDiagram-v2\n"
            "    [*] --> Active\n"
            "    Active --> [*]\n"
        )
        root = ET.fromstring(svg)

        xpath = f".//{_NS}g[@class='state start']"
        start_groups = root.findall(xpath)
        assert len(start_groups) == 1, (
            f"Expected 1 start group, found {len(start_groups)}"
        )

        circle = start_groups[0].find(f"{_NS}circle")
        assert circle is not None
        # Inline style beats CSS specificity
        style = circle.get("style", "")
        assert "fill: black" in style or "fill:black" in style, (
            f"Start circle needs inline fill:black, "
            f"got style={style!r}"
        )

    def test_end_circle_has_double_ring(self):
        """End state has two circles (outer hollow, inner filled)."""
        svg = self._render_svg(
            "stateDiagram-v2\n"
            "    [*] --> Active\n"
            "    Active --> [*]\n"
        )
        root = ET.fromstring(svg)

        xpath = f".//{_NS}g[@class='state end']"
        end_groups = root.findall(xpath)
        assert len(end_groups) == 1, (
            f"Expected 1 end group, found {len(end_groups)}"
        )

        circles = end_groups[0].findall(f"{_NS}circle")
        assert len(circles) == 2, (
            "End state should have 2 circles (outer + inner)"
        )

        # Outer circle: hollow with inline style
        outer_style = circles[0].get("style", "")
        assert "fill: none" in outer_style
        assert "stroke: black" in outer_style

        # Inner circle: filled black with inline style
        inner_style = circles[1].get("style", "")
        assert "fill: black" in inner_style
