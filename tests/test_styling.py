"""Tests for styling support and shape integration in the SVG renderer."""

import xml.etree.ElementTree as ET

from merm.ir import (
    Diagram,
    Direction,
    Edge,
    Node,
    NodeShape,
    StyleDef,
)
from merm.layout import LayoutResult, NodeLayout
from merm.render import render_svg

_SVG_NS = "http://www.w3.org/2000/svg"

def _layout_for(*node_ids: str) -> LayoutResult:
    """Build a trivial layout with one box per node id."""
    nodes = {}
    for i, nid in enumerate(node_ids):
        nodes[nid] = NodeLayout(x=float(i * 120), y=0.0, width=100.0, height=50.0)
    return LayoutResult(nodes=nodes, edges=[], width=len(node_ids) * 120.0, height=50.0)

def _parse(svg_str: str) -> ET.Element:
    return ET.fromstring(svg_str)

def _find_node_g(root: ET.Element, node_id: str) -> ET.Element:
    """Find the <g> element for a given node id."""
    for g in root.iter():
        if g.get("data-node-id") == node_id:
            return g
    raise AssertionError(f"No <g data-node-id='{node_id}'> found")

def _child_tags(g: ET.Element) -> list[str]:
    """Return the local tag names of direct children of g."""
    tags = []
    for child in g:
        tag = child.tag
        if tag.startswith("{"):
            tag = tag.split("}", 1)[1]
        tags.append(tag)
    return tags

# ===================================================================
# Part A: Shape integration
# ===================================================================

class TestShapeIntegrationDiamond:
    def test_diamond_produces_polygon(self):
        d = Diagram(
            nodes=(Node(id="A", label="Decision", shape=NodeShape.diamond),),
        )
        lr = _layout_for("A")
        root = _parse(render_svg(d, lr))
        g = _find_node_g(root, "A")
        tags = _child_tags(g)
        assert "polygon" in tags
        assert "rect" not in tags

    def test_diamond_no_rect_inside_node(self):
        d = Diagram(
            nodes=(Node(id="A", label="D", shape=NodeShape.diamond),),
        )
        lr = _layout_for("A")
        svg = render_svg(d, lr)
        root = _parse(svg)
        g = _find_node_g(root, "A")
        rects = [c for c in g if c.tag in ("rect", f"{{{_SVG_NS}}}rect")]
        assert len(rects) == 0

class TestShapeIntegrationCircle:
    def test_circle_produces_circle_element(self):
        d = Diagram(
            nodes=(Node(id="C", label="Circ", shape=NodeShape.circle),),
        )
        lr = _layout_for("C")
        root = _parse(render_svg(d, lr))
        g = _find_node_g(root, "C")
        tags = _child_tags(g)
        assert "circle" in tags

class TestShapeIntegrationStadium:
    def test_stadium_rect_has_rx(self):
        d = Diagram(
            nodes=(Node(id="S", label="Pill", shape=NodeShape.stadium),),
        )
        lr = _layout_for("S")
        root = _parse(render_svg(d, lr))
        g = _find_node_g(root, "S")
        rects = [c for c in g if c.tag in ("rect", f"{{{_SVG_NS}}}rect")]
        assert len(rects) == 1
        rx = rects[0].get("rx")
        assert rx is not None
        # rx should equal half the height (50/2 = 25)
        assert float(rx) == 25.0

class TestShapeIntegrationCylinder:
    def test_cylinder_produces_path(self):
        d = Diagram(
            nodes=(Node(id="CY", label="DB", shape=NodeShape.cylinder),),
        )
        lr = _layout_for("CY")
        root = _parse(render_svg(d, lr))
        g = _find_node_g(root, "CY")
        tags = _child_tags(g)
        assert "path" in tags

class TestShapeIntegrationSubroutine:
    def test_subroutine_has_line_elements(self):
        d = Diagram(
            nodes=(Node(id="SR", label="Sub", shape=NodeShape.subroutine),),
        )
        lr = _layout_for("SR")
        root = _parse(render_svg(d, lr))
        g = _find_node_g(root, "SR")
        tags = _child_tags(g)
        assert tags.count("line") == 2

