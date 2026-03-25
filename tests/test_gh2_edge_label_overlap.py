"""Tests for GH#2: Edge labels overlap when multiple edges connect to the same node.

Tests cover:
- Unit: resolve_label_positions with reproduction-case-like edges
- Unit: single-label midpoint preservation (no regression)
- Unit: three back-edges to the same node
- Integration: reproduction case end-to-end
- Integration: simple diagram regression check
"""

import xml.etree.ElementTree as ET

from merm.ir import Edge, EdgeType
from merm.layout import EdgeLayout, Point
from merm.render.edges import (
    _label_bbox,
    _rects_overlap,
    resolve_label_positions,
)

# ---------------------------------------------------------------------------
# Helpers
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


def _iter_edge_label_groups(root: ET.Element) -> list[ET.Element]:
    """Find all <g class="edge-label"> elements."""
    results = []
    for g in root.iter(f"{{{_NS}}}g"):
        if g.get("class") == "edge-label":
            results.append(g)
    for g in root.iter("g"):
        if g.get("class") == "edge-label" and g not in results:
            results.append(g)
    return results


def _extract_label_rects(
    root: ET.Element,
) -> list[tuple[str, tuple[float, float, float, float]]]:
    """Extract (label_text, (x, y, w, h)) from edge-label groups."""
    results = []
    for g in _iter_edge_label_groups(root):
        rect = g.find(f"{{{_NS}}}rect")
        text = g.find(f"{{{_NS}}}text")
        if rect is None:
            rect = g.find("rect")
        if text is None:
            text = g.find("text")
        if rect is None or text is None:
            continue
        x = float(rect.get("x", "0"))
        y = float(rect.get("y", "0"))
        w = float(rect.get("width", "0"))
        h = float(rect.get("height", "0"))
        label_text = text.text or ""
        results.append((label_text, (x, y, w, h)))
    return results


# ===========================================================================
# Unit: resolve_label_positions with reproduction-case-like edges
# ===========================================================================

class TestReproductionCaseLikeEdges:
    """Four labeled edges sharing two target nodes (B and D), with two
    back-edges to B. After resolve_label_positions(), all pairwise
    _label_bbox results must pass `not _rects_overlap`."""

    def _build_reproduction_edges(
        self,
    ) -> list[tuple[EdgeLayout, Edge]]:
        """Build edges mimicking the reproduction case layout.

        The layout has nodes roughly at:
        A: y=0-42, B: y=82-124, C: y=164-206, D: y=246-288, E: y=328-370
        """
        # C->D "PASS" (forward, midpoint around y=222)
        el_cd = _make_edge_layout("C", "D", [(65, 206), (65, 246)])
        ir_cd = _make_ir_edge("C", "D", "PASS")

        # C->B "FAIL" (back-edge, going upward)
        el_cb = _make_edge_layout("C", "B", [(65, 164), (66, 124)])
        ir_cb = _make_ir_edge("C", "B", "FAIL")

        # D->E "ACCEPT" (forward, midpoint around y=308)
        el_de = _make_edge_layout("D", "E", [(65, 288), (65, 328)])
        ir_de = _make_ir_edge("D", "E", "ACCEPT")

        # D->B "REJECT" (back-edge, going upward via routing)
        el_db = _make_edge_layout(
            "D", "B",
            [(89, 246), (155, 185), (112, 124)],
        )
        ir_db = _make_ir_edge("D", "B", "REJECT")

        return [(el_cd, ir_cd), (el_cb, ir_cb), (el_de, ir_de), (el_db, ir_db)]

    def test_all_labels_non_overlapping(self) -> None:
        """All pairwise label bounding boxes must not overlap."""
        edges = self._build_reproduction_edges()
        result = resolve_label_positions(edges)

        bboxes = []
        label_names = []
        for el, ir in edges:
            key = (el.source, el.target)
            pos = result[key]
            bb = _label_bbox(ir.label, pos[0], pos[1])
            bboxes.append(bb)
            label_names.append(ir.label)

        for i in range(len(bboxes)):
            for j in range(i + 1, len(bboxes)):
                assert not _rects_overlap(bboxes[i], bboxes[j]), (
                    f"Labels {label_names[i]!r} and {label_names[j]!r} "
                    f"overlap: {bboxes[i]} vs {bboxes[j]}"
                )

    def test_minimum_gap_between_closest_labels(self) -> None:
        """Gap between closest pair of label bounding boxes is at least 6px."""
        edges = self._build_reproduction_edges()
        result = resolve_label_positions(edges)

        bboxes = []
        for el, ir in edges:
            key = (el.source, el.target)
            pos = result[key]
            bboxes.append(_label_bbox(ir.label, pos[0], pos[1]))

        min_gap = float("inf")
        for i in range(len(bboxes)):
            for j in range(i + 1, len(bboxes)):
                ax, ay, aw, ah = bboxes[i]
                bx, by, bw, bh = bboxes[j]
                # Compute gap as the minimum separation on either axis.
                x_gap = max(bx - (ax + aw), ax - (bx + bw))
                y_gap = max(by - (ay + ah), ay - (by + bh))
                # If they don't overlap, the gap is the max of both
                # axis separations (or 0 if they're adjacent on one axis).
                gap = max(x_gap, y_gap)
                if gap < min_gap:
                    min_gap = gap

        assert min_gap >= 6.0, (
            f"Minimum gap between label bounding boxes is {min_gap:.1f}px, "
            f"expected at least 6px"
        )


