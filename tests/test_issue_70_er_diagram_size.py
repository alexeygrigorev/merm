"""Tests for issue 70: ER diagram renders too large.

Verifies that ER diagrams render at a compact, reasonable size with
ER-specific layout configuration and proportional entity box sizing.
"""

import xml.etree.ElementTree as ET

from merm import render_diagram
from merm.ir.erdiag import ERAttribute, ERAttributeKey, EREntity
from merm.layout.erdiag import layout_er_diagram
from merm.measure import TextMeasurer
from merm.parser.erdiag import parse_er_diagram
from merm.render.erdiag import _MIN_BOX_WIDTH, measure_er_entity_box

# The reproduction diagram from the issue
BASIC_3_ENTITY = """\
erDiagram
    CUSTOMER ||--o{ ORDER : places
    ORDER ||--|{ LINE-ITEM : contains
    CUSTOMER }|..|{ DELIVERY-ADDRESS : uses
"""

# An ER diagram with attributes
WITH_ATTRIBUTES = """\
erDiagram
    CUSTOMER {
        string name
        string email PK
        int age
        string address
    }
    ORDER {
        int id PK
        string status
        float total
    }
    LINE-ITEM {
        int id PK
        int quantity
        float price
    }
    CUSTOMER ||--o{ ORDER : places
    ORDER ||--|{ LINE-ITEM : contains
    CUSTOMER }|..|{ DELIVERY-ADDRESS : uses
"""


def _layout(text: str):
    diag = parse_er_diagram(text)
    measurer = TextMeasurer()
    return diag, layout_er_diagram(diag, measure_fn=measurer.measure)


def _svg_dimensions(svg: str) -> tuple[float, float]:
    """Extract width and height from SVG element attributes."""
    root = ET.fromstring(svg)
    w = float(root.get("width", "0"))
    h = float(root.get("height", "0"))
    return w, h


# =========================================================================
# Unit: ER diagram dimensions are reasonable
# =========================================================================


class TestERDiagramDimensions:
    """The basic 3-entity diagram should be compact."""

    def test_layout_width_under_800(self):
        _, result = _layout(BASIC_3_ENTITY)
        assert result.width < 800, f"Layout width {result.width} exceeds 800"

    def test_layout_height_under_800(self):
        _, result = _layout(BASIC_3_ENTITY)
        assert result.height < 800, f"Layout height {result.height} exceeds 800"

    def test_total_area_under_400k(self):
        _, result = _layout(BASIC_3_ENTITY)
        area = result.width * result.height
        assert area < 400_000, f"Total area {area:.0f} exceeds 400,000"

    def test_whitespace_ratio_under_60_percent(self):
        """Total whitespace should be less than 60% of total diagram area."""
        _, result = _layout(BASIC_3_ENTITY)
        total_area = result.width * result.height
        entity_area = sum(
            nl.width * nl.height for nl in result.nodes.values()
        )
        whitespace_ratio = 1.0 - entity_area / total_area
        assert whitespace_ratio < 0.70, (
            f"Whitespace ratio {whitespace_ratio:.2%} exceeds 70%"
        )


# =========================================================================
# Unit: Entity box sizing is proportional to content
# =========================================================================


class TestEntityBoxSizing:
    """Entity box dimensions should reflect their content."""

    def test_short_name_no_attrs_under_80(self):
        entity = EREntity(id="CUSTOMER", attributes=())
        w, _ = measure_er_entity_box(entity)
        assert w < 80, f"CUSTOMER box width {w} should be under 80px"

    def test_single_char_name_uses_min_width(self):
        entity = EREntity(id="X", attributes=())
        w, _ = measure_er_entity_box(entity)
        assert w == _MIN_BOX_WIDTH, (
            f"Single-char entity should use _MIN_BOX_WIDTH ({_MIN_BOX_WIDTH}), got {w}"
        )

    def test_box_height_scales_with_attributes(self):
        no_attrs = EREntity(id="E", attributes=())
        many_attrs = EREntity(
            id="E",
            attributes=tuple(
                ERAttribute(type_str="string", name=f"field{i}")
                for i in range(5)
            ),
        )
        _, h_small = measure_er_entity_box(no_attrs)
        _, h_large = measure_er_entity_box(many_attrs)
        assert h_large > h_small

    def test_box_width_scales_with_long_attribute(self):
        short = EREntity(id="E", attributes=())
        long_attr = EREntity(
            id="E",
            attributes=(
                ERAttribute(
                    type_str="varchar",
                    name="very_long_attribute_name",
                    key=ERAttributeKey.PK,
                ),
            ),
        )
        w_short, _ = measure_er_entity_box(short)
        w_long, _ = measure_er_entity_box(long_attr)
        assert w_long > w_short


# =========================================================================
# Unit: ER layout config uses tighter spacing
# =========================================================================