class TestShapeIntegrationDoubleCircle:
    def test_double_circle_two_circles(self):
        d = Diagram(
            nodes=(Node(id="DC", label="End", shape=NodeShape.double_circle),),
        )
        lr = _layout_for("DC")
        root = _parse(render_svg(d, lr))
        g = _find_node_g(root, "DC")
        circles = [c for c in g if c.tag in ("circle", f"{{{_SVG_NS}}}circle")]
        assert len(circles) == 2

class TestShapeIntegrationMixed:
    def test_mixed_shapes(self):
        d = Diagram(
            nodes=(
                Node(id="R", label="Rect", shape=NodeShape.rect),
                Node(id="D", label="Diamond", shape=NodeShape.diamond),
                Node(id="C", label="Circle", shape=NodeShape.circle),
            ),
        )
        lr = _layout_for("R", "D", "C")
        root = _parse(render_svg(d, lr))

        r_tags = _child_tags(_find_node_g(root, "R"))
        d_tags = _child_tags(_find_node_g(root, "D"))
        c_tags = _child_tags(_find_node_g(root, "C"))

        assert "rect" in r_tags
        assert "polygon" in d_tags
        assert "circle" in c_tags

# ===================================================================
# Default style block covers multiple shape selectors
# ===================================================================

class TestDefaultStyleBlock:
    def test_style_covers_polygon_circle_path(self):
        d = Diagram(nodes=(Node(id="A", label="A"),))
        lr = _layout_for("A")
        svg = render_svg(d, lr)
        assert ".node rect" in svg or ".node rect," in svg
        assert ".node polygon" in svg
        assert ".node circle" in svg
        assert ".node &gt; path" in svg or ".node > path" in svg

# ===================================================================
# Part B: Inline style application
# ===================================================================

class TestInlineStyle:
    def test_style_applied_to_shape_element(self):
        d = Diagram(
            nodes=(Node(id="A", label="A"),),
            styles=(StyleDef("A", {"fill": "#f9f", "stroke": "#333"}),),
        )
        lr = _layout_for("A")
        root = _parse(render_svg(d, lr))
        g = _find_node_g(root, "A")
        # The shape element (rect for default) should have a style attribute
        shape_el = [c for c in g if c.tag in ("rect", f"{{{_SVG_NS}}}rect")][0]
        style_attr = shape_el.get("style", "")
        assert "fill:#f9f" in style_attr
        assert "stroke:#333" in style_attr

    def test_style_only_on_target_node(self):
        d = Diagram(
            nodes=(
                Node(id="A", label="A"),
                Node(id="B", label="B"),
            ),
            styles=(StyleDef("A", {"fill": "#f00"}),),
        )
        lr = _layout_for("A", "B")
        root = _parse(render_svg(d, lr))
        g_b = _find_node_g(root, "B")
        # B's rect should NOT have an inline style
        rect_b = [c for c in g_b if c.tag in ("rect", f"{{{_SVG_NS}}}rect")][0]
        assert rect_b.get("style") is None

# ===================================================================
# Part B: classDef application
# ===================================================================

class TestClassDef:
    def test_classdef_in_style_block(self):
        d = Diagram(
            nodes=(Node(id="A", label="A", css_classes=("highlight",)),),
            classes={"highlight": {"fill": "#ff0", "stroke": "#000"}},
        )
        lr = _layout_for("A")
        svg = render_svg(d, lr)
        assert ".highlight" in svg
        assert "fill:#ff0" in svg
        assert "stroke:#000" in svg

    def test_classdef_node_has_class_attribute(self):
        d = Diagram(
            nodes=(Node(id="A", label="A", css_classes=("highlight",)),),
            classes={"highlight": {"fill": "#ff0"}},
        )
        lr = _layout_for("A")
        root = _parse(render_svg(d, lr))
        g = _find_node_g(root, "A")
        cls = g.get("class", "")
        assert "node" in cls
        assert "highlight" in cls

    def test_classdef_default_applied(self):
        d = Diagram(
            nodes=(Node(id="A", label="A"),),
            classes={"default": {"fill": "#aaa"}},
        )
        lr = _layout_for("A")
        svg = render_svg(d, lr)
        # The default class targets shape elements, not the group.
        assert ".node rect" in svg
        assert "fill:#aaa" in svg

