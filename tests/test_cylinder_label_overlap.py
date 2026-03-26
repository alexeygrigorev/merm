"""Tests for cylinder label overlap fix.

Forward-edge labels whose center falls inside a node bounding box should
be pushed out, preventing label-on-node overlap in LR layouts.
"""

import xml.etree.ElementTree as ET

from merm.ir import Edge, EdgeType
from merm.layout import EdgeLayout, Point
from merm.render.edges import (
    _label_bbox,
    _rects_overlap,
    resolve_label_positions,
)

_NS = "http://www.w3.org/2000/svg"

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
# Unit: forward-edge labels pushed out of node bboxes
# ---------------------------------------------------------------------------

class TestForwardEdgeLabelNodeOverlap:
    """Forward-edge labels whose center is inside a node must be pushed out."""

    def test_lr_forward_label_inside_node_gets_pushed(self) -> None:
        """LR layout: edge midpoint lands inside target node -> push out."""
        # Simulate an LR edge from (0,50) to (120,50).
        # Midpoint is (60,50), which is inside the target node bbox.
        el = _make_edge_layout("A", "B", [(0, 50), (120, 50)])
        ir = _make_ir_edge("A", "B", "label")

        # Target node B spans x=50..150, y=20..80 (center at 100,50).
        node_bboxes = [(50.0, 20.0, 100.0, 60.0)]

        result = resolve_label_positions(
            labeled_edges=[(el, ir)],
            node_bboxes=node_bboxes,
        )

        pos = result[("A", "B")]
        label_bb = _label_bbox("label", pos[0], pos[1])
        lx, ly, lw, lh = label_bb
        nx, ny, nw, nh = node_bboxes[0]

        # Label must not overlap the node bbox.
        assert not _rects_overlap(label_bb, (nx, ny, nw, nh)), (
            f"Label bbox {label_bb} still overlaps node bbox {node_bboxes[0]}"
        )

    def test_lr_forward_label_outside_node_not_pushed(self) -> None:
        """LR layout: label center in the gap between nodes -> no push."""
        # Edge from (0,50) to (200,50), midpoint at (100,50).
        el = _make_edge_layout("A", "B", [(0, 50), (200, 50)])
        ir = _make_ir_edge("A", "B", "label")

        # Node A: x=0..40, Node B: x=160..200.
        # Label center (100,50) is NOT inside either node.
        node_bboxes = [
            (0.0, 20.0, 40.0, 60.0),
            (160.0, 20.0, 40.0, 60.0),
        ]

        result = resolve_label_positions(
            labeled_edges=[(el, ir)],
            node_bboxes=node_bboxes,
        )

        pos = result[("A", "B")]
        # Label should stay near the midpoint (100, 50).
        assert abs(pos[0] - 100.0) < 5.0, (
            f"Label was unexpectedly moved from midpoint: {pos}"
        )
        assert abs(pos[1] - 50.0) < 5.0, (
            f"Label was unexpectedly moved from midpoint: {pos}"
        )

    def test_tb_forward_label_in_gap_not_pushed(self) -> None:
        """TB layout: label center is in the inter-rank gap, not inside
        any node bbox -> should NOT be pushed."""
        # Vertical edge from (100, 0) to (100, 120), midpoint at (100, 60).
        el = _make_edge_layout("A", "B", [(100, 0), (100, 120)])
        ir = _make_ir_edge("A", "B", "label")

        # Node A: y=0..30. Node B: y=90..120.
        # Midpoint (100, 60) is in the gap between them.
        node_bboxes = [
            (70.0, 0.0, 60.0, 30.0),   # A
            (70.0, 90.0, 60.0, 30.0),   # B
        ]

        result = resolve_label_positions(
            labeled_edges=[(el, ir)],
            node_bboxes=node_bboxes,
        )

        pos = result[("A", "B")]
        # Should stay near midpoint.
        assert abs(pos[0] - 100.0) < 5.0
        assert abs(pos[1] - 60.0) < 5.0


