"""Tests for the SVG renderer."""

import xml.etree.ElementTree as ET

from merm.ir import (
    Diagram,
    DiagramType,
    Direction,
    Edge,
    Node,
    Subgraph,
)
from merm.layout import EdgeLayout, LayoutResult, NodeLayout, Point, layout_diagram
from merm.measure import measure_text
from merm.render import render_svg

_SVG_NS = "http://www.w3.org/2000/svg"
_NS = {"svg": _SVG_NS}

def _simple_diagram(
    nodes: list[tuple[str, str]] | None = None,
    edges: list[tuple[str, str, str | None]] | None = None,
    subgraphs: tuple[Subgraph, ...] = (),
) -> Diagram:
    """Build a simple Diagram from node/edge tuples."""
    if nodes is None:
        nodes = [("A", "A"), ("B", "B")]
    if edges is None:
        edges = [("A", "B", None)]
    return Diagram(
        type=DiagramType.flowchart,
        direction=Direction.TB,
        nodes=tuple(Node(id=nid, label=label) for nid, label in nodes),
        edges=tuple(
            Edge(source=s, target=t, label=lbl) for s, t, lbl in edges
        ),
        subgraphs=subgraphs,
    )

def _simple_layout(
    nodes: dict[str, tuple[float, float, float, float]] | None = None,
    edges: list[tuple[str, str, list[tuple[float, float]]]] | None = None,
    width: float = 200.0,
    height: float = 100.0,
) -> LayoutResult:
    """Helper: build a LayoutResult from dicts.

    nodes: {id: (x, y, w, h)}
    edges: [(source, target, [(x,y), ...])]
    """
    if nodes is None:
        nodes = {
            "A": (20.0, 10.0, 80.0, 40.0),
            "B": (20.0, 80.0, 80.0, 40.0),
        }
    if edges is None:
        edges = [("A", "B", [(60.0, 50.0), (60.0, 80.0)])]

    nl = {
        nid: NodeLayout(x=x, y=y, width=w, height=h)
        for nid, (x, y, w, h) in nodes.items()
    }
    el = [
        EdgeLayout(
            source=src,
            target=tgt,
            points=[Point(x=px, y=py) for px, py in pts],
        )
        for src, tgt, pts in edges
    ]
    return LayoutResult(nodes=nl, edges=el, width=width, height=height)

def _parse(svg_str: str) -> ET.Element:
    """Parse SVG string, returning the root Element."""
    return ET.fromstring(svg_str)

# ---------------------------------------------------------------------------
# 1. render_svg returns valid SVG
# ---------------------------------------------------------------------------

class TestRenderSVGBasic:
    def test_parseable_xml(self):
        d = _simple_diagram()
        lr = _simple_layout()
        result = render_svg(d, lr)
        root = _parse(result)  # should not raise
        assert root is not None

    def test_root_is_svg(self):
        d = _simple_diagram()
        lr = _simple_layout()
        root = _parse(render_svg(d, lr))
        # Tag may be namespaced
        assert root.tag in ("svg", f"{{{_SVG_NS}}}svg")

    def test_xmlns_attribute(self):
        d = _simple_diagram()
        lr = _simple_layout()
        result = render_svg(d, lr)
        assert 'xmlns="http://www.w3.org/2000/svg"' in result

# ---------------------------------------------------------------------------
# 2. SVG contains nodes
# ---------------------------------------------------------------------------

class TestNodeRendering:
    def test_correct_node_count(self):
        d = _simple_diagram(
            nodes=[("A", "A"), ("B", "B"), ("C", "C")],
            edges=[],
        )
        lr = _simple_layout(
            nodes={
                "A": (0, 0, 80, 40),
                "B": (100, 0, 80, 40),
                "C": (200, 0, 80, 40),
            },
            edges=[],
        )
        root = _parse(render_svg(d, lr))
        node_groups = root.findall(".//*[@data-node-id]")
        assert len(node_groups) == 3

    def test_node_contains_rect_and_text(self):
        d = _simple_diagram()
        lr = _simple_layout()
        root = _parse(render_svg(d, lr))
        for g in root.findall(".//*[@data-node-id]"):
            rects = g.findall(f"{{{_SVG_NS}}}rect") or g.findall("rect")
            texts = g.findall(f"{{{_SVG_NS}}}text") or g.findall("text")
            assert len(rects) >= 1, "Node group missing <rect>"
            assert len(texts) >= 1, "Node group missing <text>"