# ===================================================================
# Part B: Multiple classes
# ===================================================================

class TestMultipleClasses:
    def test_multiple_classes_on_node(self):
        d = Diagram(
            nodes=(Node(id="A", label="A", css_classes=("foo", "bar")),),
        )
        lr = _layout_for("A")
        root = _parse(render_svg(d, lr))
        g = _find_node_g(root, "A")
        cls = g.get("class", "")
        assert cls == "node foo bar"

# ===================================================================
# Integration: round-trip parse-to-SVG (if parser available)
# ===================================================================

class TestIntegrationRoundTrip:
    def test_diamond_and_circle_via_ir(self):
        """Build IR manually with diamond and circle, render, check SVG."""
        d = Diagram(
            direction=Direction.LR,
            nodes=(
                Node(id="A", label="Decision", shape=NodeShape.diamond),
                Node(id="B", label="Circle", shape=NodeShape.circle),
            ),
            edges=(Edge(source="A", target="B"),),
        )
        from merm.layout import layout_diagram
        from merm.measure import measure_text

        lr = layout_diagram(d, measure_text)
        svg = render_svg(d, lr)
        root = _parse(svg)

        a_tags = _child_tags(_find_node_g(root, "A"))
        b_tags = _child_tags(_find_node_g(root, "B"))
        assert "polygon" in a_tags
        assert "circle" in b_tags

    def test_inline_style_via_ir(self):
        d = Diagram(
            nodes=(
                Node(id="A", label="A"),
                Node(id="B", label="B"),
            ),
            edges=(Edge(source="A", target="B"),),
            styles=(StyleDef("A", {"fill": "#f00"}),),
        )
        from merm.layout import layout_diagram
        from merm.measure import measure_text

        lr = layout_diagram(d, measure_text)
        svg = render_svg(d, lr)
        root = _parse(svg)
        g_a = _find_node_g(root, "A")
        rects = [c for c in g_a if c.tag in ("rect", f"{{{_SVG_NS}}}rect")]
        assert len(rects) >= 1
        assert "fill:#f00" in (rects[0].get("style") or "")

    def test_classdef_via_ir(self):
        d = Diagram(
            nodes=(
                Node(id="A", label="A", css_classes=("red",)),
                Node(id="B", label="B"),
            ),
            edges=(Edge(source="A", target="B"),),
            classes={"red": {"fill": "#f00"}},
        )
        from merm.layout import layout_diagram
        from merm.measure import measure_text

        lr = layout_diagram(d, measure_text)
        svg = render_svg(d, lr)

        # Check CSS rule in style block targets shape elements
        assert ".red rect" in svg
        assert "fill:#f00" in svg

        # Check node class attribute
        root = _parse(svg)
        g_a = _find_node_g(root, "A")
        assert "red" in g_a.get("class", "")

    def test_node_without_class_has_just_node_class(self):
        d = Diagram(
            nodes=(Node(id="X", label="X"),),
        )
        lr = _layout_for("X")
        root = _parse(render_svg(d, lr))
        g = _find_node_g(root, "X")
        assert g.get("class") == "node"

    def test_inline_style_on_diamond(self):
        """Inline style applied to non-rect shape."""
        d = Diagram(
            nodes=(Node(id="D", label="D", shape=NodeShape.diamond),),
            styles=(StyleDef("D", {"fill": "#0f0", "stroke-width": "3px"}),),
        )
        lr = _layout_for("D")
        root = _parse(render_svg(d, lr))
        g = _find_node_g(root, "D")
        polygon = [c for c in g if c.tag in ("polygon", f"{{{_SVG_NS}}}polygon")][0]
        style_attr = polygon.get("style", "")
        assert "fill:#0f0" in style_attr
        assert "stroke-width:3px" in style_attr