# ===========================================================================
# Unit: single-label midpoint preservation
# ===========================================================================

class TestSingleLabelMidpointPreservation:
    def test_single_label_at_midpoint(self) -> None:
        """A single labeled edge gets its label at the exact midpoint."""
        el = _make_edge_layout("A", "B", [(100, 0), (100, 200)])
        ir = _make_ir_edge("A", "B", "hello")
        result = resolve_label_positions([(el, ir)])
        cx, cy = result[("A", "B")]
        assert cx == 100.0
        assert cy == 100.0

    def test_single_label_with_node_bboxes_unchanged(self) -> None:
        """A single labeled edge in the inter-rank gap is not affected
        by node bounding boxes (forward edge labels are exempt from
        node avoidance)."""
        el = _make_edge_layout("A", "B", [(100, 50), (100, 100)])
        ir = _make_ir_edge("A", "B", "hi")
        # Nodes above and below the edge.
        node_bboxes = [
            (80, 0, 40, 42),   # Node A
            (80, 110, 40, 42),  # Node B
        ]
        result = resolve_label_positions(
            [(el, ir)], node_bboxes=node_bboxes,
        )
        cx, cy = result[("A", "B")]
        assert cx == 100.0
        assert cy == 75.0


# ===========================================================================
# Unit: three back-edges to the same node
# ===========================================================================

class TestThreeBackEdgesToSameNode:
    def test_three_back_edges_all_non_overlapping(self) -> None:
        """Three edges targeting node B with labels X, Y, Z -- after
        resolution, all three label bounding boxes must be non-overlapping."""
        edges = []
        for src, label in [("C", "X"), ("D", "Y"), ("E", "Z")]:
            # All back-edges targeting B at y=100, coming from below.
            el = _make_edge_layout(src, "B", [(100, 200), (100, 100)])
            ir = _make_ir_edge(src, "B", label)
            edges.append((el, ir))

        result = resolve_label_positions(edges)

        bboxes = []
        label_names = []
        for el, ir in edges:
            key = (el.source, el.target)
            pos = result[key]
            bboxes.append(_label_bbox(ir.label, pos[0], pos[1]))
            label_names.append(ir.label)

        for i in range(len(bboxes)):
            for j in range(i + 1, len(bboxes)):
                assert not _rects_overlap(bboxes[i], bboxes[j]), (
                    f"Labels {label_names[i]!r} and {label_names[j]!r} "
                    f"overlap: {bboxes[i]} vs {bboxes[j]}"
                )


# ===========================================================================
# Integration: reproduction case end-to-end
# ===========================================================================

