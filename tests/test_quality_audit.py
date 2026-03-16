"""Test quality audit: structural correctness tests for rendering.

This file adds tests that verify actual visual correctness properties
rather than implementation details. Each test here tests a property that,
if violated, would cause a visible rendering bug.

Categories:
1. Marker geometry consistency (refX/refY must match polygon geometry)
2. Marker minimum dimensions (>= 6x6 for visibility)
3. Edge paths reach node boundaries (within marker length)
4. Font sizes are consistent across diagram types
5. SVG viewBox dimensions are reasonable for all diagram types
6. No degenerate SVG output (zero-width, zero-height, empty)
"""

import xml.etree.ElementTree as ET

import pytest

from merm import render_diagram
from merm.render.edges import _MARKER_SHORTEN, make_edge_defs
from merm.theme import DEFAULT_THEME

_SVG_NS = "http://www.w3.org/2000/svg"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_svg(source: str) -> ET.Element:
    """Render a diagram source and return the parsed SVG root."""
    svg_str = render_diagram(source)
    return ET.fromstring(svg_str)


def _get_viewbox(root: ET.Element) -> tuple[float, float, float, float]:
    """Parse viewBox attribute into (x, y, width, height)."""
    vb = root.get("viewBox", "0 0 0 0")
    parts = vb.split()
    return float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3])


def _find_css_font_sizes(root: ET.Element) -> dict[str, float]:
    """Extract font-size values from the SVG <style> element CSS rules.

    Returns a dict mapping CSS selector (e.g. ".node text") to font-size in px.
    """
    import re
    sizes: dict[str, float] = {}
    for style_el in root.iter(f"{{{_SVG_NS}}}style"):
        css = style_el.text or ""
        # Match rules like ".node text { ... font-size: 16px; ... }"
        for m in re.finditer(
            r"([^{}]+)\{([^}]*font-size:\s*([\d.]+)px[^}]*)\}", css,
        ):
            selector = m.group(1).strip()
            font_size = float(m.group(3))
            sizes[selector] = font_size
    return sizes


# ===========================================================================
# 1. Marker geometry: refX/refY must match polygon/path geometry
# ===========================================================================

class TestMarkerGeometryConsistency:
    """Verify that marker refX aligns with the actual shape geometry."""

    @pytest.fixture()
    def defs(self) -> ET.Element:
        defs = ET.Element("defs")
        make_edge_defs(defs)
        return defs

    def _find_marker(self, defs: ET.Element, marker_id: str) -> ET.Element:
        for m in defs.iter("marker"):
            if m.get("id") == marker_id:
                return m
        pytest.fail(f"Marker '{marker_id}' not found")

    def test_arrow_refx_zero_with_shorten_matches_marker_width(self, defs):
        """Arrow marker: refX=0 + _MARKER_SHORTEN must equal markerWidth.

        This ensures the arrowhead tip touches the node boundary:
        - Path is shortened by _MARKER_SHORTEN pixels
        - refX=0 places triangle base at shortened path end
        - Triangle extends forward by viewBox width (10px scaled to markerWidth)
        - So tip reaches: path_end + markerWidth = node_boundary
        """
        m = self._find_marker(defs, "arrow")
        ref_x = float(m.get("refX", "-1"))
        marker_w = float(m.get("markerWidth", "0"))
        assert ref_x == 0.0, f"Arrow refX must be 0, got {ref_x}"
        assert _MARKER_SHORTEN == marker_w, (
            f"_MARKER_SHORTEN ({_MARKER_SHORTEN}) must equal "
            f"markerWidth ({marker_w}) for clean arrowhead alignment"
        )

    def test_arrow_refY_is_vertically_centered(self, defs):
        """Arrow marker refY must be half the viewBox height."""
        m = self._find_marker(defs, "arrow")
        vb = m.get("viewBox", "0 0 10 10")
        vb_h = float(vb.split()[3])
        ref_y = float(m.get("refY", "0"))
        assert ref_y == vb_h / 2, (
            f"Arrow refY={ref_y} should be viewBox_h/2={vb_h / 2}"
        )

    def test_arrow_path_is_closed_triangle(self, defs):
        """Arrow marker must contain a closed triangular path (ends with z)."""
        m = self._find_marker(defs, "arrow")
        path = m.find("path")
        assert path is not None, "Arrow marker must contain a <path>"
        d = path.get("d", "")
        assert d.lower().endswith("z"), f"Arrow path must be closed, got: {d}"

    def test_circle_end_refx_centers_circle(self, defs):
        """circle-end refX must equal the circle cx (centered on endpoint)."""
        m = self._find_marker(defs, "circle-end")
        ref_x = float(m.get("refX", "0"))
        circle = m.find("circle")
        assert circle is not None
        cx = float(circle.get("cx", "0"))
        assert ref_x == cx, (
            f"circle-end refX={ref_x} should equal circle cx={cx}"
        )

    def test_cross_end_refx_centers_cross(self, defs):
        """cross-end refX must be at the center of the viewBox."""
        m = self._find_marker(defs, "cross-end")
        ref_x = float(m.get("refX", "0"))
        vb = m.get("viewBox", "0 0 11 11")
        vb_w = float(vb.split()[2])
        assert ref_x == vb_w / 2, (
            f"cross-end refX={ref_x} should be viewBox_w/2={vb_w / 2}"
        )

    def test_all_markers_have_orient(self, defs):
        """Every marker must have an orient attribute for correct rotation."""
        for m in defs.iter("marker"):
            mid = m.get("id", "")
            orient = m.get("orient")
            assert orient is not None, f"Marker '{mid}' missing orient attribute"
            assert orient in ("auto", "auto-start-reverse"), (
                f"Marker '{mid}' has unexpected orient='{orient}'"
            )


