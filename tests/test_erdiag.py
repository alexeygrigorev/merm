"""Tests for ER diagram support (task 45).

Covers: IR dataclasses, parser, layout, renderer, and integration.
"""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from merm import render_diagram
from merm.ir.erdiag import (
    ERAttribute,
    ERAttributeKey,
    ERCardinality,
    ERDiagram,
    EREntity,
    ERLineStyle,
    ERRelationship,
)
from merm.layout.erdiag import er_diagram_to_flowchart, layout_er_diagram
from merm.measure import TextMeasurer
from merm.parser.erdiag import parse_er_diagram
from merm.parser.flowchart import ParseError
from merm.render.erdiag import measure_er_entity_box, render_er_diagram

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "corpus" / "er"

# ============================================================================
# IR dataclass tests
# ============================================================================

class TestIRDataclasses:
    """Test that IR dataclasses are correctly defined and frozen."""

    def test_attribute_with_all_fields(self):
        attr = ERAttribute(type_str="string", name="email", key=ERAttributeKey.PK)
        assert attr.type_str == "string"
        assert attr.name == "email"
        assert attr.key == ERAttributeKey.PK

    def test_attribute_default_key(self):
        attr = ERAttribute(type_str="int", name="age")
        assert attr.key == ERAttributeKey.NONE

    def test_entity_with_multiple_attributes(self):
        attrs = (
            ERAttribute(type_str="string", name="name"),
            ERAttribute(type_str="int", name="id", key=ERAttributeKey.PK),
        )
        entity = EREntity(id="CUSTOMER", attributes=attrs)
        assert entity.id == "CUSTOMER"
        assert len(entity.attributes) == 2
        assert entity.attributes[1].key == ERAttributeKey.PK

    def test_entity_frozen(self):
        entity = EREntity(id="A", attributes=())
        with pytest.raises(AttributeError):
            entity.id = "B"  # type: ignore[misc]

    def test_relationship_all_fields(self):
        rel = ERRelationship(
            source="CUSTOMER",
            target="ORDER",
            source_cardinality=ERCardinality.EXACTLY_ONE,
            target_cardinality=ERCardinality.ZERO_OR_MORE,
            line_style=ERLineStyle.SOLID,
            label="places",
        )
        assert rel.source == "CUSTOMER"
        assert rel.target == "ORDER"
        assert rel.source_cardinality == ERCardinality.EXACTLY_ONE
        assert rel.target_cardinality == ERCardinality.ZERO_OR_MORE
        assert rel.line_style == ERLineStyle.SOLID
        assert rel.label == "places"

    def test_diagram_frozen(self):
        d = ERDiagram(entities=(), relationships=())
        with pytest.raises(AttributeError):
            d.entities = ()  # type: ignore[misc]

    def test_cardinality_enum_values(self):
        assert ERCardinality.EXACTLY_ONE.value == "EXACTLY_ONE"
        assert ERCardinality.ZERO_OR_ONE.value == "ZERO_OR_ONE"
        assert ERCardinality.ONE_OR_MORE.value == "ONE_OR_MORE"
        assert ERCardinality.ZERO_OR_MORE.value == "ZERO_OR_MORE"

    def test_line_style_enum_values(self):
        assert ERLineStyle.SOLID.value == "SOLID"
        assert ERLineStyle.DASHED.value == "DASHED"

    def test_attribute_key_enum_values(self):
        assert ERAttributeKey.NONE.value == "NONE"
        assert ERAttributeKey.PK.value == "PK"
        assert ERAttributeKey.FK.value == "FK"
        assert ERAttributeKey.UK.value == "UK"

# ============================================================================
# Parser tests - entity blocks
# ============================================================================

class TestParserEntityBlocks:
    """Test entity definition parsing."""

    def test_entity_with_3_attributes(self):
        text = """erDiagram
    CUSTOMER {
        string name
        int age
        string email PK
    }"""
        d = parse_er_diagram(text)
        assert len(d.entities) == 1
        entity = d.entities[0]
        assert entity.id == "CUSTOMER"
        assert len(entity.attributes) == 3
        assert entity.attributes[0].type_str == "string"
        assert entity.attributes[0].name == "name"
        assert entity.attributes[2].key == ERAttributeKey.PK

    def test_entity_with_pk_fk_uk(self):
        text = """erDiagram
    ITEM {
        int id PK
        int customer_id FK
        string email UK
    }"""
        d = parse_er_diagram(text)
        entity = d.entities[0]
        assert entity.attributes[0].key == ERAttributeKey.PK
        assert entity.attributes[1].key == ERAttributeKey.FK
        assert entity.attributes[2].key == ERAttributeKey.UK

    def test_entity_empty_block(self):
        # Entity with no attributes but has braces
        text = """erDiagram
    EMPTY {
    }"""
        d = parse_er_diagram(text)
        assert len(d.entities) == 1
        assert d.entities[0].id == "EMPTY"
        assert d.entities[0].attributes == ()

    def test_entity_referenced_only_in_relationship(self):
        text = """erDiagram
    A ||--o{ B : links"""
        d = parse_er_diagram(text)
        assert len(d.entities) == 2
        ids = {e.id for e in d.entities}
        assert ids == {"A", "B"}
        # Both have empty attributes
        for e in d.entities:
            assert e.attributes == ()

    def test_multiple_entities(self):
        text = """erDiagram
    CUSTOMER {
        string name
    }
    ORDER {
        int id PK
    }
    PRODUCT {
        string name
        float price
    }"""
        d = parse_er_diagram(text)
        assert len(d.entities) == 3
        ids = {e.id for e in d.entities}
        assert ids == {"CUSTOMER", "ORDER", "PRODUCT"}