# ---------------------------------------------------------------------------
# 3. Node text labels
# ---------------------------------------------------------------------------

class TestNodeTextLabels:
    def test_single_line_label(self):
        d = _simple_diagram(nodes=[("X", "Hello World")], edges=[])
        lr = _simple_layout(nodes={"X": (10, 10, 100, 40)}, edges=[])
        root = _parse(render_svg(d, lr))
        g = root.findall(".//*[@data-node-id='X']")
        assert len(g) == 1
        # Check text content (may be direct text or in tspan)
        text_els = g[0].iter()
        all_text = "".join(el.text or "" for el in text_els)
        assert "Hello World" in all_text

    def test_multiline_label_tspans(self):
        d = _simple_diagram(
            nodes=[("M", "Line1<br/>Line2<br/>Line3")], edges=[]
        )
        lr = _simple_layout(nodes={"M": (10, 10, 100, 60)}, edges=[])
        root = _parse(render_svg(d, lr))
        g = root.findall(".//*[@data-node-id='M']")
        assert len(g) == 1
        tspans = list(g[0].iter())
        tspan_els = [
            el for el in tspans
            if el.tag in ("tspan", f"{{{_SVG_NS}}}tspan")
        ]
        assert len(tspan_els) == 3
        texts = [ts.text for ts in tspan_els]
        assert texts == ["Line1", "Line2", "Line3"]

# ---------------------------------------------------------------------------
# 4. SVG contains edges
# ---------------------------------------------------------------------------

class TestEdgeRendering:
    def test_edge_path_exists(self):
        d = _simple_diagram()
        lr = _simple_layout()
        root = _parse(render_svg(d, lr))
        edge_groups = root.findall(".//*[@data-edge-source]")
        assert len(edge_groups) == 1
        g = edge_groups[0]
        assert g.get("data-edge-source") == "A"
        assert g.get("data-edge-target") == "B"

    def test_edge_path_d_attribute(self):
        d = _simple_diagram()
        lr = _simple_layout()
        root = _parse(render_svg(d, lr))
        edge_groups = root.findall(".//*[@data-edge-source]")
        g = edge_groups[0]
        paths = list(g.iter())
        path_els = [
            el for el in paths
            if el.tag in ("path", f"{{{_SVG_NS}}}path")
        ]
        assert len(path_els) >= 1
        d_attr = path_els[0].get("d", "")
        assert d_attr.startswith("M")

    def test_edge_count_matches(self):
        d = _simple_diagram(
            nodes=[("A", "A"), ("B", "B"), ("C", "C")],
            edges=[("A", "B", None), ("B", "C", None)],
        )
        lr = _simple_layout(
            nodes={
                "A": (0, 0, 80, 40),
                "B": (0, 60, 80, 40),
                "C": (0, 120, 80, 40),
            },
            edges=[
                ("A", "B", [(40, 40), (40, 60)]),
                ("B", "C", [(40, 100), (40, 120)]),
            ],
        )
        root = _parse(render_svg(d, lr))
        edge_groups = root.findall(".//*[@data-edge-source]")
        assert len(edge_groups) == 2

# ---------------------------------------------------------------------------
# 5. Edge labels
# ---------------------------------------------------------------------------

class TestEdgeLabels:
    def test_edge_label_rendered(self):
        d = _simple_diagram(edges=[("A", "B", "yes")])
        lr = _simple_layout()
        root = _parse(render_svg(d, lr))
        # Edge path and label are in separate groups (two-pass rendering).
        edge_groups = root.findall(".//*[@data-edge-source='A']")
        assert len(edge_groups) >= 1
        all_text = "".join(
            el.text or "" for g in edge_groups for el in g.iter()
        )
        assert "yes" in all_text

    def test_edge_without_label_no_extra_text(self):
        d = _simple_diagram(edges=[("A", "B", None)])
        lr = _simple_layout()
        root = _parse(render_svg(d, lr))
        edge_groups = root.findall(".//*[@data-edge-source='A']")
        g = edge_groups[0]
        text_els = [
            el for el in g.iter()
            if el.tag in ("text", f"{{{_SVG_NS}}}text")
        ]
        assert len(text_els) == 0