# ===========================================================================
# 2. Marker minimum dimensions (visibility)
# ===========================================================================

class TestMarkerMinimumDimensions:
    """All markers must be at least 6x6 to be visible at normal zoom."""

    @pytest.fixture()
    def defs(self) -> ET.Element:
        defs = ET.Element("defs")
        make_edge_defs(defs)
        return defs

    @pytest.mark.parametrize("marker_id", [
        "arrow", "arrow-reverse", "circle-end", "cross-end",
    ])
    def test_marker_at_least_6x6(self, defs, marker_id):
        for m in defs.iter("marker"):
            if m.get("id") == marker_id:
                w = float(m.get("markerWidth", "0"))
                h = float(m.get("markerHeight", "0"))
                assert w >= 6, f"{marker_id} markerWidth={w} < 6"
                assert h >= 6, f"{marker_id} markerHeight={h} < 6"
                return
        pytest.fail(f"Marker '{marker_id}' not found")

    @pytest.mark.parametrize("marker_id", [
        "arrow", "arrow-reverse", "circle-end", "cross-end",
    ])
    def test_marker_not_oversized(self, defs, marker_id):
        """Markers should not exceed 12x12 (would look cartoonishly large)."""
        for m in defs.iter("marker"):
            if m.get("id") == marker_id:
                w = float(m.get("markerWidth", "0"))
                h = float(m.get("markerHeight", "0"))
                assert w <= 12, f"{marker_id} markerWidth={w} > 12"
                assert h <= 12, f"{marker_id} markerHeight={h} > 12"
                return
        pytest.fail(f"Marker '{marker_id}' not found")

    @pytest.mark.parametrize("marker_id", [
        "arrow", "arrow-reverse", "circle-end", "cross-end",
    ])
    def test_marker_uses_user_space_on_use(self, defs, marker_id):
        """userSpaceOnUse prevents markers from scaling with stroke-width."""
        for m in defs.iter("marker"):
            if m.get("id") == marker_id:
                assert m.get("markerUnits") == "userSpaceOnUse", (
                    f"{marker_id} must use userSpaceOnUse"
                )
                return
        pytest.fail(f"Marker '{marker_id}' not found")


# ===========================================================================
# 3. Font size consistency across diagram types
# ===========================================================================