# ============================================================================
# Parser tests - relationships
# ============================================================================

class TestParserRelationships:
    """Test relationship parsing."""

    def test_one_to_zero_or_more(self):
        text = "erDiagram\n    CUSTOMER ||--o{ ORDER : places"
        d = parse_er_diagram(text)
        assert len(d.relationships) == 1
        r = d.relationships[0]
        assert r.source == "CUSTOMER"
        assert r.target == "ORDER"
        assert r.source_cardinality == ERCardinality.EXACTLY_ONE
        assert r.target_cardinality == ERCardinality.ZERO_OR_MORE
        assert r.line_style == ERLineStyle.SOLID
        assert r.label == "places"

    def test_one_to_one_or_more(self):
        text = "erDiagram\n    A ||--|{ B : contains"
        d = parse_er_diagram(text)
        r = d.relationships[0]
        assert r.source_cardinality == ERCardinality.EXACTLY_ONE
        assert r.target_cardinality == ERCardinality.ONE_OR_MORE
        assert r.line_style == ERLineStyle.SOLID

    def test_one_or_more_to_one_or_more_dashed(self):
        text = "erDiagram\n    A }|..|{ B : uses"
        d = parse_er_diagram(text)
        r = d.relationships[0]
        assert r.source_cardinality == ERCardinality.ONE_OR_MORE
        assert r.target_cardinality == ERCardinality.ONE_OR_MORE
        assert r.line_style == ERLineStyle.DASHED

    def test_one_to_one(self):
        text = "erDiagram\n    A ||--|| B : has"
        d = parse_er_diagram(text)
        r = d.relationships[0]
        assert r.source_cardinality == ERCardinality.EXACTLY_ONE
        assert r.target_cardinality == ERCardinality.EXACTLY_ONE
        assert r.line_style == ERLineStyle.SOLID

    def test_zero_or_more_to_zero_or_more(self):
        text = "erDiagram\n    A }o--o{ B : enrolls"
        d = parse_er_diagram(text)
        r = d.relationships[0]
        assert r.source_cardinality == ERCardinality.ZERO_OR_MORE
        assert r.target_cardinality == ERCardinality.ZERO_OR_MORE

    def test_zero_or_one_to_exactly_one(self):
        text = "erDiagram\n    A o|--|| B : belongs"
        d = parse_er_diagram(text)
        r = d.relationships[0]
        assert r.source_cardinality == ERCardinality.ZERO_OR_ONE
        assert r.target_cardinality == ERCardinality.EXACTLY_ONE

    def test_quoted_label(self):
        text = 'erDiagram\n    A ||--o{ B : "has many"'
        d = parse_er_diagram(text)
        r = d.relationships[0]
        assert r.label == "has many"

    def test_creates_two_entities_and_one_relationship(self):
        """Acceptance criteria: parse basic returns 2 entities, 1 relationship."""
        text = "erDiagram\n    CUSTOMER ||--o{ ORDER : places"
        d = parse_er_diagram(text)
        assert len(d.entities) == 2
        assert len(d.relationships) == 1

# ============================================================================
# Parser tests - edge cases
# ============================================================================

