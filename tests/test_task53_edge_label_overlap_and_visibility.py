"""Tests for task 53: edge label overlap fix and edge style visibility."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from pymermaid.ir import Edge, EdgeType
from pymermaid.layout import EdgeLayout, Point
from pymermaid.render.edges import (
    _STYLE_MAP,
    _label_bbox,
    _rects_overlap,
    resolve_label_positions,
)

# ---------------------------------------------------------------------------
# Helpers (reused from test_edge_label_positioning.py)
# ---------------------------------------------------------------------------

_NS = "http://www.w3.org/2000/svg"


def _make_edge_layout(
    source: str, target: str, points: list[tuple[float, float]],
) -> EdgeLayout:
    return EdgeLayout(
        source=source,
        target=target,
        points=[Point(x=x, y=y) for x, y in points],
    )


def _make_ir_edge(
    source: str, target: str, label: str,
    edge_type: EdgeType = EdgeType.arrow,
) -> Edge:
    return Edge(source=source, target=target, label=label, edge_type=edge_type)


def _iter_edge_groups(root: ET.Element) -> list[ET.Element]:
    """Find all <g class="edge"> elements, handling SVG namespace."""
    results = []
    for g in root.iter(f"{{{_NS}}}g"):
        if g.get("class") == "edge":
            results.append(g)
    for g in root.iter("g"):
        if g.get("class") == "edge" and g not in results:
            results.append(g)
    return results


def _find_child(parent: ET.Element, tag: str) -> ET.Element | None:
    el = parent.find(f"{{{_NS}}}{tag}")
    if el is None:
        el = parent.find(tag)
    return el


def _find_children(parent: ET.Element, tag: str) -> list[ET.Element]:
    results = parent.findall(f"{{{_NS}}}{tag}")
    if not results:
        results = parent.findall(tag)
    return results


# ===========================================================================
# Unit: resolve_label_positions x-axis overlap fix
# ===========================================================================

class TestResolveLabelPositionsXAxisOverlap:
    def test_overlapping_x_ranges_same_y_midpoint(self) -> None:
        """Two edges with overlapping x-ranges but same y midpoint:
        after resolve, their label bounding boxes must not overlap."""
        # Edge 1: midpoint at (65, 100)
        el1 = _make_edge_layout("B", "D", [(65, 0), (65, 200)])
        ir1 = _make_ir_edge("B", "D", "long label text")

        # Edge 2: midpoint at (80, 100) -- close x, same y
        el2 = _make_edge_layout("C", "D", [(80, 0), (80, 200)])
        ir2 = _make_ir_edge("C", "D", "dotted label")

        result = resolve_label_positions([(el1, ir1), (el2, ir2)])

        pos1 = result[("B", "D")]
        pos2 = result[("C", "D")]
        bb1 = _label_bbox("long label text", pos1[0], pos1[1])
        bb2 = _label_bbox("dotted label", pos2[0], pos2[1])
        assert not _rects_overlap(bb1, bb2), (
            f"Bounding boxes overlap: {bb1} vs {bb2}"
        )

    def test_reproduces_labeled_edges_bug(self) -> None:
        """Labels 'long label text' and 'dotted label' placed at positions
        that reproduce the original bug: cx close together, cy close together.
        After resolution, bounding boxes must not overlap."""
        # Simulate the original positions that caused the bug:
        # "long label text" centered at ~65, "dotted label" at ~83
        el1 = _make_edge_layout("B", "D", [(65, 80), (65, 160)])
        ir1 = _make_ir_edge("B", "D", "long label text")

        el2 = _make_edge_layout("C", "D", [(83, 80), (83, 160)])
        ir2 = _make_ir_edge("C", "D", "dotted label")

        result = resolve_label_positions([(el1, ir1), (el2, ir2)])

        pos1 = result[("B", "D")]
        pos2 = result[("C", "D")]
        bb1 = _label_bbox("long label text", pos1[0], pos1[1])
        bb2 = _label_bbox("dotted label", pos2[0], pos2[1])
        assert not _rects_overlap(bb1, bb2), (
            f"Bounding boxes overlap after resolution: {bb1} vs {bb2}"
        )


# ===========================================================================
# Unit: _STYLE_MAP dash pattern values
# ===========================================================================

class TestStyleMapValues:
    def test_dotted_dasharray_not_single_3(self) -> None:
        """Dotted edges must NOT use the old single-number '3' pattern."""
        da = _STYLE_MAP[EdgeType.dotted]["stroke-dasharray"]
        assert da != "3", f"stroke-dasharray should not be '3', got {da!r}"

    def test_dotted_dasharray_comma_separated(self) -> None:
        """Dotted edges must have comma-separated dash values."""
        da = _STYLE_MAP[EdgeType.dotted]["stroke-dasharray"]
        assert "," in da, f"Expected comma-separated, got {da!r}"

    def test_dotted_dasharray_components_gte_5(self) -> None:
        """Each numeric component of the dash array must be >= 5."""
        da = _STYLE_MAP[EdgeType.dotted]["stroke-dasharray"]
        parts = [float(x.strip()) for x in da.split(",")]
        for part in parts:
            assert part >= 5, f"Dash component {part} < 5 in {da!r}"

    def test_dotted_arrow_dasharray_same_pattern(self) -> None:
        """dotted_arrow should have the same dash pattern as dotted."""
        da = _STYLE_MAP[EdgeType.dotted_arrow]["stroke-dasharray"]
        assert "," in da, f"Expected comma-separated, got {da!r}"
        parts = [float(x.strip()) for x in da.split(",")]
        for part in parts:
            assert part >= 5, f"Dash component {part} < 5 in {da!r}"

    def test_thick_stroke_width_gte_3_5(self) -> None:
        """Thick edges must have stroke-width >= 3.5."""
        sw = float(_STYLE_MAP[EdgeType.thick]["stroke-width"])
        assert sw >= 3.5, f"Thick stroke-width {sw} < 3.5"

    def test_thick_arrow_stroke_width_gte_3_5(self) -> None:
        """thick_arrow edges must have stroke-width >= 3.5."""
        sw = float(_STYLE_MAP[EdgeType.thick_arrow]["stroke-width"])
        assert sw >= 3.5, f"Thick arrow stroke-width {sw} < 3.5"


# ===========================================================================
# Integration: labeled_edges.mmd full render -- no label overlap
# ===========================================================================

class TestLabeledEdgesIntegrationNoOverlap:
    def test_all_five_labels_present(self) -> None:
        """All 5 expected labels must be present in the rendered SVG."""
        from pymermaid import render_diagram

        source = (
            "graph TD\n"
            "    A -->|yes| B\n"
            "    A -->|no| C\n"
            "    B -- long label text --> D\n"
            "    C -. dotted label .-> D\n"
            "    D == thick label ==> E\n"
        )
        svg = render_diagram(source)
        root = ET.fromstring(svg)

        labels_found: list[str] = []
        for g in _iter_edge_groups(root):
            text = _find_child(g, "text")
            if text is None:
                continue
            label_text = text.text or ""
            if not label_text:
                tspans = _find_children(text, "tspan")
                parts = [ts.text or "" for ts in tspans]
                label_text = " ".join(parts)
            if label_text:
                labels_found.append(label_text)

        expected = {"yes", "no", "long label text", "dotted label", "thick label"}
        assert set(labels_found) == expected, (
            f"Expected {expected}, got {set(labels_found)}"
        )

    def test_no_pairwise_rect_overlap(self) -> None:
        """No pair of label background rects should overlap."""
        from pymermaid import render_diagram

        source = (
            "graph TD\n"
            "    A -->|yes| B\n"
            "    A -->|no| C\n"
            "    B -- long label text --> D\n"
            "    C -. dotted label .-> D\n"
            "    D == thick label ==> E\n"
        )
        svg = render_diagram(source)
        root = ET.fromstring(svg)

        rects: list[tuple[float, float, float, float]] = []
        labels_found: list[str] = []

        for g in _iter_edge_groups(root):
            rect = _find_child(g, "rect")
            text = _find_child(g, "text")
            if rect is None or text is None:
                continue
            x = float(rect.get("x", "0"))
            y = float(rect.get("y", "0"))
            w = float(rect.get("width", "0"))
            h = float(rect.get("height", "0"))
            rects.append((x, y, w, h))
            label_text = text.text or ""
            if not label_text:
                tspans = _find_children(text, "tspan")
                parts = [ts.text or "" for ts in tspans]
                label_text = " ".join(parts)
            labels_found.append(label_text)

        # Verify we found labels (sanity check)
        assert len(rects) == 5, f"Expected 5 label rects, got {len(rects)}"

        for i in range(len(rects)):
            for j in range(i + 1, len(rects)):
                assert not _rects_overlap(rects[i], rects[j]), (
                    f"Labels {labels_found[i]!r} and {labels_found[j]!r} overlap: "
                    f"{rects[i]} vs {rects[j]}"
                )


# ===========================================================================
# Integration: dotted edge has visible dash pattern
# ===========================================================================

class TestDottedEdgeVisibleDash:
    def test_dotted_edge_has_visible_dasharray(self) -> None:
        """The dotted edge C->D must have stroke-dasharray with components >= 5."""
        from pymermaid import render_diagram

        source = (
            "graph TD\n"
            "    A -->|yes| B\n"
            "    A -->|no| C\n"
            "    B -- long label text --> D\n"
            "    C -. dotted label .-> D\n"
            "    D == thick label ==> E\n"
        )
        svg = render_diagram(source)
        root = ET.fromstring(svg)

        found = False
        for g in _iter_edge_groups(root):
            if g.get("data-edge-source") == "C" and g.get("data-edge-target") == "D":
                path = _find_child(g, "path")
                assert path is not None, "No <path> in C->D edge group"
                da = path.get("stroke-dasharray")
                assert da is not None, "C->D edge missing stroke-dasharray"
                parts = [float(x.strip()) for x in da.split(",")]
                for part in parts:
                    assert part >= 5, (
                        f"Dash component {part} < 5 in C->D edge dasharray {da!r}"
                    )
                found = True
                break

        assert found, "Could not find edge group with source=C, target=D"


# ===========================================================================
# Integration: thick edge has visible stroke
# ===========================================================================

class TestThickEdgeVisibleStroke:
    def test_thick_edge_has_sufficient_stroke_width(self) -> None:
        """The thick edge D->E must have stroke-width >= 3.5."""
        from pymermaid import render_diagram

        source = (
            "graph TD\n"
            "    A -->|yes| B\n"
            "    A -->|no| C\n"
            "    B -- long label text --> D\n"
            "    C -. dotted label .-> D\n"
            "    D == thick label ==> E\n"
        )
        svg = render_diagram(source)
        root = ET.fromstring(svg)

        found = False
        for g in _iter_edge_groups(root):
            if g.get("data-edge-source") == "D" and g.get("data-edge-target") == "E":
                path = _find_child(g, "path")
                assert path is not None, "No <path> in D->E edge group"
                sw = path.get("stroke-width")
                assert sw is not None, "D->E edge missing stroke-width"
                assert float(sw) >= 3.5, (
                    f"D->E edge stroke-width {sw} < 3.5"
                )
                found = True
                break

        assert found, "Could not find edge group with source=D, target=E"