class TestFontSizeConsistency:
    """Font sizes must be reasonable and consistent across diagram types."""

    def test_flowchart_node_font_size_matches_theme(self):
        """Flowchart node text should use the theme node_font_size (16px)."""
        root = _parse_svg("graph TD\n    A[Hello] --> B[World]")
        css_sizes = _find_css_font_sizes(root)
        expected_node_fs = float(DEFAULT_THEME.node_font_size.replace("px", ""))
        # Find the .node text rule
        node_selector = None
        for sel in css_sizes:
            if "node" in sel and "text" in sel:
                node_selector = sel
                break
        assert node_selector is not None, (
            f"No CSS rule for .node text found. CSS rules: {list(css_sizes.keys())}"
        )
        assert css_sizes[node_selector] == expected_node_fs, (
            f"Node text font-size is {css_sizes[node_selector]}px, "
            f"expected {expected_node_fs}px from theme"
        )

    def test_edge_label_font_size_smaller_than_node(self):
        """Edge labels should use a smaller font than node labels."""
        root = _parse_svg("graph TD\n    A -->|label| B")
        css_sizes = _find_css_font_sizes(root)
        node_fs = None
        edge_fs = None
        for sel, fs in css_sizes.items():
            if "node" in sel and "text" in sel:
                node_fs = fs
            if "edge" in sel and "text" in sel:
                edge_fs = fs
        if node_fs is not None and edge_fs is not None:
            assert edge_fs < node_fs, (
                f"Edge label font ({edge_fs}px) should be smaller than "
                f"node font ({node_fs}px)"
            )

    def test_all_css_font_sizes_are_positive(self):
        """No CSS font-size rule should have a zero or negative value."""
        for source in [
            "graph TD\n    A --> B",
            "sequenceDiagram\n    Alice->>Bob: Hello",
            "stateDiagram-v2\n    [*] --> Still",
        ]:
            root = _parse_svg(source)
            css_sizes = _find_css_font_sizes(root)
            for sel, fs in css_sizes.items():
                assert fs > 0, f"Font size {fs} <= 0 in CSS rule '{sel}'"


# ===========================================================================
# 4. SVG viewBox dimensions are reasonable
# ===========================================================================

class TestViewBoxReasonable:
    """SVG viewBox must have positive, non-degenerate dimensions."""

    @pytest.mark.parametrize("source,desc", [
        ("graph TD\n    A --> B", "simple flowchart"),
        ("graph LR\n    A --> B --> C", "LR flowchart"),
        ("sequenceDiagram\n    Alice->>Bob: Hello", "sequence"),
        ("stateDiagram-v2\n    [*] --> Still\n    Still --> Moving", "state"),
        ("erDiagram\n    A ||--o{ B : has", "ER"),
        ("pie\n    \"A\" : 30\n    \"B\" : 70", "pie"),
    ])
    def test_viewbox_positive_dimensions(self, source, desc):
        """ViewBox width and height must be > 0 for {desc}."""
        root = _parse_svg(source)
        _, _, w, h = _get_viewbox(root)
        assert w > 0, f"{desc}: viewBox width is {w}"
        assert h > 0, f"{desc}: viewBox height is {h}"

    @pytest.mark.parametrize("source,desc,max_w,max_h", [
        ("graph TD\n    A --> B", "2-node flowchart", 400, 400),
        ("graph LR\n    A --> B --> C", "3-node LR", 600, 300),
        ("sequenceDiagram\n    Alice->>Bob: Hello", "simple sequence", 600, 400),
    ])
    def test_viewbox_not_excessively_large(self, source, desc, max_w, max_h):
        """Small diagrams should not produce oversized viewBoxes."""
        root = _parse_svg(source)
        _, _, w, h = _get_viewbox(root)
        assert w < max_w, f"{desc}: viewBox width {w} > {max_w}"
        assert h < max_h, f"{desc}: viewBox height {h} > {max_h}"

    def test_viewbox_matches_width_height_attributes(self):
        """SVG width/height attributes should match viewBox dimensions."""
        root = _parse_svg("graph TD\n    A --> B")
        _, _, vb_w, vb_h = _get_viewbox(root)
        svg_w = float(root.get("width", "0"))
        svg_h = float(root.get("height", "0"))
        if svg_w > 0 and svg_h > 0:
            assert abs(vb_w - svg_w) < 1.0, (
                f"viewBox width {vb_w} != SVG width {svg_w}"
            )
            assert abs(vb_h - svg_h) < 1.0, (
                f"viewBox height {vb_h} != SVG height {svg_h}"
            )


