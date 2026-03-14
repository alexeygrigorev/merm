"""Edge case rendering tests: complex diagrams render to valid SVG and PNG.

Tests 15 complex fixture files covering flowcharts, subgraphs, shapes,
styling, edges, scale, sequence, class, state, and real-world GitHub diagrams.
Also includes regression tests for three bugs found during this process:

Bug 1: Edge labels were painted under nodes due to Z-order (edge labels
       rendered as part of edge groups, but nodes rendered after edges).
Bug 2: Multiline edge labels rendered at SVG origin (0,0) instead of at the
       label center because the parent <text> element lacked x/y attributes.
Bug 3: ViewBox did not account for edge label overflow, causing labels that
       extend beyond node boundaries to be clipped.
"""

import struct
import xml.etree.ElementTree as ET
from pathlib import Path

import cairosvg
import pytest

from merm import render_diagram

FIXTURES_DIR = Path(__file__).parent / "fixtures"
OUTPUT_DIR = Path(__file__).parent.parent / ".tmp" / "edge_cases"

# All 15 fixture files to test
EDGE_CASE_FIXTURES = [
    FIXTURES_DIR / "corpus" / "flowchart" / "ci_pipeline.mmd",
    FIXTURES_DIR / "corpus" / "flowchart" / "elt_bigquery.mmd",
    FIXTURES_DIR / "corpus" / "flowchart" / "registration.mmd",
    FIXTURES_DIR / "corpus" / "subgraphs" / "nested_subgraphs.mmd",
    FIXTURES_DIR / "corpus" / "subgraphs" / "cross_boundary_edges.mmd",
    FIXTURES_DIR / "corpus" / "shapes" / "mixed_shapes.mmd",
    FIXTURES_DIR / "corpus" / "styling" / "mixed_styled_unstyled.mmd",
    FIXTURES_DIR / "corpus" / "edges" / "labeled_edges.mmd",
    FIXTURES_DIR / "corpus" / "edges" / "circle_endpoint.mmd",
    FIXTURES_DIR / "corpus" / "scale" / "large.mmd",
    FIXTURES_DIR / "corpus" / "sequence" / "complex.mmd",
    FIXTURES_DIR / "corpus" / "class" / "complex.mmd",
    FIXTURES_DIR / "corpus" / "state" / "complex.mmd",
    FIXTURES_DIR / "github" / "flink_late_upsert.mmd",
    FIXTURES_DIR / "github" / "ci_pipeline.mmd",
]

FIXTURE_IDS = [
    str(f.relative_to(FIXTURES_DIR)) for f in EDGE_CASE_FIXTURES
]


def _get_png_dims(data: bytes) -> tuple[int, int]:
    """Extract width and height from a PNG file's IHDR chunk."""
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return (0, 0)
    w, h = struct.unpack(">II", data[16:24])
    return w, h


# -------------------------------------------------------------------------
# Parametrized: Render-and-verify for all 15 fixtures
# -------------------------------------------------------------------------


@pytest.mark.parametrize("mmd_file", EDGE_CASE_FIXTURES, ids=FIXTURE_IDS)
def test_renders_to_valid_svg(mmd_file: Path) -> None:
    """render_diagram() produces well-formed SVG for each fixture."""
    source = mmd_file.read_text()
    svg = render_diagram(source)

    assert isinstance(svg, str)
    assert len(svg) > 0
    assert "<svg" in svg
    assert "</svg>" in svg

    # Must be parseable as XML with an <svg> root
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg"), f"Expected <svg> root, got <{root.tag}>"


@pytest.mark.parametrize("mmd_file", EDGE_CASE_FIXTURES, ids=FIXTURE_IDS)
def test_renders_to_valid_png(mmd_file: Path) -> None:
    """SVG converts to a non-degenerate PNG (>50x50 pixels)."""
    source = mmd_file.read_text()
    svg = render_diagram(source)
    png_data = cairosvg.svg2png(bytestring=svg.encode())

    assert len(png_data) > 0, "PNG is empty"

    w, h = _get_png_dims(png_data)
    assert w > 50, f"PNG width {w} is too small (< 50px)"
    assert h > 50, f"PNG height {h} is too small (< 50px)"

    # Save to output directory for visual inspection
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    name = mmd_file.stem
    category = mmd_file.parent.name
    out_path = OUTPUT_DIR / f"{category}_{name}.png"
    out_path.write_bytes(png_data)


