"""Tests for issue 92: ER diagram relationship labels must not overlap.

Verifies that relationship labels and cardinality markers have adequate
spacing and do not overlap each other in the rendered SVG.
"""

import xml.etree.ElementTree as ET

from merm import render_diagram
from merm.layout.erdiag import layout_er_diagram
from merm.measure import TextMeasurer
from merm.parser.erdiag import parse_er_diagram
from merm.render.erdiag import _midpoint

ALL_CARDINALITIES = """\
erDiagram
    A ||--|| B : "one to one"
    C ||--o{ D : "one to zero-or-more"
    E ||--|{ F : "one to one-or-more"
    G }o--o{ H : "zero-or-more to zero-or-more"
    I o|--|| J : "zero-or-one to one"
"""

BASIC_3_ENTITY = """\
erDiagram
    CUSTOMER ||--o{ ORDER : places
    ORDER ||--|{ LINE-ITEM : contains
    CUSTOMER }|..|{ DELIVERY-ADDRESS : uses
"""

_SVG_NS = "http://www.w3.org/2000/svg"

# Approximate character width used in the renderer for label background rects.
_LABEL_CHAR_W = 7.0
_LABEL_PAD = 4.0


def _get_label_rects(svg_str: str) -> list[tuple[float, float, float, float]]:
    """Extract label background rects from ER relationship groups.

    Returns list of (x, y, width, height) for each label background rect.
    """
    root = ET.fromstring(svg_str)
    rects = []
    for g in root.findall(f".//{{{_SVG_NS}}}g[@class='er-relationship']"):
        for rect in g.findall(f"{{{_SVG_NS}}}rect"):
            x = float(rect.get("x", "0"))
            y = float(rect.get("y", "0"))
            w = float(rect.get("width", "0"))
            h = float(rect.get("height", "0"))
            rects.append((x, y, w, h))
    return rects


def _get_label_texts(svg_str: str) -> list[tuple[float, float, str]]:
    """Extract label text elements from ER relationship groups.

    Returns list of (x, y, text_content) for each label.
    """
    root = ET.fromstring(svg_str)
    labels = []
    for g in root.findall(f".//{{{_SVG_NS}}}g[@class='er-relationship']"):
        for text_el in g.findall(f"{{{_SVG_NS}}}text"):
            x = float(text_el.get("x", "0"))
            y = float(text_el.get("y", "0"))
            labels.append((x, y, text_el.text or ""))
    return labels


def _rects_overlap(r1: tuple[float, float, float, float],
                   r2: tuple[float, float, float, float]) -> bool:
    """Check if two rectangles (x, y, w, h) overlap."""
    x1, y1, w1, h1 = r1
    x2, y2, w2, h2 = r2
    # No overlap if one is entirely to the left/right/above/below the other
    if x1 + w1 <= x2 or x2 + w2 <= x1:
        return False
    if y1 + h1 <= y2 or y2 + h2 <= y1:
        return False
    return True


class TestERLabelNoOverlap:
    """Relationship labels must not overlap each other."""

    def test_all_cardinalities_labels_no_overlap(self):
        """Labels in all_cardinalities fixture must not overlap."""
        svg = render_diagram(ALL_CARDINALITIES)
        rects = _get_label_rects(svg)
        assert len(rects) == 5, f"Expected 5 label rects, got {len(rects)}"
        for i in range(len(rects)):
            for j in range(i + 1, len(rects)):
                assert not _rects_overlap(rects[i], rects[j]), (
                    f"Label rects {i} and {j} overlap: {rects[i]} vs {rects[j]}"
                )

    def test_basic_3_entity_labels_no_overlap(self):
        """Labels in basic 3-entity diagram must not overlap."""
        svg = render_diagram(BASIC_3_ENTITY)
        rects = _get_label_rects(svg)
        assert len(rects) == 3, f"Expected 3 label rects, got {len(rects)}"
        for i in range(len(rects)):
            for j in range(i + 1, len(rects)):
                assert not _rects_overlap(rects[i], rects[j]), (
                    f"Label rects {i} and {j} overlap: {rects[i]} vs {rects[j]}"
                )

    def test_all_labels_readable(self):
        """All five cardinality labels must appear as text in SVG."""
        svg = render_diagram(ALL_CARDINALITIES)
        labels = _get_label_texts(svg)
        texts = {lbl[2] for lbl in labels}
        expected = {
            "one to one",
            "one to zero-or-more",
            "one to one-or-more",
            "zero-or-more to zero-or-more",
            "zero-or-one to one",
        }
        assert expected == texts, f"Missing labels: {expected - texts}"