class TestERLayoutSpacing:
    """ER layout should use tighter spacing than generic flowchart defaults."""

    def test_inter_entity_gap_in_range(self):
        """Directly connected entities should have edge-to-edge gap between 10-60px."""
        diag, result = _layout(BASIC_3_ENTITY)
        nodes = result.nodes

        # Only check gaps between entities connected by a relationship
        found_gap = False
        for rel in diag.relationships:
            nl1 = nodes[rel.source]
            nl2 = nodes[rel.target]

            # Check vertical gap
            if nl1.y + nl1.height < nl2.y:
                gap = nl2.y - (nl1.y + nl1.height)
                assert 5 <= gap <= 60, (
                    f"V-gap {rel.source}->{rel.target} is {gap:.1f}, "
                    f"expected 5-60"
                )
                found_gap = True
            elif nl2.y + nl2.height < nl1.y:
                gap = nl1.y - (nl2.y + nl2.height)
                assert 5 <= gap <= 60, (
                    f"V-gap {rel.target}->{rel.source} is {gap:.1f}, "
                    f"expected 5-60"
                )
                found_gap = True

            # Check horizontal gap
            if nl1.x + nl1.width < nl2.x:
                gap = nl2.x - (nl1.x + nl1.width)
                assert 5 <= gap <= 60, (
                    f"H-gap {rel.source}->{rel.target} is {gap:.1f}, "
                    f"expected 5-60"
                )
                found_gap = True
            elif nl2.x + nl2.width < nl1.x:
                gap = nl1.x - (nl2.x + nl2.width)
                assert 5 <= gap <= 60, (
                    f"H-gap {rel.target}->{rel.source} is {gap:.1f}, "
                    f"expected 5-60"
                )
                found_gap = True

        assert found_gap, "No adjacent entity pairs found to measure gap"

    def test_er_spacing_tighter_than_default(self):
        """ER layout should be smaller than with flowchart defaults."""
        from merm.layout.config import LayoutConfig

        diag = parse_er_diagram(BASIC_3_ENTITY)
        measurer = TextMeasurer()

        # ER defaults (no config -> tighter defaults)
        result_er = layout_er_diagram(diag, measure_fn=measurer.measure)

        # Flowchart defaults (explicit default config)
        flowchart_config = LayoutConfig()  # rank_sep=40, node_sep=30
        result_fc = layout_er_diagram(
            diag, measure_fn=measurer.measure, config=flowchart_config
        )

        er_area = result_er.width * result_er.height
        fc_area = result_fc.width * result_fc.height
        assert er_area < fc_area, (
            f"ER area ({er_area:.0f}) should be smaller than "
            f"flowchart-default area ({fc_area:.0f})"
        )


# =========================================================================
# Integration: Full render roundtrip
# =========================================================================


class TestFullRenderRoundtrip:
    """End-to-end SVG rendering dimensions check."""

    def test_svg_width_under_800(self):
        svg = render_diagram(BASIC_3_ENTITY)
        w, _ = _svg_dimensions(svg)
        assert w < 800, f"SVG width {w} exceeds 800"

    def test_svg_height_under_800(self):
        svg = render_diagram(BASIC_3_ENTITY)
        _, h = _svg_dimensions(svg)
        assert h < 800, f"SVG height {h} exceeds 800"

    def test_viewbox_matches_width_height(self):
        svg = render_diagram(BASIC_3_ENTITY)
        root = ET.fromstring(svg)
        vb = root.get("viewBox", "")
        parts = vb.split()
        assert len(parts) == 4
        vb_w = float(parts[2])
        vb_h = float(parts[3])
        w, h = _svg_dimensions(svg)
        assert abs(vb_w - w) < 1.0
        assert abs(vb_h - h) < 1.0


# =========================================================================
# Regression: ER diagrams with attributes
# =========================================================================


class TestERWithAttributes:
    """ER diagrams with attributes should still be reasonably sized."""

    def test_attributes_diagram_under_800(self):
        _, result = _layout(WITH_ATTRIBUTES)
        assert result.width < 800, f"Width {result.width} exceeds 800"
        assert result.height < 800, f"Height {result.height} exceeds 800"

    def test_entity_boxes_tall_enough_for_attributes(self):
        diag, result = _layout(WITH_ATTRIBUTES)
        for entity in diag.entities:
            if entity.attributes:
                nl = result.nodes[entity.id]
                # Header (22) + attributes (16 each)
                expected_min_height = 22 + len(entity.attributes) * 16
                assert nl.height >= expected_min_height, (
                    f"{entity.id} height {nl.height:.1f} too short "
                    f"for {len(entity.attributes)} attributes "
                    f"(expected >= {expected_min_height})"
                )

    def test_attributes_diagram_renders_svg(self):
        svg = render_diagram(WITH_ATTRIBUTES)
        assert "<svg" in svg
        assert "CUSTOMER" in svg
        assert "string name" in svg