# -------------------------------------------------------------------------
# Regression test: Bug 1 - Edge labels Z-order (rendered on top of nodes)
# -------------------------------------------------------------------------


class TestBug1EdgeLabelZOrder:
    """Edge labels must be rendered on top of nodes, not behind them.

    Previously, edge labels were part of edge <g> elements which were
    rendered before nodes. When an edge label overlapped a node (common
    in LR layouts with short edges), the node's filled background would
    paint over the label text, making it partially or fully invisible.
    """

    def test_lr_edge_labels_visible_over_nodes(self) -> None:
        """In an LR layout, edge labels between adjacent nodes must be
        fully visible and rendered after (on top of) the node backgrounds."""
        source = "flowchart LR\n    A -->|label1| B -->|label2| C"
        svg = render_diagram(source)
        root = ET.fromstring(svg)

        # Edge labels should be in edge-label groups rendered after nodes
        ns = "http://www.w3.org/2000/svg"
        groups = list(root.iter(f"{{{ns}}}g"))
        class_order = [g.get("class") for g in groups if g.get("class")]

        # Verify edge-label groups come after node groups in the SVG tree
        last_node_idx = -1
        first_label_idx = len(class_order)
        for i, cls in enumerate(class_order):
            if cls == "node":
                last_node_idx = i
            if cls == "edge-label" and i < first_label_idx:
                first_label_idx = i

        assert first_label_idx > last_node_idx, (
            "Edge labels must be rendered after nodes for correct Z-order"
        )

    def test_approved_label_not_clipped_by_nodes(self) -> None:
        """The 'Approved' label in the CI pipeline should be fully visible."""
        source = Path(
            FIXTURES_DIR / "corpus" / "flowchart" / "ci_pipeline.mmd"
        ).read_text()
        svg = render_diagram(source)

        # The label 'Approved' should be in an edge-label group
        assert "Approved" in svg, "Label 'Approved' missing from SVG"

        # The edge-label group should be separate from the edge path group
        root = ET.fromstring(svg)
        ns = "http://www.w3.org/2000/svg"
        label_groups = [
            g for g in root.iter(f"{{{ns}}}g")
            if g.get("class") == "edge-label"
        ]
        found = False
        for g in label_groups:
            all_text = "".join(el.text or "" for el in g.iter())
            if "Approved" in all_text:
                found = True
                break
        assert found, "'Approved' not found in any edge-label group"


# -------------------------------------------------------------------------
# Regression test: Bug 2 - Multiline edge labels positioned at origin
# -------------------------------------------------------------------------


class TestBug2MultilineEdgeLabelPosition:
    """Multiline edge labels must be positioned at the edge midpoint.

    Previously, the parent <text> element for multiline edge labels
    lacked x/y attributes, causing tspan dy offsets to be relative to
    (0,0) instead of the label center. This placed multiline labels
    at the top-left corner of the SVG, often outside the viewport.
    """

    def test_multiline_label_has_text_coordinates(self) -> None:
        """The <text> element for a multiline edge label must have x/y."""
        source = "graph TD\n    A -->|line1<br/>line2| B"
        svg = render_diagram(source)
        root = ET.fromstring(svg)

        ns = "http://www.w3.org/2000/svg"
        for g in root.iter(f"{{{ns}}}g"):
            if g.get("class") != "edge-label":
                continue
            text_el = g.find(f"{{{ns}}}text")
            if text_el is None:
                text_el = g.find("text")
            if text_el is None:
                continue

            # Text element must have explicit x and y coordinates
            assert text_el.get("x") is not None, (
                "Multiline edge label <text> missing x attribute"
            )
            assert text_el.get("y") is not None, (
                "Multiline edge label <text> missing y attribute"
            )

            # The y coordinate should be near the edge midpoint, not at 0
            y = float(text_el.get("y"))
            assert y > 10, (
                f"Multiline edge label y={y} is too close to origin"
            )

    def test_multiline_label_within_viewport(self) -> None:
        """A 3-line edge label must be within the SVG viewport."""
        source = "graph TD\n    A -->|line1<br/>line2<br/>line3| B"
        svg = render_diagram(source)
        root = ET.fromstring(svg)

        # Parse viewBox
        vb = root.get("viewBox", "").split()
        vb_y = float(vb[1])
        vb_h = float(vb[3])
        vb_bottom = vb_y + vb_h

        ns = "http://www.w3.org/2000/svg"
        for g in root.iter(f"{{{ns}}}g"):
            if g.get("class") != "edge-label":
                continue
            rect = g.find(f"{{{ns}}}rect")
            if rect is None:
                rect = g.find("rect")
            if rect is None:
                continue

            # Label rect must be within viewport
            ry = float(rect.get("y", "0"))
            rh = float(rect.get("height", "0"))
            assert ry >= vb_y, (
                f"Label rect top {ry} above viewport top {vb_y}"
            )
            assert ry + rh <= vb_bottom, (
                f"Label rect bottom {ry + rh} below viewport bottom {vb_bottom}"
            )