# ---------------------------------------------------------------------------
# 6. Arrowhead marker in defs
# ---------------------------------------------------------------------------

class TestDefs:
    def test_defs_contains_marker(self):
        d = _simple_diagram()
        lr = _simple_layout()
        root = _parse(render_svg(d, lr))
        markers = [
            el for el in root.iter()
            if el.tag in ("marker", f"{{{_SVG_NS}}}marker")
        ]
        assert len(markers) >= 1

    def test_marker_attributes(self):
        d = _simple_diagram()
        lr = _simple_layout()
        root = _parse(render_svg(d, lr))
        markers = [
            el for el in root.iter()
            if el.tag in ("marker", f"{{{_SVG_NS}}}marker")
        ]
        m = markers[0]
        assert m.get("id") is not None
        assert m.get("markerWidth") is not None
        assert m.get("markerHeight") is not None

# ---------------------------------------------------------------------------
# 7. Default theme colors
# ---------------------------------------------------------------------------

class TestDefaultTheme:
    def test_style_contains_node_fill(self):
        d = _simple_diagram()
        lr = _simple_layout()
        result = render_svg(d, lr)
        assert "#ECECFF" in result

    def test_style_contains_text_color(self):
        d = _simple_diagram()
        lr = _simple_layout()
        result = render_svg(d, lr)
        assert "#333" in result

# ---------------------------------------------------------------------------
# 8. ViewBox includes padding
# ---------------------------------------------------------------------------

class TestViewBox:
    def test_viewbox_has_padding(self):
        d = _simple_diagram()
        lr = _simple_layout(width=200.0, height=100.0)
        root = _parse(render_svg(d, lr))
        vb = root.get("viewBox", "")
        parts = vb.split()
        assert len(parts) == 4
        vb_x, vb_y, vb_w, vb_h = (float(p) for p in parts)
        # Padding means viewBox is larger than content
        assert vb_w > 200.0
        assert vb_h > 100.0

    def test_viewbox_negative_origin(self):
        d = _simple_diagram()
        lr = _simple_layout(width=200.0, height=100.0)
        root = _parse(render_svg(d, lr))
        vb = root.get("viewBox", "")
        parts = vb.split()
        vb_x = float(parts[0])
        vb_y = float(parts[1])
        assert vb_x < 0
        assert vb_y < 0

# ---------------------------------------------------------------------------
# 9. Subgraph rendering
# ---------------------------------------------------------------------------

class TestSubgraph:
    def test_subgraph_rendered(self):
        sg = Subgraph(id="sg1", title="My Group", node_ids=("A", "B"))
        d = _simple_diagram(subgraphs=(sg,))
        lr = _simple_layout()
        root = _parse(render_svg(d, lr))
        sg_groups = root.findall(".//*[@data-subgraph-id]")
        assert len(sg_groups) == 1
        assert sg_groups[0].get("data-subgraph-id") == "sg1"

    def test_subgraph_contains_rect_and_text(self):
        sg = Subgraph(id="sg1", title="My Group", node_ids=("A", "B"))
        d = _simple_diagram(subgraphs=(sg,))
        lr = _simple_layout()
        root = _parse(render_svg(d, lr))
        sg_groups = root.findall(".//*[@data-subgraph-id='sg1']")
        g = sg_groups[0]
        rects = [
            el for el in g.iter()
            if el.tag in ("rect", f"{{{_SVG_NS}}}rect")
        ]
        texts = [
            el for el in g.iter()
            if el.tag in ("text", f"{{{_SVG_NS}}}text")
        ]
        assert len(rects) >= 1
        assert len(texts) >= 1

    def test_subgraph_rect_has_rx(self):
        sg = Subgraph(id="sg1", title="Title", node_ids=("A",))
        d = _simple_diagram(subgraphs=(sg,))
        lr = _simple_layout()
        root = _parse(render_svg(d, lr))
        sg_groups = root.findall(".//*[@data-subgraph-id='sg1']")
        rects = [
            el for el in sg_groups[0].iter()
            if el.tag in ("rect", f"{{{_SVG_NS}}}rect")
        ]
        assert rects[0].get("rx") == "5"

    def test_subgraph_title_text(self):
        sg = Subgraph(id="sg1", title="My Group", node_ids=("A",))
        d = _simple_diagram(subgraphs=(sg,))
        lr = _simple_layout()
        root = _parse(render_svg(d, lr))
        sg_groups = root.findall(".//*[@data-subgraph-id='sg1']")
        all_text = "".join(el.text or "" for el in sg_groups[0].iter())
        assert "My Group" in all_text

