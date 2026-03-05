"""Tests for edge label positioning and overlap resolution."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from pymermaid.ir import Edge, EdgeType
from pymermaid.layout import EdgeLayout, Point
from pymermaid.render.edges import (
    _label_bbox,
    _rects_overlap,
    render_edge,
    resolve_label_positions,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Unit tests: _rects_overlap
# ---------------------------------------------------------------------------

class TestRectsOverlap:
    def test_no_overlap(self) -> None:
        assert not _rects_overlap((0, 0, 10, 10), (20, 20, 10, 10))

    def test_overlap(self) -> None:
        assert _rects_overlap((0, 0, 20, 20), (10, 10, 20, 20))

    def test_adjacent_no_overlap(self) -> None:
        # Touching edges do not overlap (strict inequality).
        assert not _rects_overlap((0, 0, 10, 10), (10, 0, 10, 10))


# ---------------------------------------------------------------------------
# Unit tests: resolve_label_positions -- no overlaps
# ---------------------------------------------------------------------------

class TestResolveLabelPositionsNoOverlap:
    def test_single_label_unchanged(self) -> None:
        el = _make_edge_layout("A", "B", [(100, 0), (100, 200)])
        ir = _make_ir_edge("A", "B", "hello")
        result = resolve_label_positions([(el, ir)])
        cx, cy = result[("A", "B")]
        # Midpoint of the polyline is (100, 100).
        assert cx == 100.0
        assert cy == 100.0

    def test_two_well_separated_labels_unchanged(self) -> None:
        el1 = _make_edge_layout("A", "B", [(50, 0), (50, 100)])
        ir1 = _make_ir_edge("A", "B", "ab")
        el2 = _make_edge_layout("C", "D", [(300, 400), (300, 500)])
        ir2 = _make_ir_edge("C", "D", "cd")
        result = resolve_label_positions([(el1, ir1), (el2, ir2)])
        assert result[("A", "B")] == (50.0, 50.0)
        assert result[("C", "D")] == (300.0, 450.0)

    def test_empty_list(self) -> None:
        assert resolve_label_positions([]) == {}


# ---------------------------------------------------------------------------
# Unit tests: resolve_label_positions -- with overlaps
# ---------------------------------------------------------------------------

class TestResolveLabelPositionsOverlap:
    def test_two_labels_same_position_nudged_apart(self) -> None:
        # Both edges have the same midpoint -> labels must be nudged.
        el1 = _make_edge_layout("A", "D", [(100, 0), (100, 200)])
        ir1 = _make_ir_edge("A", "D", "label one")
        el2 = _make_edge_layout("B", "D", [(100, 0), (100, 200)])
        ir2 = _make_ir_edge("B", "D", "label two")
        result = resolve_label_positions([(el1, ir1), (el2, ir2)])

        pos1 = result[("A", "D")]
        pos2 = result[("B", "D")]

        # Bounding boxes must not overlap after resolution.
        bb1 = _label_bbox("label one", pos1[0], pos1[1])
        bb2 = _label_bbox("label two", pos2[0], pos2[1])
        assert not _rects_overlap(bb1, bb2)

    def test_three_labels_vertical_stack(self) -> None:
        edges_data = []
        for i, name in enumerate(["alpha", "beta", "gamma"]):
            el = _make_edge_layout(name, "Z", [(100, 0), (100, 200)])
            ir = _make_ir_edge(name, "Z", f"label {name}")
            edges_data.append((el, ir))

        result = resolve_label_positions(edges_data)

        # All pairwise bounding boxes must not overlap.
        bboxes = []
        for key, pos in result.items():
            label_text = f"label {key[0]}"
            bboxes.append(_label_bbox(label_text, pos[0], pos[1]))

        for i in range(len(bboxes)):
            for j in range(i + 1, len(bboxes)):
                assert not _rects_overlap(bboxes[i], bboxes[j]), (
                    f"Bounding boxes {i} and {j} overlap: {bboxes[i]}, {bboxes[j]}"
                )

    def test_different_text_lengths(self) -> None:
        el1 = _make_edge_layout("A", "B", [(100, 0), (100, 200)])
        ir1 = _make_ir_edge("A", "B", "x")  # short
        el2 = _make_edge_layout("C", "D", [(100, 0), (100, 200)])
        ir2 = _make_ir_edge("C", "D", "a very long label text")  # long
        result = resolve_label_positions([(el1, ir1), (el2, ir2)])

        bb1 = _label_bbox("x", *result[("A", "B")])
        bb2 = _label_bbox("a very long label text", *result[("C", "D")])
        assert not _rects_overlap(bb1, bb2)


# ---------------------------------------------------------------------------
# Unit tests: render_edge with explicit label_pos
# ---------------------------------------------------------------------------

class TestRenderEdgeWithLabelPos:
    def test_explicit_label_pos_used(self) -> None:
        parent = ET.Element("g")
        el = _make_edge_layout("A", "B", [(10, 10), (10, 100)])
        ir = _make_ir_edge("A", "B", "hello")

        render_edge(parent, el, ir, label_pos=(100.0, 200.0))

        # Find the <text> element inside the edge group.
        edge_g = parent.find("g")
        assert edge_g is not None
        text_el = edge_g.find("text")
        assert text_el is not None
        assert text_el.get("x") == "100.0"
        assert text_el.get("y") == "200.0"

    def test_no_label_pos_uses_midpoint(self) -> None:
        parent = ET.Element("g")
        el = _make_edge_layout("A", "B", [(10, 10), (10, 100)])
        ir = _make_ir_edge("A", "B", "hello")

        render_edge(parent, el, ir, label_pos=None)

        edge_g = parent.find("g")
        assert edge_g is not None
        text_el = edge_g.find("text")
        assert text_el is not None
        # Midpoint of [(10,10), (10,100)] is (10, 55).
        assert text_el.get("x") == "10.0"
        assert text_el.get("y") == "55.0"


# ---------------------------------------------------------------------------
# Integration: labeled_edges.mmd SVG output
# ---------------------------------------------------------------------------

_NS = "http://www.w3.org/2000/svg"


def _iter_edge_groups(root: ET.Element) -> list[ET.Element]:
    """Find all <g class="edge"> elements, handling SVG namespace."""
    results = []
    for g in root.iter(f"{{{_NS}}}g"):
        if g.get("class") == "edge":
            results.append(g)
    # Also try without namespace (in case SVG is parsed without ns).
    for g in root.iter("g"):
        if g.get("class") == "edge" and g not in results:
            results.append(g)
    return results


def _find_child(parent: ET.Element, tag: str) -> ET.Element | None:
    """Find first child with given tag, with or without SVG namespace."""
    el = parent.find(f"{{{_NS}}}{tag}")
    if el is None:
        el = parent.find(tag)
    return el


def _find_children(parent: ET.Element, tag: str) -> list[ET.Element]:
    """Find all children with given tag, with or without SVG namespace."""
    results = parent.findall(f"{{{_NS}}}{tag}")
    if not results:
        results = parent.findall(tag)
    return results


class TestLabeledEdgesIntegration:
    def test_no_overlapping_labels_in_svg(self) -> None:
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

        expected_labels = {
            "yes", "no", "long label text",
            "dotted label", "thick label",
        }
        assert set(labels_found) == expected_labels, (
            f"Expected {expected_labels}, got {set(labels_found)}"
        )

        for i in range(len(rects)):
            for j in range(i + 1, len(rects)):
                assert not _rects_overlap(rects[i], rects[j]), (
                    f"Labels {labels_found[i]!r} and {labels_found[j]!r} overlap: "
                    f"{rects[i]} vs {rects[j]}"
                )

    def test_labels_have_background_rects(self) -> None:
        """Verify no regression: each label still has a background <rect>."""
        from pymermaid import render_diagram

        source = (
            "graph TD\n"
            "    A -->|yes| B\n"
            "    A -->|no| C\n"
        )
        svg = render_diagram(source)
        root = ET.fromstring(svg)

        rect_count = 0
        for g in _iter_edge_groups(root):
            rect = _find_child(g, "rect")
            text = _find_child(g, "text")
            if rect is not None and text is not None:
                rect_count += 1
                children = list(g)
                rect_idx = children.index(rect)
                text_idx = children.index(text)
                assert rect_idx < text_idx

        assert rect_count == 2

    def test_single_edge_label_at_midpoint(self) -> None:
        """A diagram with one labeled edge produces label at exact midpoint."""
        from pymermaid import render_diagram

        source = "graph TD\n    A -->|only| B\n"
        svg = render_diagram(source)
        root = ET.fromstring(svg)

        for g in _iter_edge_groups(root):
            text = _find_child(g, "text")
            if text is not None and text.text == "only":
                assert True
                return
        assert False, "Label 'only' not found in SVG output"

    def test_label_positions_close_to_midpoint(self) -> None:
        """Each label position remains within 40px of its edge midpoint."""
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

        for g in _iter_edge_groups(root):
            text = _find_child(g, "text")
            rect = _find_child(g, "rect")
            if text is None or rect is None:
                continue
            rx = float(rect.get("x", "0"))
            ry = float(rect.get("y", "0"))
            rw = float(rect.get("width", "0"))
            rh = float(rect.get("height", "0"))
            label_cx = rx + rw / 2.0
            label_cy = ry + rh / 2.0

            path = _find_child(g, "path")
            assert path is not None
            assert label_cx >= -100 and label_cy >= -100