# ---------------------------------------------------------------------------
# Unit: back-edge labels still pushed (no regression)
# ---------------------------------------------------------------------------

class TestBackEdgeLabelNodeOverlapPreserved:
    """Back-edge label node-bbox avoidance must still work."""

    def test_back_edge_label_pushed_from_node(self) -> None:
        """Back-edge label overlapping a node should still be pushed."""
        # Back-edge: 3+ points going upward (y decreases).
        el = _make_edge_layout("B", "A", [
            (100, 100), (150, 50), (100, 0),
        ])
        ir = _make_ir_edge("B", "A", "back")

        # Node at the apex area.
        node_bboxes = [(120.0, 20.0, 80.0, 60.0)]

        result = resolve_label_positions(
            labeled_edges=[(el, ir)],
            node_bboxes=node_bboxes,
        )

        pos = result[("B", "A")]
        label_bb = _label_bbox("back", pos[0], pos[1])
        # Must not overlap the node.
        assert not _rects_overlap(label_bb, node_bboxes[0]), (
            f"Back-edge label bbox {label_bb} overlaps node {node_bboxes[0]}"
        )


# ---------------------------------------------------------------------------
# Integration: cylinder LR diagram renders without label overlap
# ---------------------------------------------------------------------------

def _iter_groups_by_class(
    root: ET.Element, cls: str,
) -> list[ET.Element]:
    results = []
    for g in root.iter(f"{{{_NS}}}g"):
        if g.get("class") == cls:
            results.append(g)
    for g in root.iter("g"):
        if g.get("class") == cls and g not in results:
            results.append(g)
    return results


def _find_child(parent: ET.Element, tag: str) -> ET.Element | None:
    el = parent.find(f"{{{_NS}}}{tag}")
    if el is None:
        el = parent.find(tag)
    return el


def _extract_node_bboxes(root: ET.Element) -> list[tuple[float, float, float, float]]:
    """Extract node bounding boxes from SVG node groups."""
    bboxes = []
    for g in _iter_groups_by_class(root, "node"):
        # Nodes typically have a rect, or path-based shape.
        rect = _find_child(g, "rect")
        if rect is not None:
            x = float(rect.get("x", "0"))
            y = float(rect.get("y", "0"))
            w = float(rect.get("width", "0"))
            h = float(rect.get("height", "0"))
            bboxes.append((x, y, w, h))
    return bboxes


def _extract_label_bboxes(
    root: ET.Element,
) -> list[tuple[str, tuple[float, float, float, float]]]:
    """Extract edge-label bboxes: (label_text, (x, y, w, h))."""
    results = []
    for g in _iter_groups_by_class(root, "edge-label"):
        rect = _find_child(g, "rect")
        text = _find_child(g, "text")
        if rect is None or text is None:
            continue
        x = float(rect.get("x", "0"))
        y = float(rect.get("y", "0"))
        w = float(rect.get("width", "0"))
        h = float(rect.get("height", "0"))
        label_text = text.text or ""
        if not label_text:
            tspans = text.findall(f"{{{_NS}}}tspan")
            if not tspans:
                tspans = text.findall("tspan")
            label_text = " ".join(ts.text or "" for ts in tspans)
        results.append((label_text, (x, y, w, h)))
    return results


def _label_center_inside_node(
    lbb: tuple[float, float, float, float],
    nbb: tuple[float, float, float, float],
) -> bool:
    """Return True if the label center is inside the node bbox."""
    lcx = lbb[0] + lbb[2] / 2
    lcy = lbb[1] + lbb[3] / 2
    nx, ny, nw, nh = nbb
    return nx <= lcx <= nx + nw and ny <= lcy <= ny + nh