# ---------------------------------------------------------------------------
# 10. Empty diagram
# ---------------------------------------------------------------------------

class TestEmptyDiagram:
    def test_empty_returns_valid_svg(self):
        d = Diagram()
        lr = LayoutResult(nodes={}, edges=[], width=0.0, height=0.0)
        result = render_svg(d, lr)
        root = _parse(result)
        assert root.tag in ("svg", f"{{{_SVG_NS}}}svg")

    def test_empty_no_node_or_edge_elements(self):
        d = Diagram()
        lr = LayoutResult(nodes={}, edges=[], width=0.0, height=0.0)
        root = _parse(render_svg(d, lr))
        assert root.findall(".//*[@data-node-id]") == []
        assert root.findall(".//*[@data-edge-source]") == []

# ---------------------------------------------------------------------------
# 11. Single node, no edges
# ---------------------------------------------------------------------------

class TestSingleNode:
    def test_single_node_no_edges(self):
        d = _simple_diagram(nodes=[("X", "Only")], edges=[])
        lr = _simple_layout(nodes={"X": (10, 10, 80, 40)}, edges=[])
        root = _parse(render_svg(d, lr))
        assert len(root.findall(".//*[@data-node-id]")) == 1
        assert len(root.findall(".//*[@data-edge-source]")) == 0

# ---------------------------------------------------------------------------
# 12. Integration: Round-trip with layout_diagram
# ---------------------------------------------------------------------------

class TestIntegration:
    def test_round_trip_3_nodes_2_edges(self):
        d = Diagram(
            type=DiagramType.flowchart,
            direction=Direction.TB,
            nodes=(
                Node(id="A", label="Start"),
                Node(id="B", label="Middle"),
                Node(id="C", label="End"),
            ),
            edges=(
                Edge(source="A", target="B"),
                Edge(source="B", target="C"),
            ),
        )
        lr = layout_diagram(d, measure_text)
        result = render_svg(d, lr)
        root = _parse(result)
        assert root.tag in ("svg", f"{{{_SVG_NS}}}svg")
        assert len(root.findall(".//*[@data-node-id]")) == 3
        assert len(root.findall(".//*[@data-edge-source]")) == 2

    def test_integration_with_subgraph(self):
        d = Diagram(
            type=DiagramType.flowchart,
            direction=Direction.TB,
            nodes=(
                Node(id="A", label="A"),
                Node(id="B", label="B"),
                Node(id="C", label="C"),
            ),
            edges=(
                Edge(source="A", target="B"),
                Edge(source="B", target="C"),
            ),
            subgraphs=(
                Subgraph(id="sg", title="Group", node_ids=("A", "B")),
            ),
        )
        lr = layout_diagram(d, measure_text)
        result = render_svg(d, lr)
        root = _parse(result)
        assert len(root.findall(".//*[@data-subgraph-id]")) == 1
        all_text = "".join(
            el.text or ""
            for el in root.findall(".//*[@data-subgraph-id='sg']")[0].iter()
        )
        assert "Group" in all_text

# ---------------------------------------------------------------------------
# 13. SVG starts with <svg
# ---------------------------------------------------------------------------

class TestSVGOutput:
    def test_starts_with_svg_tag(self):
        d = _simple_diagram()
        lr = _simple_layout()
        result = render_svg(d, lr)
        assert result.strip().startswith("<svg")

    def test_width_and_height_attributes(self):
        d = _simple_diagram()
        lr = _simple_layout()
        root = _parse(render_svg(d, lr))
        assert root.get("width") is not None
        assert root.get("height") is not None
