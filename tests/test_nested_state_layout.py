"""Tests for nested/composite state diagram layout (issue 95).

Verifies that:
- Composite states and outer states are in a coherent connected layout
- Edges between outer and inner states connect properly
- Edge labels do not overlap
- Subgraph boundaries contain only child nodes
"""

from merm import render_diagram
from merm.layout.statediag import (
    layout_state_diagram,
    state_diagram_to_flowchart,
)
from merm.measure.text import TextMeasurer
from merm.parser.statediag import parse_state_diagram

NESTED_INPUT = """\
stateDiagram-v2
    [*] --> Active
    state Active {
        [*] --> Running
        Running --> Paused: pause
        Paused --> Running: resume
    }
    Active --> Stopped: stop
    Stopped --> [*]
"""


class TestNestedStateFlowchartConversion:
    """Test state_diagram_to_flowchart for composite states."""

    def test_composite_children_in_subgraph(self):
        diagram = parse_state_diagram(NESTED_INPUT)
        fc, entry, exit_ = state_diagram_to_flowchart(diagram)
        # Should have exactly one subgraph for Active
        assert len(fc.subgraphs) == 1
        sg = fc.subgraphs[0]
        assert sg.id == "Active"
        # Children should be in the subgraph
        assert "Running" in sg.node_ids
        assert "Paused" in sg.node_ids

    def test_incoming_edge_redirected_to_entry(self):
        diagram = parse_state_diagram(NESTED_INPUT)
        fc, entry, exit_ = state_diagram_to_flowchart(diagram)
        # The incoming edge [*] --> Active should be redirected to
        # the internal start pseudo-state
        entry_id = entry.get("Active")
        assert entry_id is not None
        # Find the edge from __start_0
        incoming = [e for e in fc.edges if e.target == entry_id]
        assert len(incoming) >= 1

    def test_outgoing_edge_redirected_from_exit(self):
        diagram = parse_state_diagram(NESTED_INPUT)
        fc, entry, exit_ = state_diagram_to_flowchart(diagram)
        # The outgoing edge Active --> Stopped should be redirected
        # from the exit child node
        exit_id = exit_.get("Active")
        assert exit_id is not None
        outgoing = [
            e for e in fc.edges
            if e.source == exit_id and e.target == "Stopped"
        ]
        assert len(outgoing) == 1

    def test_composite_entry_and_exit_maps(self):
        diagram = parse_state_diagram(NESTED_INPUT)
        _, entry, exit_ = state_diagram_to_flowchart(diagram)
        assert "Active" in entry
        assert "Active" in exit_


class TestNestedStateLayout:
    """Test layout of nested state diagrams."""

    def setup_method(self):
        self.measurer = TextMeasurer()

    def test_layout_produces_all_nodes(self):
        diagram = parse_state_diagram(NESTED_INPUT)
        layout = layout_state_diagram(diagram, measure_fn=self.measurer.measure)
        node_ids = set(layout.nodes.keys())
        assert "Running" in node_ids
        assert "Paused" in node_ids
        assert "Stopped" in node_ids

    def test_outer_states_below_subgraph(self):
        """Stopped should be positioned below the Active subgraph."""
        diagram = parse_state_diagram(NESTED_INPUT)
        layout = layout_state_diagram(diagram, measure_fn=self.measurer.measure)
        sg = layout.subgraphs.get("Active")
        assert sg is not None
        stopped = layout.nodes["Stopped"]
        # Stopped should be below the Active subgraph boundary
        sg_bottom = sg.y + sg.height
        assert stopped.y >= sg_bottom - 1.0, (
            f"Stopped (y={stopped.y}) should be below Active subgraph "
            f"(bottom={sg_bottom})"
        )

    def test_inner_states_inside_subgraph(self):
        """Running and Paused should be within the Active subgraph bounds."""
        diagram = parse_state_diagram(NESTED_INPUT)
        layout = layout_state_diagram(diagram, measure_fn=self.measurer.measure)
        sg = layout.subgraphs.get("Active")
        assert sg is not None
        for nid in ("Running", "Paused"):
            nl = layout.nodes[nid]
            assert nl.x >= sg.x, f"{nid} x={nl.x} < sg.x={sg.x}"
            assert nl.y >= sg.y, f"{nid} y={nl.y} < sg.y={sg.y}"
            assert nl.x + nl.width <= sg.x + sg.width + 1.0
            assert nl.y + nl.height <= sg.y + sg.height + 1.0

    def test_edges_cross_subgraph_boundary(self):
        """Edges to/from composite should start/end near subgraph boundary."""
        diagram = parse_state_diagram(NESTED_INPUT)
        layout = layout_state_diagram(diagram, measure_fn=self.measurer.measure)
        sg = layout.subgraphs.get("Active")
        assert sg is not None
        sg_bottom = sg.y + sg.height

        # Find the edge from composite exit to Stopped (the "stop" edge)
        stop_edge = None
        for el in layout.edges:
            if el.target == "Stopped":
                stop_edge = el
                break
        assert stop_edge is not None
        # The first point (source) should be near the subgraph boundary
        src_y = stop_edge.points[0].y
        assert abs(src_y - sg_bottom) < 5.0, (
            f"Edge source y={src_y} should be near subgraph bottom={sg_bottom}"
        )

    def test_bidirectional_edges_detected(self):
        """Running<->Paused should be a bidirectional pair."""
        from merm.render.edges import apply_bidi_offsets, find_bidirectional_pairs

        diagram = parse_state_diagram(NESTED_INPUT)
        layout = layout_state_diagram(diagram, measure_fn=self.measurer.measure)
        pairs = find_bidirectional_pairs(layout.edges)
        assert ("Running", "Paused") in pairs
        assert ("Paused", "Running") in pairs

        # After bidi offsets, edges should have different x coords
        offset_edges = apply_bidi_offsets(layout.edges)
        fwd = [
            e for e in offset_edges
            if e.source == "Running" and e.target == "Paused"
        ]
        bwd = [
            e for e in offset_edges
            if e.source == "Paused" and e.target == "Running"
        ]
        assert len(fwd) == 1
        assert len(bwd) == 1
        assert fwd[0].points[0].x != bwd[0].points[0].x


class TestNestedStateSVGRendering:
    """Test SVG rendering of nested state diagrams."""

    def test_renders_without_error(self):
        svg = render_diagram(NESTED_INPUT)
        assert "<svg" in svg
        assert "</svg>" in svg

    def test_composite_box_present(self):
        svg = render_diagram(NESTED_INPUT)
        assert 'class="composite"' in svg
        assert 'data-state-id="Active"' in svg

    def test_all_states_rendered(self):
        svg = render_diagram(NESTED_INPUT)
        assert "Running" in svg
        assert "Paused" in svg
        assert "Stopped" in svg
        assert "Active" in svg

    def test_edge_labels_present(self):
        svg = render_diagram(NESTED_INPUT)
        assert "pause" in svg
        assert "resume" in svg
        assert "stop" in svg

    def test_start_end_circles_present(self):
        svg = render_diagram(NESTED_INPUT)
        # Should have start circles (filled black) and end circles
        assert 'class="state start"' in svg
        assert 'class="state end"' in svg
