"""Tests for state diagram fork/join bars (issue 94).

Verifies that composite states with multiple parallel entries/exits
produce fork/join bars instead of multiple start/end pseudo-states.
"""

import xml.etree.ElementTree as ET

from merm.ir.statediag import (
    StateType,
)
from merm.layout.statediag import (
    layout_state_diagram,
    state_diagram_to_flowchart,
)
from merm.measure import TextMeasurer
from merm.parser.statediag import parse_state_diagram
from merm.render.statediag import render_state_svg

FORK_JOIN_INPUT = """\
stateDiagram-v2
    [*] --> Ready
    Ready --> Processing
    state Processing {
        [*] --> TaskA
        [*] --> TaskB
        TaskA --> [*]
        TaskB --> [*]
    }
    Processing --> Done
    Done --> [*]
"""


class TestParserForkJoin:
    """Parser correctly merges parallel pseudo-states into fork/join."""

    def test_composite_has_fork_child(self):
        diagram = parse_state_diagram(FORK_JOIN_INPUT)
        processing = next(s for s in diagram.states if s.id == "Processing")
        fork_children = [
            c for c in processing.children if c.state_type == StateType.FORK
        ]
        assert len(fork_children) == 1, "Expected exactly one fork child"

    def test_composite_has_join_child(self):
        diagram = parse_state_diagram(FORK_JOIN_INPUT)
        processing = next(s for s in diagram.states if s.id == "Processing")
        join_children = [
            c for c in processing.children if c.state_type == StateType.JOIN
        ]
        assert len(join_children) == 1, "Expected exactly one join child"

    def test_no_start_pseudo_states_in_composite(self):
        diagram = parse_state_diagram(FORK_JOIN_INPUT)
        processing = next(s for s in diagram.states if s.id == "Processing")
        start_children = [
            c for c in processing.children if c.state_type == StateType.START
        ]
        assert len(start_children) == 0, (
            "Start pseudo-states should be merged into fork"
        )

    def test_no_end_pseudo_states_in_composite(self):
        diagram = parse_state_diagram(FORK_JOIN_INPUT)
        processing = next(s for s in diagram.states if s.id == "Processing")
        end_children = [
            c for c in processing.children if c.state_type == StateType.END
        ]
        assert len(end_children) == 0, "End pseudo-states should be merged into join"

    def test_fork_transitions_correct(self):
        diagram = parse_state_diagram(FORK_JOIN_INPUT)
        processing = next(s for s in diagram.states if s.id == "Processing")
        fork = next(
            c for c in processing.children if c.state_type == StateType.FORK
        )
        fork_transitions = [
            t for t in diagram.transitions if t.source == fork.id
        ]
        targets = {t.target for t in fork_transitions}
        assert targets == {"TaskA", "TaskB"}

    def test_join_transitions_correct(self):
        diagram = parse_state_diagram(FORK_JOIN_INPUT)
        processing = next(s for s in diagram.states if s.id == "Processing")
        join = next(
            c for c in processing.children if c.state_type == StateType.JOIN
        )
        join_transitions = [
            t for t in diagram.transitions if t.target == join.id
        ]
        sources = {t.source for t in join_transitions}
        assert sources == {"TaskA", "TaskB"}

    def test_outer_flow_preserved(self):
        diagram = parse_state_diagram(FORK_JOIN_INPUT)
        outer_transitions = [
            (t.source, t.target)
            for t in diagram.transitions
            if "fork" not in t.source
            and "join" not in t.target
            and "fork" not in t.target
            and "join" not in t.source
            and "Task" not in t.source
            and "Task" not in t.target
        ]
        # Should have: start->Ready, Ready->Processing, Processing->Done, Done->end
        assert len(outer_transitions) == 4

    def test_single_start_not_converted(self):
        """A composite with a single [*] should keep it as START, not fork."""
        text = """\
stateDiagram-v2
    state Wrapper {
        [*] --> OnlyChild
        OnlyChild --> [*]
    }
"""
        diagram = parse_state_diagram(text)
        wrapper = next(s for s in diagram.states if s.id == "Wrapper")
        start_children = [
            c for c in wrapper.children if c.state_type == StateType.START
        ]
        fork_children = [
            c for c in wrapper.children if c.state_type == StateType.FORK
        ]
        assert len(start_children) == 1
        assert len(fork_children) == 0

    def test_three_parallel_branches(self):
        """Three parallel branches should also produce fork/join."""
        text = """\
stateDiagram-v2
    state Parallel {
        [*] --> A
        [*] --> B
        [*] --> C
        A --> [*]
        B --> [*]
        C --> [*]
    }
"""
        diagram = parse_state_diagram(text)
        parallel = next(s for s in diagram.states if s.id == "Parallel")
        fork_children = [
            c for c in parallel.children if c.state_type == StateType.FORK
        ]
        join_children = [
            c for c in parallel.children if c.state_type == StateType.JOIN
        ]
        assert len(fork_children) == 1
        assert len(join_children) == 1
        fork = fork_children[0]
        fork_targets = {
            t.target for t in diagram.transitions if t.source == fork.id
        }
        assert fork_targets == {"A", "B", "C"}