# -------------------------------------------------------------------------
# Regression test: Bug 3 - ViewBox does not account for edge label overflow
# -------------------------------------------------------------------------


class TestBug3ViewBoxEdgeLabelOverflow:
    """ViewBox must expand to include edge labels that extend beyond nodes.

    Previously, the viewBox was computed from layout dimensions (node and
    subgraph positions only). Edge labels that extended beyond node
    boundaries were clipped by the viewport.
    """

    def test_long_label_expands_viewbox(self) -> None:
        """A long edge label should cause the viewBox to expand."""
        source = (
            "graph TD\n"
            "    A -->|this is a long label extending beyond| B"
        )
        svg = render_diagram(source)
        root = ET.fromstring(svg)

        # Parse viewBox
        vb = root.get("viewBox", "").split()
        vb_x = float(vb[0])
        vb_w = float(vb[2])

        # The viewBox should be wider than just the node width (~70px)
        # to accommodate the long label
        assert vb_w > 100, (
            f"ViewBox width {vb_w} too narrow for long edge label"
        )

        # The viewBox should extend left of x=0 if the label extends left
        ns = "http://www.w3.org/2000/svg"
        for g in root.iter(f"{{{ns}}}g"):
            if g.get("class") != "edge-label":
                continue
            rect = g.find(f"{{{ns}}}rect")
            if rect is None:
                rect = g.find("rect")
            if rect is None:
                continue

            rx = float(rect.get("x", "0"))
            rw = float(rect.get("width", "0"))
            # Label rect must be within the viewBox
            assert rx >= vb_x, (
                f"Label rect left {rx} outside viewBox left {vb_x}"
            )
            assert rx + rw <= vb_x + vb_w, (
                f"Label rect right {rx + rw} outside viewBox right {vb_x + vb_w}"
            )

    def test_viewbox_covers_all_labels(self) -> None:
        """All edge labels in a multi-label diagram must be within viewBox."""
        source = (
            "graph TD\n"
            "    A -->|yes| B\n"
            "    A -->|no| C\n"
            "    B -->|maybe| D\n"
        )
        svg = render_diagram(source)
        root = ET.fromstring(svg)

        vb = root.get("viewBox", "").split()
        vb_x = float(vb[0])
        vb_y = float(vb[1])
        vb_w = float(vb[2])
        vb_h = float(vb[3])

        ns = "http://www.w3.org/2000/svg"
        for g in root.iter(f"{{{ns}}}g"):
            if g.get("class") != "edge-label":
                continue
            rect = g.find(f"{{{ns}}}rect")
            if rect is None:
                rect = g.find("rect")
            if rect is None:
                continue

            rx = float(rect.get("x", "0"))
            ry = float(rect.get("y", "0"))
            rw = float(rect.get("width", "0"))
            rh = float(rect.get("height", "0"))
            assert rx >= vb_x, f"Label left {rx} < viewBox left {vb_x}"
            assert ry >= vb_y, f"Label top {ry} < viewBox top {vb_y}"
            assert rx + rw <= vb_x + vb_w, (
                f"Label right {rx + rw} > viewBox right {vb_x + vb_w}"
            )
            assert ry + rh <= vb_y + vb_h, (
                f"Label bottom {ry + rh} > viewBox bottom {vb_y + vb_h}"
            )