class TestParserEdgeCases:
    """Test parser edge cases."""

    def test_empty_diagram(self):
        d = parse_er_diagram("erDiagram\n")
        assert isinstance(d, ERDiagram)
        assert d.entities == ()
        assert d.relationships == ()

    def test_comments_skipped(self):
        text = """erDiagram
    %% This is a comment
    CUSTOMER ||--o{ ORDER : places
    %% Another comment"""
        d = parse_er_diagram(text)
        assert len(d.relationships) == 1
        assert len(d.entities) == 2

    def test_entity_name_with_hyphens(self):
        text = "erDiagram\n    LINE-ITEM ||--o{ DELIVERY-ADDRESS : links"
        d = parse_er_diagram(text)
        ids = {e.id for e in d.entities}
        assert "LINE-ITEM" in ids
        assert "DELIVERY-ADDRESS" in ids

    def test_whitespace_variations(self):
        text = "erDiagram\n\tCUSTOMER  ||--o{  ORDER  :  places"
        d = parse_er_diagram(text)
        assert len(d.relationships) == 1

    def test_empty_input_raises(self):
        with pytest.raises(ParseError):
            parse_er_diagram("")

    def test_wrong_declaration_raises(self):
        with pytest.raises(ParseError, match="erDiagram"):
            parse_er_diagram("flowchart TD\n  A --> B")

    def test_attribute_string_name_pk(self):
        """Acceptance criteria: 'string name PK' produces correct ERAttribute."""
        text = """erDiagram
    CUSTOMER {
        string name PK
    }"""
        d = parse_er_diagram(text)
        attr = d.entities[0].attributes[0]
        assert attr.type_str == "string"
        assert attr.name == "name"
        assert attr.key == ERAttributeKey.PK

# ============================================================================
# Layout tests
# ============================================================================

class TestERLayout:
    """Test ER diagram layout."""

    def test_er_diagram_to_flowchart(self):
        diag = ERDiagram(
            entities=(
                EREntity(id="A", attributes=()),
                EREntity(id="B", attributes=()),
            ),
            relationships=(
                ERRelationship(
                    source="A", target="B",
                    source_cardinality=ERCardinality.EXACTLY_ONE,
                    target_cardinality=ERCardinality.ZERO_OR_MORE,
                    line_style=ERLineStyle.SOLID,
                    label="test",
                ),
            ),
        )
        fc = er_diagram_to_flowchart(diag)
        assert len(fc.nodes) == 2
        assert len(fc.edges) == 1

    def test_layout_two_entities_non_overlapping(self):
        text = "erDiagram\n    A ||--o{ B : links"
        diag = parse_er_diagram(text)
        measurer = TextMeasurer()
        result = layout_er_diagram(diag, measure_fn=measurer.measure)
        assert "A" in result.nodes
        assert "B" in result.nodes

        nl_a = result.nodes["A"]
        nl_b = result.nodes["B"]
        no_x_overlap = nl_a.x + nl_a.width <= nl_b.x or nl_b.x + nl_b.width <= nl_a.x
        no_y_overlap = nl_a.y + nl_a.height <= nl_b.y or nl_b.y + nl_b.height <= nl_a.y
        assert no_x_overlap or no_y_overlap

    def test_layout_four_entities(self):
        text = """erDiagram
    A ||--o{ B : r1
    C ||--|{ D : r2"""
        diag = parse_er_diagram(text)
        measurer = TextMeasurer()
        result = layout_er_diagram(diag, measure_fn=measurer.measure)
        assert len(result.nodes) == 4
        for nid, nl in result.nodes.items():
            assert nl.width > 0
            assert nl.height > 0

    def test_entity_height_scales_with_attributes(self):
        entity_empty = EREntity(id="A", attributes=())
        entity_full = EREntity(
            id="B",
            attributes=(
                ERAttribute(type_str="string", name="name"),
                ERAttribute(type_str="int", name="age"),
                ERAttribute(type_str="string", name="email"),
                ERAttribute(type_str="string", name="address"),
            ),
        )
        _, h_empty = measure_er_entity_box(entity_empty)
        _, h_full = measure_er_entity_box(entity_full)
        assert h_full > h_empty

# ============================================================================
# Renderer tests
# ============================================================================