class TestERLabelSpacing:
    """Labels must have adequate spacing from entities and each other."""

    def test_node_sep_accounts_for_label_width(self):
        """Layout node_sep must be at least as wide as the longest label."""
        diagram = parse_er_diagram(ALL_CARDINALITIES)
        measurer = TextMeasurer()
        layout = layout_er_diagram(diagram, measure_fn=measurer.measure)

        # Compute edge midpoints (x values) for all edges
        edge_xs = []
        for el in layout.edges:
            mid = _midpoint(el.points)
            edge_xs.append(mid.x)
        edge_xs.sort()

        # Minimum gap between adjacent edge midpoints
        min_gap = min(
            edge_xs[i + 1] - edge_xs[i]
            for i in range(len(edge_xs) - 1)
        )

        # The widest label
        max_label_w = max(
            len(rel.label) * _LABEL_CHAR_W + _LABEL_PAD * 2
            for rel in diagram.relationships
            if rel.label
        )

        assert min_gap >= max_label_w, (
            f"Gap between adjacent edges ({min_gap:.0f}) is less than "
            f"widest label ({max_label_w:.0f})"
        )

    def test_labels_within_viewbox(self):
        """All label rects must be fully within the SVG viewBox."""
        svg = render_diagram(ALL_CARDINALITIES)
        root = ET.fromstring(svg)
        vb = root.get("viewBox", "").split()
        vb_x, vb_y = float(vb[0]), float(vb[1])
        vb_w, vb_h = float(vb[2]), float(vb[3])

        rects = _get_label_rects(svg)
        for i, (rx, ry, rw, rh) in enumerate(rects):
            assert rx >= vb_x, (
                f"Label rect {i} left edge ({rx}) outside viewBox left ({vb_x})"
            )
            vb_right = vb_x + vb_w
            assert rx + rw <= vb_right, (
                f"Label rect {i} right edge ({rx + rw}) "
                f"outside viewBox right ({vb_right})"
            )
            assert ry >= vb_y, (
                f"Label rect {i} top ({ry}) outside viewBox ({vb_y})"
            )
            vb_bottom = vb_y + vb_h
            assert ry + rh <= vb_bottom, (
                f"Label rect {i} bottom edge ({ry + rh}) "
                f"outside viewBox bottom ({vb_bottom})"
            )


class TestERLabelFixtureFile:
    """Test with the actual fixture file."""

    def test_fixture_renders_without_error(self):
        """The all_cardinalities.mmd fixture must render successfully."""
        with open("tests/fixtures/corpus/er/all_cardinalities.mmd") as f:
            source = f.read()
        svg = render_diagram(source)
        assert "<svg" in svg
        assert "er-relationship" in svg

    def test_fixture_labels_no_overlap(self):
        """Labels in the fixture file must not overlap."""
        with open("tests/fixtures/corpus/er/all_cardinalities.mmd") as f:
            source = f.read()
        svg = render_diagram(source)
        rects = _get_label_rects(svg)
        for i in range(len(rects)):
            for j in range(i + 1, len(rects)):
                assert not _rects_overlap(rects[i], rects[j]), (
                    f"Label rects {i} and {j} overlap: {rects[i]} vs {rects[j]}"
                )