# ===========================================================================
# 5. No degenerate SVG output
# ===========================================================================

class TestNoDegenerateSVG:
    """Rendered SVG must not be empty or degenerate."""

    @pytest.mark.parametrize("source", [
        "graph TD\n    A --> B",
        "graph LR\n    A --> B --> C",
        "sequenceDiagram\n    Alice->>Bob: Hello",
        "stateDiagram-v2\n    [*] --> Still",
        "classDiagram\n    Animal <|-- Duck",
        "erDiagram\n    A ||--o{ B : has",
        "pie\n    \"A\" : 30\n    \"B\" : 70",
        "gantt\n    title Test\n    section S\n    Task : a1, 2024-01-01, 7d",
    ])
    def test_renders_non_empty_svg(self, source):
        """Every diagram type must produce non-empty, parseable SVG."""
        svg_str = render_diagram(source)
        assert len(svg_str) > 100, "SVG output too short"
        root = ET.fromstring(svg_str)
        assert root.tag.endswith("svg"), f"Root tag is {root.tag}, not svg"

    @pytest.mark.parametrize("source", [
        "graph TD\n    A --> B",
        "sequenceDiagram\n    Alice->>Bob: Hello",
        "stateDiagram-v2\n    [*] --> Still\n    Still --> Moving",
    ])
    def test_contains_visible_elements(self, source):
        """SVG must contain visible shapes (rect, circle, path, or line)."""
        svg_str = render_diagram(source)
        root = ET.fromstring(svg_str)
        visible_tags = {"rect", "circle", "path", "line", "polygon", "polyline"}
        found = set()
        for el in root.iter():
            local_tag = el.tag.split("}")[-1] if "}" in el.tag else el.tag
            if local_tag in visible_tags:
                found.add(local_tag)
        assert len(found) > 0, (
            f"SVG contains no visible shape elements. "
            f"Expected at least one of: {visible_tags}"
        )


# ===========================================================================
# 6. Edge path endpoints proximity to nodes
# ===========================================================================

