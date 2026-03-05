"""Tests for the edge rendering module."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from pymermaid.ir import (
    ArrowType,
    Diagram,
    DiagramType,
    Direction,
    Edge,
    EdgeType,
    Node,
)
from pymermaid.layout import EdgeLayout, LayoutResult, NodeLayout, Point
from pymermaid.render import render_svg
from pymermaid.render.edges import make_edge_defs, points_to_path_d, render_edge

_SVG_NS = "http://www.w3.org/2000/svg"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _defs_element() -> ET.Element:
    """Create a <defs> element and populate it with markers."""
    defs = ET.Element("defs")
    make_edge_defs(defs)
    return defs


def _find_markers(parent: ET.Element) -> list[ET.Element]:
    return [el for el in parent.iter() if el.tag in ("marker", f"{{{_SVG_NS}}}marker")]


def _make_edge_layout(
    source: str = "A",
    target: str = "B",
    points: list[tuple[float, float]] | None = None,
) -> EdgeLayout:
    if points is None:
        points = [(10.0, 10.0), (10.0, 100.0)]
    return EdgeLayout(
        source=source,
        target=target,
        points=[Point(x=x, y=y) for x, y in points],
    )


def _render_edge_to_group(
    ir_edge: Edge | None = None,
    edge_layout: EdgeLayout | None = None,
    smooth: bool = True,
) -> ET.Element:
    """Render a single edge into a parent <g> and return the parent."""
    parent = ET.Element("g")
    if edge_layout is None:
        edge_layout = _make_edge_layout()
    render_edge(parent, edge_layout, ir_edge, smooth=smooth)
    return parent


def _find_path(parent: ET.Element) -> ET.Element | None:
    for el in parent.iter():
        if el.tag in ("path", f"{{{_SVG_NS}}}path"):
            return el
    return None


def _find_texts(parent: ET.Element) -> list[ET.Element]:
    return [el for el in parent.iter() if el.tag in ("text", f"{{{_SVG_NS}}}text")]


def _find_rects(parent: ET.Element) -> list[ET.Element]:
    return [el for el in parent.iter() if el.tag in ("rect", f"{{{_SVG_NS}}}rect")]


def _simple_layout(
    edge_source: str = "A",
    edge_target: str = "B",
) -> LayoutResult:
    return LayoutResult(
        nodes={
            "A": NodeLayout(x=20.0, y=10.0, width=80.0, height=40.0),
            "B": NodeLayout(x=20.0, y=80.0, width=80.0, height=40.0),
        },
        edges=[
            EdgeLayout(
                source=edge_source,
                target=edge_target,
                points=[Point(x=60.0, y=50.0), Point(x=60.0, y=80.0)],
            ),
        ],
        width=200.0,
        height=150.0,
    )


def _simple_diagram(
    edge_type: EdgeType = EdgeType.arrow,
    target_arrow: ArrowType = ArrowType.arrow,
    source_arrow: ArrowType = ArrowType.none,
    label: str | None = None,
) -> Diagram:
    return Diagram(
        type=DiagramType.flowchart,
        direction=Direction.TB,
        nodes=(Node(id="A", label="A"), Node(id="B", label="B")),
        edges=(
            Edge(
                source="A",
                target="B",
                edge_type=edge_type,
                target_arrow=target_arrow,
                source_arrow=source_arrow,
                label=label,
            ),
        ),
    )


def _parse(svg_str: str) -> ET.Element:
    return ET.fromstring(svg_str)


# =========================================================================
# Unit: Marker definitions
# =========================================================================


class TestMarkerDefinitions:
    def test_creates_four_markers(self):
        defs = _defs_element()
        markers = _find_markers(defs)
        assert len(markers) == 4

    def test_marker_ids(self):
        defs = _defs_element()
        markers = _find_markers(defs)
        ids = {m.get("id") for m in markers}
        assert ids == {"arrow", "circle-end", "cross-end", "arrow-reverse"}

    def test_marker_required_attributes(self):
        defs = _defs_element()
        for m in _find_markers(defs):
            assert m.get("id") is not None
            assert m.get("markerWidth") is not None
            assert m.get("markerHeight") is not None
            assert m.get("refX") is not None
            assert m.get("refY") is not None
            assert m.get("orient") is not None
            assert m.get("markerUnits") is not None

    def test_arrow_marker_contains_path(self):
        defs = _defs_element()
        for m in _find_markers(defs):
            if m.get("id") == "arrow":
                paths = [c for c in m if c.tag in ("path", f"{{{_SVG_NS}}}path")]
                assert len(paths) == 1
                assert paths[0].get("fill") is not None

    def test_circle_marker_contains_circle(self):
        defs = _defs_element()
        for m in _find_markers(defs):
            if m.get("id") == "circle-end":
                circles = [c for c in m if c.tag in ("circle", f"{{{_SVG_NS}}}circle")]
                assert len(circles) == 1

    def test_cross_marker_contains_path(self):
        defs = _defs_element()
        for m in _find_markers(defs):
            if m.get("id") == "cross-end":
                paths = [c for c in m if c.tag in ("path", f"{{{_SVG_NS}}}path")]
                assert len(paths) == 1


# =========================================================================
# Unit: Edge line styles
# =========================================================================


class TestEdgeLineStyles:
    def test_arrow_no_dasharray(self):
        edge = Edge(source="A", target="B", edge_type=EdgeType.arrow)
        g = _render_edge_to_group(ir_edge=edge)
        path = _find_path(g)
        assert path is not None
        assert path.get("stroke-dasharray") is None

    def test_arrow_has_marker_end(self):
        edge = Edge(source="A", target="B", edge_type=EdgeType.arrow)
        g = _render_edge_to_group(ir_edge=edge)
        path = _find_path(g)
        assert path is not None
        assert "arrow" in (path.get("marker-end") or "")

    def test_open_no_marker_end(self):
        edge = Edge(
            source="A", target="B",
            edge_type=EdgeType.open,
            target_arrow=ArrowType.none,
        )
        g = _render_edge_to_group(ir_edge=edge)
        path = _find_path(g)
        assert path is not None
        assert path.get("marker-end") is None

    def test_dotted_arrow_has_dasharray_and_marker(self):
        edge = Edge(source="A", target="B", edge_type=EdgeType.dotted_arrow)
        g = _render_edge_to_group(ir_edge=edge)
        path = _find_path(g)
        assert path is not None
        assert path.get("stroke-dasharray") is not None
        assert "arrow" in (path.get("marker-end") or "")

    def test_dotted_has_dasharray_no_arrow(self):
        edge = Edge(
            source="A", target="B",
            edge_type=EdgeType.dotted,
            target_arrow=ArrowType.none,
        )
        g = _render_edge_to_group(ir_edge=edge)
        path = _find_path(g)
        assert path is not None
        assert path.get("stroke-dasharray") is not None
        assert path.get("marker-end") is None

    def test_thick_arrow_has_thick_stroke_and_marker(self):
        edge = Edge(source="A", target="B", edge_type=EdgeType.thick_arrow)
        g = _render_edge_to_group(ir_edge=edge)
        path = _find_path(g)
        assert path is not None
        assert float(path.get("stroke-width", "0")) >= 3.0
        assert "arrow" in (path.get("marker-end") or "")

    def test_thick_has_thick_stroke_no_arrow(self):
        edge = Edge(
            source="A", target="B",
            edge_type=EdgeType.thick,
            target_arrow=ArrowType.none,
        )
        g = _render_edge_to_group(ir_edge=edge)
        path = _find_path(g)
        assert path is not None
        assert float(path.get("stroke-width", "0")) >= 3.0
        assert path.get("marker-end") is None

    def test_invisible_hidden(self):
        edge = Edge(source="A", target="B", edge_type=EdgeType.invisible)
        g = _render_edge_to_group(ir_edge=edge)
        path = _find_path(g)
        assert path is not None
        hidden = path.get("visibility") == "hidden" or path.get("stroke") == "none"
        assert hidden


# =========================================================================
# Unit: Marker assignment
# =========================================================================


class TestMarkerAssignment:
    def test_target_arrow_arrow(self):
        edge = Edge(source="A", target="B", target_arrow=ArrowType.arrow)
        g = _render_edge_to_group(ir_edge=edge)
        path = _find_path(g)
        assert "arrow" in (path.get("marker-end") or "")

    def test_target_arrow_circle(self):
        edge = Edge(
            source="A", target="B",
            edge_type=EdgeType.arrow,
            target_arrow=ArrowType.circle,
        )
        g = _render_edge_to_group(ir_edge=edge)
        path = _find_path(g)
        assert "circle" in (path.get("marker-end") or "")

    def test_target_arrow_cross(self):
        edge = Edge(
            source="A", target="B",
            edge_type=EdgeType.arrow,
            target_arrow=ArrowType.cross,
        )
        g = _render_edge_to_group(ir_edge=edge)
        path = _find_path(g)
        assert "cross" in (path.get("marker-end") or "")

    def test_target_arrow_none(self):
        edge = Edge(
            source="A", target="B",
            edge_type=EdgeType.open,
            target_arrow=ArrowType.none,
        )
        g = _render_edge_to_group(ir_edge=edge)
        path = _find_path(g)
        assert path.get("marker-end") is None

    def test_source_arrow_arrow(self):
        edge = Edge(
            source="A", target="B",
            source_arrow=ArrowType.arrow,
        )
        g = _render_edge_to_group(ir_edge=edge)
        path = _find_path(g)
        assert path.get("marker-start") is not None
        assert "arrow-reverse" in path.get("marker-start", "")

    def test_source_arrow_none(self):
        edge = Edge(
            source="A", target="B",
            source_arrow=ArrowType.none,
        )
        g = _render_edge_to_group(ir_edge=edge)
        path = _find_path(g)
        assert path.get("marker-start") is None


# =========================================================================
# Unit: Path generation
# =========================================================================


class TestPathGeneration:
    def test_empty_list(self):
        assert points_to_path_d([]) == ""

    def test_single_point(self):
        d = points_to_path_d([Point(5.0, 10.0)])
        assert d.startswith("M")
        assert "5.0" in d
        assert "10.0" in d

    def test_two_points_m_and_l(self):
        d = points_to_path_d([Point(0, 0), Point(10, 20)])
        assert d.startswith("M")
        assert "L" in d

    def test_four_points_smooth_has_c(self):
        pts = [Point(0, 0), Point(10, 10), Point(20, 5), Point(30, 15)]
        d = points_to_path_d(pts, smooth=True)
        assert d.startswith("M")
        assert "C" in d

    def test_four_points_no_smooth_only_m_l(self):
        pts = [Point(0, 0), Point(10, 10), Point(20, 5), Point(30, 15)]
        d = points_to_path_d(pts, smooth=False)
        assert d.startswith("M")
        assert "C" not in d
        assert "L" in d

    def test_path_is_parseable(self):
        pts = [Point(0, 0), Point(10, 10), Point(20, 5), Point(30, 15)]
        d = points_to_path_d(pts, smooth=True)
        # Must start with M and contain valid commands
        assert d[0] == "M"
        # Only M, L, C commands expected
        allowed_commands = set("MLCmlc")
        for ch in d:
            if ch.isalpha():
                assert ch in allowed_commands, f"Unexpected command: {ch}"


# =========================================================================
# Unit: Edge labels
# =========================================================================


class TestEdgeLabels:
    def test_label_renders_text(self):
        edge = Edge(source="A", target="B", label="Yes")
        g = _render_edge_to_group(ir_edge=edge)
        texts = _find_texts(g)
        assert len(texts) >= 1
        all_text = "".join(el.text or "" for el in g.iter())
        assert "Yes" in all_text

    def test_label_has_background_rect(self):
        edge = Edge(source="A", target="B", label="Yes")
        g = _render_edge_to_group(ir_edge=edge)
        rects = _find_rects(g)
        assert len(rects) >= 1
        # At least one rect should have a background fill
        bg_fills = ("white", "#fff", "#ffffff", "rgba(232,232,232,0.8)")
        bg_rects = [r for r in rects if r.get("fill") in bg_fills]
        assert len(bg_rects) >= 1

    def test_rect_before_text_in_dom(self):
        edge = Edge(source="A", target="B", label="Yes")
        g = _render_edge_to_group(ir_edge=edge)
        # In the edge group, find the first rect and first text
        edge_g = list(g)[0]  # the edge <g>
        children_tags = [c.tag for c in edge_g]
        # path comes first, then rect, then text
        rect_idx = None
        text_idx = None
        for i, tag in enumerate(children_tags):
            if tag in ("rect", f"{{{_SVG_NS}}}rect") and rect_idx is None:
                rect_idx = i
            if tag in ("text", f"{{{_SVG_NS}}}text") and text_idx is None:
                text_idx = i
        assert rect_idx is not None
        assert text_idx is not None
        assert rect_idx < text_idx

    def test_label_text_anchor_middle(self):
        edge = Edge(source="A", target="B", label="Yes")
        g = _render_edge_to_group(ir_edge=edge)
        texts = _find_texts(g)
        assert any(t.get("text-anchor") == "middle" for t in texts)

    def test_no_label_no_text(self):
        edge = Edge(source="A", target="B", label=None)
        g = _render_edge_to_group(ir_edge=edge)
        texts = _find_texts(g)
        assert len(texts) == 0

    def test_multiline_label_tspans(self):
        edge = Edge(source="A", target="B", label="Line1<br/>Line2")
        g = _render_edge_to_group(ir_edge=edge)
        tspans = [
            el for el in g.iter()
            if el.tag in ("tspan", f"{{{_SVG_NS}}}tspan")
        ]
        assert len(tspans) == 2
        assert tspans[0].text == "Line1"
        assert tspans[1].text == "Line2"


# =========================================================================
# Unit: Edge label positioning
# =========================================================================


class TestEdgeLabelPositioning:
    def test_label_at_midpoint_2_points(self):
        el = _make_edge_layout(points=[(0, 0), (100, 200)])
        edge = Edge(source="A", target="B", label="mid")
        g = _render_edge_to_group(ir_edge=edge, edge_layout=el)
        texts = _find_texts(g)
        assert len(texts) == 1
        tx = float(texts[0].get("x", "0"))
        ty = float(texts[0].get("y", "0"))
        assert abs(tx - 50.0) < 1.0
        assert abs(ty - 100.0) < 1.0

    def test_label_at_midpoint_multi_segment(self):
        el = _make_edge_layout(points=[(0, 0), (50, 50), (100, 50), (150, 100)])
        edge = Edge(source="A", target="B", label="mid")
        g = _render_edge_to_group(ir_edge=edge, edge_layout=el)
        texts = _find_texts(g)
        assert len(texts) == 1
        # Midpoint is between points[1] and points[2]: (75, 50)
        tx = float(texts[0].get("x", "0"))
        ty = float(texts[0].get("y", "0"))
        assert abs(tx - 75.0) < 1.0
        assert abs(ty - 50.0) < 1.0


# =========================================================================
# Integration: Full render_svg with edges
# =========================================================================


class TestIntegrationRenderSvg:
    def test_arrow_edge_has_marker_end(self):
        d = _simple_diagram(edge_type=EdgeType.arrow)
        lr = _simple_layout()
        root = _parse(render_svg(d, lr))
        edge_groups = root.findall(".//*[@data-edge-source]")
        assert len(edge_groups) == 1
        path = _find_path(edge_groups[0])
        assert path is not None
        assert "arrow" in (path.get("marker-end") or "")

    def test_dotted_arrow_edge_has_dasharray(self):
        d = _simple_diagram(edge_type=EdgeType.dotted_arrow)
        lr = _simple_layout()
        root = _parse(render_svg(d, lr))
        edge_groups = root.findall(".//*[@data-edge-source]")
        path = _find_path(edge_groups[0])
        assert path.get("stroke-dasharray") is not None

    def test_circle_marker_in_defs_and_referenced(self):
        d = _simple_diagram(
            edge_type=EdgeType.arrow,
            target_arrow=ArrowType.circle,
        )
        lr = _simple_layout()
        root = _parse(render_svg(d, lr))
        # Check defs has circle-end marker
        markers = _find_markers(root)
        marker_ids = {m.get("id") for m in markers}
        assert "circle-end" in marker_ids
        # Check edge path references it
        edge_groups = root.findall(".//*[@data-edge-source]")
        path = _find_path(edge_groups[0])
        assert "circle-end" in (path.get("marker-end") or "")

    def test_edge_label_in_svg(self):
        d = _simple_diagram(label="Yes")
        lr = _simple_layout()
        root = _parse(render_svg(d, lr))
        edge_groups = root.findall(".//*[@data-edge-source]")
        g = edge_groups[0]
        rects = _find_rects(g)
        texts = _find_texts(g)
        assert len(rects) >= 1
        assert len(texts) >= 1
        all_text = "".join(el.text or "" for el in g.iter())
        assert "Yes" in all_text

    def test_old_arrowhead_marker_replaced(self):
        d = _simple_diagram()
        lr = _simple_layout()
        root = _parse(render_svg(d, lr))
        markers = _find_markers(root)
        marker_ids = {m.get("id") for m in markers}
        assert "arrowhead" not in marker_ids
        assert "arrow" in marker_ids


# =========================================================================
# Integration: All edge types produce valid SVG
# =========================================================================


class TestAllEdgeTypesValidSvg:
    def test_all_edge_types_well_formed(self):
        for et in EdgeType:
            # Choose appropriate arrow types
            if et in (EdgeType.arrow, EdgeType.dotted_arrow, EdgeType.thick_arrow):
                ta = ArrowType.arrow
            else:
                ta = ArrowType.none
            d = _simple_diagram(edge_type=et, target_arrow=ta)
            lr = _simple_layout()
            result = render_svg(d, lr)
            # Should parse as valid XML
            root = _parse(result)
            assert root.tag in ("svg", f"{{{_SVG_NS}}}svg"), (
                f"EdgeType.{et.name} produced invalid SVG root"
            )