# ===================================================================
# Part D: classDef text contrast (issue 87)
# ===================================================================

class TestClassDefTextContrast:
    """Verify that classDef color goes to fill/border, not text."""

    def test_classdef_fill_targets_shapes_not_text(self):
        """classDef fill should appear in shape-targeting CSS selectors."""
        d = Diagram(
            nodes=(Node(id="A", label="A", css_classes=("myclass",)),),
            classes={"myclass": {"fill": "#ff0", "stroke": "#000"}},
        )
        lr = _layout_for("A")
        svg = render_svg(d, lr)
        # Shape selectors should contain fill
        assert ".myclass rect" in svg
        assert "fill:#ff0" in svg
        assert "stroke:#000" in svg
        # The classDef should NOT emit a bare .myclass { fill:... }
        # that would cascade to text via SVG inheritance.
        import re
        # Ensure there's no rule like ".myclass { fill:..." (bare group selector)
        bare_rule = re.search(r"\.myclass\s*\{", svg)
        assert bare_rule is None, (
            "classDef should not target the group directly"
        )

    def test_default_text_color_preserved(self):
        """Text fill should remain #333333 when classDef has no color property."""
        d = Diagram(
            nodes=(Node(id="A", label="A"),),
            classes={"default": {"fill": "#ffd", "stroke": "#aa0"}},
        )
        lr = _layout_for("A")
        svg = render_svg(d, lr)
        # Text rule should still have the default text color
        assert ".node text { fill: #333333;" in svg
        # classDef fill should NOT appear in a text rule
        text_lines = [
            ln for ln in svg.split("\n")
            if ".node text" in ln and "fill:#ffd" in ln
        ]
        assert len(text_lines) == 0

    def test_explicit_color_becomes_text_fill(self):
        """classDef 'color' property should map to text fill in SVG."""
        d = Diagram(
            nodes=(Node(id="A", label="A", css_classes=("styled",)),),
            classes={"styled": {"fill": "#ff0", "color": "#fff"}},
        )
        lr = _layout_for("A")
        svg = render_svg(d, lr)
        # Shape elements get fill:#ff0
        assert ".styled rect" in svg
        assert "fill:#ff0" in svg
        # Text elements get fill:#fff (mapped from color)
        assert ".styled text" in svg
        assert "fill:#fff" in svg

    def test_color_only_class_targets_text(self):
        """classDef with only 'color' should only emit text rule."""
        d = Diagram(
            nodes=(Node(id="A", label="A", css_classes=("textonly",)),),
            classes={"textonly": {"color": "#f00"}},
        )
        lr = _layout_for("A")
        svg = render_svg(d, lr)
        # Only text rule, no shape rule
        assert ".textonly text" in svg
        assert "fill:#f00" in svg
        # No shape targeting for this class (no fill/stroke defined)
        assert ".textonly rect" not in svg

    def test_default_class_with_color(self):
        """Default classDef with color targets .node text."""
        d = Diagram(
            nodes=(Node(id="A", label="A"),),
            classes={"default": {"fill": "#ffd", "stroke": "#aa0", "color": "#000"}},
        )
        lr = _layout_for("A")
        svg = render_svg(d, lr)
        # Shape elements
        assert ".node rect" in svg
        assert "fill:#ffd" in svg
        # Text gets explicit color
        assert ".node text { fill:#000; }" in svg

    def test_stroke_dasharray_targets_shapes(self):
        """stroke-dasharray should go to shape elements, not text."""
        d = Diagram(
            nodes=(Node(id="A", label="A", css_classes=("dashed",)),),
            classes={"dashed": {"stroke-dasharray": "5,5", "stroke": "#f00"}},
        )
        lr = _layout_for("A")
        svg = render_svg(d, lr)
        assert ".dashed rect" in svg
        assert "stroke-dasharray:5,5" in svg
        assert ".dashed text" not in svg