class TestEdgePathEndpointsReachNodes:
    """Edge paths must actually connect to nodes, not float in space."""

    def _get_node_rects(self, root: ET.Element) -> dict[str, dict]:
        """Find node bounding boxes by data-node-id."""
        nodes = {}
        for g in root.iter(f"{{{_SVG_NS}}}g"):
            if g.get("class") == "node":
                nid = g.get("data-node-id", "")
                if not nid:
                    continue
                rect = g.find(f"{{{_SVG_NS}}}rect")
                if rect is not None:
                    rx = float(rect.get("x", "0"))
                    ry = float(rect.get("y", "0"))
                    rw = float(rect.get("width", "0"))
                    rh = float(rect.get("height", "0"))
                    nodes[nid] = {
                        "cx": rx + rw / 2,
                        "cy": ry + rh / 2,
                        "hw": rw / 2,
                        "hh": rh / 2,
                    }
        return nodes

    def _get_edge_endpoints(self, root: ET.Element) -> list[dict]:
        """Extract edge source/target and path start/end coordinates."""
        import re
        edges = []
        for g in root.iter(f"{{{_SVG_NS}}}g"):
            if g.get("class") != "edge":
                continue
            src = g.get("data-edge-source", "")
            tgt = g.get("data-edge-target", "")
            path = g.find(f"{{{_SVG_NS}}}path")
            if path is None or not src or not tgt:
                continue
            d = path.get("d", "")
            coords = re.findall(r"([-\d.]+),([-\d.]+)", d)
            if len(coords) >= 2:
                edges.append({
                    "source": src,
                    "target": tgt,
                    "start": (float(coords[0][0]), float(coords[0][1])),
                    "end": (float(coords[-1][0]), float(coords[-1][1])),
                    "marker_end": path.get("marker-end", ""),
                })
        return edges

    def test_td_edge_source_near_node(self):
        """In TD layout, edge start point should be near source node."""
        root = _parse_svg("graph TD\n    A[Start] --> B[End]")
        nodes = self._get_node_rects(root)
        edges = self._get_edge_endpoints(root)

        for edge in edges:
            src = nodes.get(edge["source"])
            if src is None:
                continue
            sx, sy = edge["start"]
            # Source endpoint should be within node_hw + 2px horizontally
            # and within node_hh + 2px vertically of node center
            dx = abs(sx - src["cx"])
            dy = abs(sy - src["cy"])
            assert dx <= src["hw"] + 2, (
                f"Edge start x={sx} too far from source center x={src['cx']} "
                f"(half-width={src['hw']})"
            )
            assert dy <= src["hh"] + 2, (
                f"Edge start y={sy} too far from source center y={src['cy']} "
                f"(half-height={src['hh']})"
            )

    def test_td_edge_target_near_node(self):
        """In TD layout, edge end point should be near target node.

        For arrow edges, the path is shortened by _MARKER_SHORTEN, so the
        end point can be up to _MARKER_SHORTEN pixels away from the boundary.
        """
        root = _parse_svg("graph TD\n    A[Start] --> B[End]")
        nodes = self._get_node_rects(root)
        edges = self._get_edge_endpoints(root)

        for edge in edges:
            tgt = nodes.get(edge["target"])
            if tgt is None:
                continue
            ex, ey = edge["end"]
            dx = abs(ex - tgt["cx"])
            dy = abs(ey - tgt["cy"])
            max_dist = max(tgt["hw"], tgt["hh"]) + _MARKER_SHORTEN + 2
            assert dx <= max_dist and dy <= max_dist, (
                f"Edge end ({ex},{ey}) too far from target center "
                f"({tgt['cx']},{tgt['cy']}) "
                f"half-size=({tgt['hw']},{tgt['hh']})"
            )


# ===========================================================================
# 7. Theme values are sane
# ===========================================================================

class TestThemeValuesSanity:
    """Theme constants must produce reasonable visual output."""

    def test_node_font_size_readable(self):
        """Node font size must be between 10px and 24px for readability."""
        fs = float(DEFAULT_THEME.node_font_size.replace("px", ""))
        assert 10 <= fs <= 24, f"Node font size {fs}px outside readable range"

    def test_edge_label_font_size_readable(self):
        """Edge label font size must be between 8px and 18px."""
        fs = float(DEFAULT_THEME.edge_label_font_size.replace("px", ""))
        assert 8 <= fs <= 18, f"Edge label font size {fs}px outside readable range"

    def test_edge_label_smaller_than_node(self):
        """Edge label font must be smaller than node font."""
        node_fs = float(DEFAULT_THEME.node_font_size.replace("px", ""))
        edge_fs = float(DEFAULT_THEME.edge_label_font_size.replace("px", ""))
        assert edge_fs < node_fs, (
            f"Edge label font {edge_fs}px should be smaller than "
            f"node font {node_fs}px"
        )

    def test_node_min_dimensions_positive(self):
        """Node minimum dimensions must be positive."""
        assert DEFAULT_THEME.node_min_height > 0
        assert DEFAULT_THEME.node_min_width > 0

    def test_spacing_values_positive(self):
        """Layout spacing values must be positive."""
        assert DEFAULT_THEME.rank_sep > 0
        assert DEFAULT_THEME.node_sep > 0

    def test_marker_shorten_matches_theme(self):
        """_MARKER_SHORTEN should be consistent with marker definitions."""
        defs = ET.Element("defs")
        make_edge_defs(defs)
        for m in defs.iter("marker"):
            if m.get("id") == "arrow":
                mw = float(m.get("markerWidth", "0"))
                assert _MARKER_SHORTEN == mw, (
                    f"_MARKER_SHORTEN ({_MARKER_SHORTEN}) != "
                    f"arrow markerWidth ({mw})"
                )
                return
        pytest.fail("Arrow marker not found")