class TestRenderer:
    """Test SVG rendering of ER diagrams."""

    def _render(self, text: str) -> str:
        diag = parse_er_diagram(text)
        measurer = TextMeasurer()
        layout = layout_er_diagram(diag, measure_fn=measurer.measure)
        return render_er_diagram(diag, layout)

    def _parse_svg(self, svg: str) -> ET.Element:
        return ET.fromstring(svg)

    def test_renders_valid_svg(self):
        svg = self._render("erDiagram\n    CUSTOMER ||--o{ ORDER : places")
        assert "<svg" in svg
        assert "</svg>" in svg

    def test_entity_has_rect(self):
        svg = self._render("erDiagram\n    CUSTOMER ||--o{ ORDER : places")
        root = self._parse_svg(svg)
        ns = {"svg": "http://www.w3.org/2000/svg"}
        rects = root.findall(".//svg:g[@class='er-entity']//svg:rect", ns)
        assert len(rects) == 2

    def test_entity_has_name_text(self):
        svg = self._render("erDiagram\n    CUSTOMER ||--o{ ORDER : places")
        assert "CUSTOMER" in svg
        assert "ORDER" in svg

    def test_relationship_has_path(self):
        svg = self._render("erDiagram\n    CUSTOMER ||--o{ ORDER : places")
        root = self._parse_svg(svg)
        ns = {"svg": "http://www.w3.org/2000/svg"}
        paths = root.findall(".//svg:g[@class='er-relationship']//svg:path", ns)
        assert len(paths) >= 1

    def test_relationship_label_rendered(self):
        svg = self._render("erDiagram\n    CUSTOMER ||--o{ ORDER : places")
        assert "places" in svg

    def test_attributes_render_inside_entity(self):
        text = """erDiagram
    CUSTOMER {
        string name
        int age
    }"""
        svg = self._render(text)
        assert "string name" in svg
        assert "int age" in svg

    def test_key_markers_visually_distinct(self):
        """PK/FK/UK key markers render with bold+italic."""
        text = """erDiagram
    CUSTOMER {
        string email PK
        int order_id FK
    }"""
        svg = self._render(text)
        root = self._parse_svg(svg)
        ns = {"svg": "http://www.w3.org/2000/svg"}
        # Find text elements with font-weight=bold and font-style=italic
        bold_italic_texts = root.findall(
            ".//svg:g[@class='er-entity']//svg:text[@font-weight='bold'][@font-style='italic']",
            ns,
        )
        assert len(bold_italic_texts) >= 2
        key_texts = {t.text for t in bold_italic_texts}
        assert "PK" in key_texts
        assert "FK" in key_texts

    def test_cardinality_markers_at_endpoints(self):
        svg = self._render("erDiagram\n    A ||--o{ B : test")
        assert "er-exactly-one" in svg
        assert "er-zero-or-more" in svg

    def test_dashed_line_style(self):
        svg = self._render("erDiagram\n    A ||..o{ B : test")
        assert "stroke-dasharray" in svg

    def test_three_entities_three_rects(self):
        text = """erDiagram
    A ||--o{ B : r1
    B ||--|{ C : r2"""
        svg = self._render(text)
        root = self._parse_svg(svg)
        ns = {"svg": "http://www.w3.org/2000/svg"}
        rects = root.findall(".//svg:g[@class='er-entity']//svg:rect", ns)
        assert len(rects) == 3

    def test_marker_defs_present(self):
        svg = self._render("erDiagram\n    A ||--o{ B : test")
        assert "er-exactly-one" in svg
        assert "er-zero-or-one" in svg
        assert "er-one-or-more" in svg
        assert "er-zero-or-more" in svg

    def test_er_entity_css_class(self):
        svg = self._render("erDiagram\n    A ||--o{ B : test")
        assert "er-entity" in svg

    def test_er_relationship_css_class(self):
        svg = self._render("erDiagram\n    A ||--o{ B : test")
        assert "er-relationship" in svg

# ============================================================================
# Integration tests
# ============================================================================

class TestIntegration:
    """End-to-end integration tests using render_diagram()."""

    def test_render_diagram_basic(self):
        svg = render_diagram("erDiagram\n    CUSTOMER ||--o{ ORDER : places")
        assert "<svg" in svg
        assert "</svg>" in svg

    def test_render_all_fixtures(self):
        """Render all corpus fixture files without errors."""
        fixtures = sorted(FIXTURES_DIR.glob("*.mmd"))
        assert len(fixtures) >= 5, f"Expected >= 5 fixtures, found {len(fixtures)}"
        for fixture in fixtures:
            source = fixture.read_text()
            svg = render_diagram(source)
            assert "<svg" in svg, f"Failed for {fixture.name}"
            assert "</svg>" in svg, f"Failed for {fixture.name}"

    def test_basic_fixture(self):
        source = (FIXTURES_DIR / "basic.mmd").read_text()
        svg = render_diagram(source)
        assert "CUSTOMER" in svg
        assert "ORDER" in svg
        assert "LINE-ITEM" in svg

    def test_attributes_fixture(self):
        source = (FIXTURES_DIR / "attributes.mmd").read_text()
        svg = render_diagram(source)
        assert "string name" in svg
        assert "PK" in svg

    def test_complex_fixture(self):
        source = (FIXTURES_DIR / "complex.mmd").read_text()
        svg = render_diagram(source)
        assert "CUSTOMER" in svg
        assert "PRODUCT" in svg
        assert "DELIVERY-ADDRESS" in svg
        assert "stroke-dasharray" in svg  # dashed line present

    def test_all_cardinalities_fixture(self):
        source = (FIXTURES_DIR / "all_cardinalities.mmd").read_text()
        d = parse_er_diagram(source)
        assert len(d.relationships) == 5
        svg = render_diagram(source)
        assert "<svg" in svg

    def test_dashed_lines_fixture(self):
        source = (FIXTURES_DIR / "dashed_lines.mmd").read_text()
        svg = render_diagram(source)
        assert "stroke-dasharray" in svg