class TestLayoutForkJoin:
    """Layout correctly handles fork/join nodes."""

    def test_fork_join_in_flowchart_ir(self):
        diagram = parse_state_diagram(FORK_JOIN_INPUT)
        fc, _, _ = state_diagram_to_flowchart(diagram)
        # Fork and join nodes should exist
        node_ids = {n.id for n in fc.nodes}
        assert any("fork" in nid for nid in node_ids)
        assert any("join" in nid for nid in node_ids)

    def test_layout_produces_fork_join_nodes(self):
        diagram = parse_state_diagram(FORK_JOIN_INPUT)
        measurer = TextMeasurer()
        result = layout_state_diagram(diagram, measure_fn=measurer.measure)
        # Fork and join nodes should be in the layout
        node_ids = set(result.nodes.keys())
        fork_ids = {nid for nid in node_ids if "fork" in nid}
        join_ids = {nid for nid in node_ids if "join" in nid}
        assert len(fork_ids) >= 1
        assert len(join_ids) >= 1

    def test_fork_join_dimensions(self):
        """Fork/join bars should be wide and thin."""
        diagram = parse_state_diagram(FORK_JOIN_INPUT)
        measurer = TextMeasurer()
        result = layout_state_diagram(diagram, measure_fn=measurer.measure)
        for nid, nl in result.nodes.items():
            if "fork" in nid or "join" in nid:
                assert nl.width > nl.height, (
                    f"Fork/join bar {nid} should be wider than tall: "
                    f"{nl.width}x{nl.height}"
                )


class TestRenderForkJoin:
    """SVG rendering includes fork/join bars."""

    def test_svg_contains_fork_join_class(self):
        diagram = parse_state_diagram(FORK_JOIN_INPUT)
        measurer = TextMeasurer()
        result = layout_state_diagram(diagram, measure_fn=measurer.measure)
        svg = render_state_svg(diagram, result)
        assert "fork-join" in svg, "SVG should contain fork-join class elements"

    def test_svg_has_fork_join_rect(self):
        diagram = parse_state_diagram(FORK_JOIN_INPUT)
        measurer = TextMeasurer()
        result = layout_state_diagram(diagram, measure_fn=measurer.measure)
        svg = render_state_svg(diagram, result)
        root = ET.fromstring(svg)
        ns = {"svg": "http://www.w3.org/2000/svg"}
        fork_join_groups = root.findall(
            ".//svg:g[@class='state fork-join']", ns
        )
        assert len(fork_join_groups) == 2, (
            f"Expected 2 fork-join groups (fork + join), got {len(fork_join_groups)}"
        )

    def test_svg_fork_join_rects_are_black(self):
        diagram = parse_state_diagram(FORK_JOIN_INPUT)
        measurer = TextMeasurer()
        result = layout_state_diagram(diagram, measure_fn=measurer.measure)
        svg = render_state_svg(diagram, result)
        root = ET.fromstring(svg)
        ns = {"svg": "http://www.w3.org/2000/svg"}
        for g in root.findall(".//svg:g[@class='state fork-join']", ns):
            rect = g.find("svg:rect", ns)
            assert rect is not None
            assert rect.get("fill") == "black"

    def test_full_render_via_render_diagram(self):
        """End-to-end: render_diagram produces valid SVG with fork/join."""
        from merm import render_diagram

        svg = render_diagram(FORK_JOIN_INPUT)
        assert "fork-join" in svg
        # Should parse as valid XML
        ET.fromstring(svg)

    def test_fixture_file_renders(self):
        """The corpus fixture file renders without errors."""
        from merm import render_diagram

        with open("tests/fixtures/corpus/state/fork_join.mmd") as f:
            text = f.read()
        svg = render_diagram(text)
        assert "fork-join" in svg
        ET.fromstring(svg)