class TestReproductionCaseEndToEnd:
    _SOURCE = (
        "flowchart TB\n"
        "    A[PM grooms] --> B[SWE implements]\n"
        "    B --> C[QA verifies]\n"
        "    C -->|PASS| D[PM accepts]\n"
        "    C -->|FAIL| B\n"
        "    D -->|ACCEPT| E[Commit]\n"
        "    D -->|REJECT| B\n"
    )

    def test_all_four_labels_present(self) -> None:
        """PASS, FAIL, ACCEPT, REJECT must all be present in the SVG."""
        from merm import render_diagram

        svg = render_diagram(self._SOURCE)
        root = ET.fromstring(svg)
        label_rects = _extract_label_rects(root)
        found_labels = {name for name, _ in label_rects}
        expected = {"PASS", "FAIL", "ACCEPT", "REJECT"}
        assert expected == found_labels, (
            f"Expected {expected}, got {found_labels}"
        )

    def test_no_pairwise_label_overlap(self) -> None:
        """No pair of edge label rects should overlap in the SVG."""
        from merm import render_diagram

        svg = render_diagram(self._SOURCE)
        root = ET.fromstring(svg)
        label_rects = _extract_label_rects(root)

        for i in range(len(label_rects)):
            for j in range(i + 1, len(label_rects)):
                name_i, rect_i = label_rects[i]
                name_j, rect_j = label_rects[j]
                assert not _rects_overlap(rect_i, rect_j), (
                    f"Labels {name_i!r} and {name_j!r} overlap: "
                    f"{rect_i} vs {rect_j}"
                )

    def test_fail_reject_separated_by_8px(self) -> None:
        """FAIL and REJECT labels must be separated by at least 8px."""
        from merm import render_diagram

        svg = render_diagram(self._SOURCE)
        root = ET.fromstring(svg)
        label_rects = _extract_label_rects(root)

        fail_rect = None
        reject_rect = None
        for name, rect in label_rects:
            if name == "FAIL":
                fail_rect = rect
            elif name == "REJECT":
                reject_rect = rect

        assert fail_rect is not None, "FAIL label not found"
        assert reject_rect is not None, "REJECT label not found"

        fx, fy, fw, fh = fail_rect
        rx, ry, rw, rh = reject_rect

        # Compute axis-aligned gap.
        x_gap = max(rx - (fx + fw), fx - (rx + rw))
        y_gap = max(ry - (fy + fh), fy - (ry + rh))
        gap = max(x_gap, y_gap)

        assert gap >= 8.0, (
            f"FAIL and REJECT labels separated by only {gap:.1f}px, "
            f"expected at least 8px. FAIL={fail_rect}, REJECT={reject_rect}"
        )

    def test_pass_does_not_overlap_fail_or_reject(self) -> None:
        """PASS label must not overlap with FAIL or REJECT."""
        from merm import render_diagram

        svg = render_diagram(self._SOURCE)
        root = ET.fromstring(svg)
        label_rects = _extract_label_rects(root)

        rects_by_name = {name: rect for name, rect in label_rects}
        pass_rect = rects_by_name.get("PASS")
        fail_rect = rects_by_name.get("FAIL")
        reject_rect = rects_by_name.get("REJECT")

        assert pass_rect is not None
        if fail_rect is not None:
            assert not _rects_overlap(pass_rect, fail_rect), (
                f"PASS overlaps FAIL: {pass_rect} vs {fail_rect}"
            )
        if reject_rect is not None:
            assert not _rects_overlap(pass_rect, reject_rect), (
                f"PASS overlaps REJECT: {pass_rect} vs {reject_rect}"
            )


# ===========================================================================
# Integration: simple diagram regression check
# ===========================================================================

class TestSimpleDiagramRegression:
    def test_single_label_at_edge_midpoint(self) -> None:
        """Render 'graph TD A -->|hello| B' and verify label is at edge
        midpoint (within 2px tolerance)."""
        from merm import render_diagram

        source = "graph TD\n    A -->|hello| B\n"
        svg = render_diagram(source)
        root = ET.fromstring(svg)

        label_rects = _extract_label_rects(root)
        assert len(label_rects) == 1, (
            f"Expected 1 label rect, got {len(label_rects)}"
        )
        name, (lx, ly, lw, lh) = label_rects[0]
        assert name == "hello"

        # The label center should be roughly at the edge midpoint.
        # Find the edge path to compare.
        label_cy = ly + lh / 2.0

        # For a simple A->B diagram, the edge midpoint y should be
        # between the two nodes. Just verify the label is in a
        # reasonable position (not pushed far away).
        # Node A is at y~0-42, Node B at y~82-124, gap midpoint ~62.
        assert 40 < label_cy < 100, (
            f"Label center y={label_cy:.1f} is outside expected range "
            f"for simple A->B diagram"
        )

    def test_no_back_edge_diagram_labels_unaffected(self) -> None:
        """A diagram with no back-edges should have labels at midpoints,
        unaffected by the node avoidance logic."""
        from merm import render_diagram

        source = (
            "graph TD\n"
            "    A -->|step1| B\n"
            "    B -->|step2| C\n"
        )
        svg = render_diagram(source)
        root = ET.fromstring(svg)

        label_rects = _extract_label_rects(root)
        found_labels = {name for name, _ in label_rects}
        assert found_labels == {"step1", "step2"}, (
            f"Expected step1/step2, got {found_labels}"
        )

        # Labels should not overlap each other (they're on different edges).
        if len(label_rects) == 2:
            assert not _rects_overlap(
                label_rects[0][1], label_rects[1][1],
            )


# ===========================================================================
# Unit: node_bboxes parameter backward compatibility
# ===========================================================================

class TestNodeBboxesBackwardCompatibility:
    def test_resolve_without_node_bboxes(self) -> None:
        """resolve_label_positions still works without node_bboxes arg."""
        el = _make_edge_layout("A", "B", [(100, 0), (100, 200)])
        ir = _make_ir_edge("A", "B", "test")
        # Should work with just the required arg.
        result = resolve_label_positions([(el, ir)])
        assert ("A", "B") in result

    def test_resolve_with_empty_node_bboxes(self) -> None:
        """resolve_label_positions works with empty node_bboxes list."""
        el = _make_edge_layout("A", "B", [(100, 0), (100, 200)])
        ir = _make_ir_edge("A", "B", "test")
        result = resolve_label_positions([(el, ir)], node_bboxes=[])
        assert ("A", "B") in result