class TestCylinderLRIntegration:
    """Integration test: the diy_sqlite.mmd diagram must have no overlaps."""

    def test_label_centers_not_inside_nodes(self) -> None:
        """Label centers must not be inside any node bounding box."""
        from merm import render_diagram

        source = (
            "graph LR\n"
            "    App[Streamlit App] -->|logs & events| SQLite[(SQLite)]\n"
            "    SQLite --> Dashboard[Streamlit Dashboard]\n"
            "    SQLite --> Judge[Online Judge]\n"
            "    Judge -->|evaluation events| SQLite\n"
        )
        svg = render_diagram(source)
        root = ET.fromstring(svg)

        node_bboxes = _extract_node_bboxes(root)
        label_entries = _extract_label_bboxes(root)

        assert len(label_entries) >= 2, (
            f"Expected at least 2 labels, got {len(label_entries)}"
        )

        for label_text, lbb in label_entries:
            for nbb in node_bboxes:
                assert not _label_center_inside_node(lbb, nbb), (
                    f"Label {label_text!r} center is inside "
                    f"node bbox {nbb}"
                )

    def test_labels_do_not_overlap_each_other(self) -> None:
        from merm import render_diagram

        source = (
            "graph LR\n"
            "    App[Streamlit App] -->|logs & events| SQLite[(SQLite)]\n"
            "    SQLite --> Dashboard[Streamlit Dashboard]\n"
            "    SQLite --> Judge[Online Judge]\n"
            "    Judge -->|evaluation events| SQLite\n"
        )
        svg = render_diagram(source)
        root = ET.fromstring(svg)

        label_entries = _extract_label_bboxes(root)
        for i in range(len(label_entries)):
            for j in range(i + 1, len(label_entries)):
                assert not _rects_overlap(
                    label_entries[i][1], label_entries[j][1],
                ), (
                    f"Labels {label_entries[i][0]!r} and "
                    f"{label_entries[j][0]!r} overlap"
                )

    def test_labels_have_adequate_separation(self) -> None:
        """Labels pushed out of a cylinder must have visible separation."""
        from merm import render_diagram

        source = (
            "graph LR\n"
            "    App[Streamlit App] -->|logs & events| SQLite[(SQLite)]\n"
            "    SQLite --> Dashboard[Streamlit Dashboard]\n"
            "    SQLite --> Judge[Online Judge]\n"
            "    Judge -->|evaluation events| SQLite\n"
        )
        svg = render_diagram(source)
        root = ET.fromstring(svg)

        label_entries = _extract_label_bboxes(root)
        assert len(label_entries) >= 2

        min_gap = 15.0  # at least 15px separation
        for i in range(len(label_entries)):
            for j in range(i + 1, len(label_entries)):
                bb_i = label_entries[i][1]
                bb_j = label_entries[j][1]
                # Compute minimum distance on each axis.
                x_gap = max(bb_j[0] - (bb_i[0] + bb_i[2]),
                            bb_i[0] - (bb_j[0] + bb_j[2]))
                y_gap = max(bb_j[1] - (bb_i[1] + bb_i[3]),
                            bb_i[1] - (bb_j[1] + bb_j[3]))
                separation = max(x_gap, y_gap)
                assert separation >= min_gap, (
                    f"Labels {label_entries[i][0]!r} and "
                    f"{label_entries[j][0]!r} are only {separation:.1f}px "
                    f"apart (minimum {min_gap}px)"
                )


class TestRectangularLRIntegration:
    """Non-cylinder LR diagram with edge labels -- no regression."""

    def test_rectangular_lr_label_centers_not_on_nodes(self) -> None:
        """In a simple LR diagram, label centers must not be inside nodes."""
        from merm import render_diagram

        source = (
            "graph LR\n"
            "    A[Source] -->|data flow| B[Target]\n"
            "    B -->|response| C[Sink]\n"
        )
        svg = render_diagram(source)
        root = ET.fromstring(svg)

        node_bboxes = _extract_node_bboxes(root)
        label_entries = _extract_label_bboxes(root)

        assert len(label_entries) >= 2, (
            f"Expected at least 2 labels, got {len(label_entries)}"
        )

        for label_text, lbb in label_entries:
            for nbb in node_bboxes:
                assert not _label_center_inside_node(lbb, nbb), (
                    f"Label {label_text!r} center is inside "
                    f"node bbox {nbb}"
                )
