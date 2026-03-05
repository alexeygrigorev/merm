"""Tests for class diagram support (task 15).

Covers: IR dataclasses, parser, layout, renderer, and CLI integration.
25+ tests organized by component.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from pymermaid.ir.classdiag import (
    ClassDiagram,
    ClassMember,
    ClassNode,
    ClassRelation,
    RelationType,
    Visibility,
)
from pymermaid.layout.classdiag import (
    class_diagram_to_flowchart,
    layout_class_diagram,
)
from pymermaid.measure import TextMeasurer
from pymermaid.parser.classdiag import parse_class_diagram
from pymermaid.parser.flowchart import ParseError
from pymermaid.render.classdiag import (
    measure_class_box,
    render_class_diagram,
)

# ============================================================================
# IR dataclass tests
# ============================================================================


class TestIRDataclasses:
    """Test that IR dataclasses are correctly defined and frozen."""

    def test_visibility_values(self):
        assert Visibility.PUBLIC.value == "+"
        assert Visibility.PRIVATE.value == "-"
        assert Visibility.PROTECTED.value == "#"
        assert Visibility.PACKAGE.value == "~"

    def test_class_member_frozen(self):
        m = ClassMember(
            name="x", type_str="int",
            visibility=Visibility.PUBLIC, is_method=False,
        )
        assert m.name == "x"
        with pytest.raises(AttributeError):
            m.name = "y"  # type: ignore[misc]

    def test_class_node_frozen(self):
        node = ClassNode(id="A", label="A", annotation=None, members=())
        assert node.id == "A"
        with pytest.raises(AttributeError):
            node.id = "B"  # type: ignore[misc]

    def test_relation_type_values(self):
        assert RelationType.INHERITANCE.value == "inheritance"
        assert RelationType.COMPOSITION.value == "composition"
        assert RelationType.AGGREGATION.value == "aggregation"
        assert RelationType.ASSOCIATION.value == "association"
        assert RelationType.DEPENDENCY.value == "dependency"
        assert RelationType.REALIZATION.value == "realization"

    def test_class_relation_defaults(self):
        r = ClassRelation(source="A", target="B", rel_type=RelationType.ASSOCIATION)
        assert r.label == ""
        assert r.source_cardinality == ""
        assert r.target_cardinality == ""

    def test_class_diagram_frozen(self):
        d = ClassDiagram(classes=(), relations=())
        with pytest.raises(AttributeError):
            d.classes = ()  # type: ignore[misc]


# ============================================================================
# Parser tests
# ============================================================================


class TestParserDeclaration:
    """Test classDiagram declaration parsing."""

    def test_empty_input_raises(self):
        with pytest.raises(ParseError):
            parse_class_diagram("")

    def test_wrong_declaration_raises(self):
        with pytest.raises(ParseError, match="classDiagram"):
            parse_class_diagram("flowchart TD\n  A --> B")

    def test_minimal_declaration(self):
        d = parse_class_diagram("classDiagram\n")
        assert isinstance(d, ClassDiagram)
        assert d.classes == ()
        assert d.relations == ()


class TestParserClassDefinitions:
    """Test class definition parsing (block and shorthand)."""

    def test_class_shorthand(self):
        d = parse_class_diagram("classDiagram\n  class Animal")
        assert len(d.classes) == 1
        assert d.classes[0].id == "Animal"
        assert d.classes[0].label == "Animal"

    def test_class_block_with_members(self):
        text = """classDiagram
    class Animal {
        +name: string
        -age: int
        +makeSound()
        #sleep() void
    }"""
        d = parse_class_diagram(text)
        assert len(d.classes) == 1
        cls = d.classes[0]
        assert cls.id == "Animal"
        assert len(cls.members) == 4

        # Check fields
        fields = [m for m in cls.members if not m.is_method]
        assert len(fields) == 2
        assert fields[0].name == "name"
        assert fields[0].type_str == "string"
        assert fields[0].visibility == Visibility.PUBLIC
        assert fields[1].visibility == Visibility.PRIVATE

        # Check methods
        methods = [m for m in cls.members if m.is_method]
        assert len(methods) == 2
        assert methods[0].name == "makeSound"
        assert methods[1].name == "sleep"
        assert methods[1].visibility == Visibility.PROTECTED

    def test_member_shorthand(self):
        text = """classDiagram
    class Dog
    Dog : +bark()
    Dog : -breed: string"""
        d = parse_class_diagram(text)
        assert len(d.classes) == 1
        cls = d.classes[0]
        assert len(cls.members) == 2

    def test_annotation_in_block(self):
        text = """classDiagram
    class Flyable {
        <<interface>>
        +fly()
    }"""
        d = parse_class_diagram(text)
        cls = d.classes[0]
        assert cls.annotation == "<<interface>>"
        methods = [m for m in cls.members if m.is_method]
        assert len(methods) == 1

    def test_annotation_standalone(self):
        text = """classDiagram
    class Shape
    <<abstract>> Shape"""
        d = parse_class_diagram(text)
        assert d.classes[0].annotation == "<<abstract>>"


class TestParserRelationships:
    """Test relationship parsing."""

    def test_inheritance(self):
        text = "classDiagram\n  Animal <|-- Dog"
        d = parse_class_diagram(text)
        assert len(d.relations) == 1
        r = d.relations[0]
        assert r.rel_type == RelationType.INHERITANCE
        assert r.source == "Dog"
        assert r.target == "Animal"

    def test_inheritance_right_arrow(self):
        text = "classDiagram\n  Dog --|> Animal"
        d = parse_class_diagram(text)
        assert len(d.relations) == 1
        r = d.relations[0]
        assert r.rel_type == RelationType.INHERITANCE
        assert r.source == "Dog"
        assert r.target == "Animal"

    def test_composition(self):
        text = "classDiagram\n  Car *-- Engine"
        d = parse_class_diagram(text)
        r = d.relations[0]
        assert r.rel_type == RelationType.COMPOSITION
        assert r.source == "Engine"
        assert r.target == "Car"

    def test_aggregation(self):
        text = "classDiagram\n  Library o-- Book"
        d = parse_class_diagram(text)
        r = d.relations[0]
        assert r.rel_type == RelationType.AGGREGATION
        assert r.source == "Book"
        assert r.target == "Library"

    def test_association(self):
        text = "classDiagram\n  Student --> Course"
        d = parse_class_diagram(text)
        r = d.relations[0]
        assert r.rel_type == RelationType.ASSOCIATION
        assert r.source == "Student"
        assert r.target == "Course"

    def test_dependency(self):
        text = "classDiagram\n  Client ..> Service"
        d = parse_class_diagram(text)
        r = d.relations[0]
        assert r.rel_type == RelationType.DEPENDENCY
        assert r.source == "Client"
        assert r.target == "Service"

    def test_realization(self):
        text = "classDiagram\n  Duck ..|> Flyable"
        d = parse_class_diagram(text)
        r = d.relations[0]
        assert r.rel_type == RelationType.REALIZATION
        assert r.source == "Duck"
        assert r.target == "Flyable"

    def test_relationship_with_label(self):
        text = "classDiagram\n  A --> B : uses"
        d = parse_class_diagram(text)
        r = d.relations[0]
        assert r.label == "uses"

    def test_relationship_with_cardinality(self):
        text = 'classDiagram\n  Customer "1" --> "*" Order'
        d = parse_class_diagram(text)
        r = d.relations[0]
        assert r.source == "Customer"
        assert r.target == "Order"
        assert r.source_cardinality == "1"
        assert r.target_cardinality == "*"

    def test_auto_create_classes_from_relationships(self):
        text = "classDiagram\n  A --> B"
        d = parse_class_diagram(text)
        assert len(d.classes) == 2
        ids = {c.id for c in d.classes}
        assert ids == {"A", "B"}

    def test_multiple_relationships(self):
        text = """classDiagram
    Animal <|-- Dog
    Animal <|-- Cat
    Dog --> Bone"""
        d = parse_class_diagram(text)
        assert len(d.relations) == 3
        assert len(d.classes) == 4


class TestParserVisibility:
    """Test visibility marker parsing."""

    def test_public_visibility(self):
        text = """classDiagram
    class A {
        +publicField: string
    }"""
        d = parse_class_diagram(text)
        assert d.classes[0].members[0].visibility == Visibility.PUBLIC

    def test_private_visibility(self):
        text = """classDiagram
    class A {
        -privateField: int
    }"""
        d = parse_class_diagram(text)
        assert d.classes[0].members[0].visibility == Visibility.PRIVATE

    def test_protected_visibility(self):
        text = """classDiagram
    class A {
        #protectedMethod()
    }"""
        d = parse_class_diagram(text)
        assert d.classes[0].members[0].visibility == Visibility.PROTECTED

    def test_package_visibility(self):
        text = """classDiagram
    class A {
        ~packageField: boolean
    }"""
        d = parse_class_diagram(text)
        assert d.classes[0].members[0].visibility == Visibility.PACKAGE


class TestParserComments:
    """Test comment handling."""

    def test_comments_stripped(self):
        text = """classDiagram
    %% This is a comment
    class Animal
    Animal : +name: string %% inline comment"""
        d = parse_class_diagram(text)
        assert len(d.classes) == 1


# ============================================================================
# Layout tests
# ============================================================================


class TestClassLayout:
    """Test class diagram layout bridge."""

    def test_class_diagram_to_flowchart(self):
        diag = ClassDiagram(
            classes=(
                ClassNode(id="A", label="A", annotation=None, members=()),
                ClassNode(id="B", label="B", annotation=None, members=()),
            ),
            relations=(
                ClassRelation(
                    source="A", target="B",
                    rel_type=RelationType.ASSOCIATION,
                ),
            ),
        )
        fc = class_diagram_to_flowchart(diag)
        assert len(fc.nodes) == 2
        assert len(fc.edges) == 1

    def test_layout_produces_result(self):
        diag = ClassDiagram(
            classes=(
                ClassNode(id="A", label="A", annotation=None, members=()),
                ClassNode(id="B", label="B", annotation=None, members=()),
            ),
            relations=(
                ClassRelation(
                    source="A", target="B",
                    rel_type=RelationType.INHERITANCE,
                ),
            ),
        )
        measurer = TextMeasurer()
        result = layout_class_diagram(diag, measure_fn=measurer.measure)
        assert "A" in result.nodes
        assert "B" in result.nodes
        assert result.width > 0
        assert result.height > 0

    def test_layout_non_overlapping(self):
        """Verify that laid-out class boxes don't overlap."""
        text = """classDiagram
    class Animal {
        +name: string
    }
    class Dog {
        +breed: string
    }
    Animal <|-- Dog"""
        diag = parse_class_diagram(text)
        measurer = TextMeasurer()
        result = layout_class_diagram(diag, measure_fn=measurer.measure)

        nl_a = result.nodes["Animal"]
        nl_b = result.nodes["Dog"]

        # Check no overlap (at least one axis must be non-overlapping)
        no_x_overlap = nl_a.x + nl_a.width <= nl_b.x or nl_b.x + nl_b.width <= nl_a.x
        no_y_overlap = nl_a.y + nl_a.height <= nl_b.y or nl_b.y + nl_b.height <= nl_a.y
        assert no_x_overlap or no_y_overlap


# ============================================================================
# Measure tests
# ============================================================================


class TestMeasureClassBox:
    """Test class box measurement."""

    def test_empty_class_has_minimum_size(self):
        node = ClassNode(id="A", label="A", annotation=None, members=())
        w, h = measure_class_box(node)
        assert w >= 100.0
        assert h > 0

    def test_class_with_members_larger(self):
        node_empty = ClassNode(id="A", label="A", annotation=None, members=())
        node_full = ClassNode(
            id="B", label="B", annotation=None,
            members=(
                ClassMember("x", "int", Visibility.PUBLIC, False),
                ClassMember("y", "string", Visibility.PRIVATE, False),
                ClassMember("doStuff", "void", Visibility.PUBLIC, True),
            ),
        )
        _, h_empty = measure_class_box(node_empty)
        _, h_full = measure_class_box(node_full)
        assert h_full > h_empty

    def test_annotation_adds_height(self):
        node_no_ann = ClassNode(id="A", label="A", annotation=None, members=())
        node_ann = ClassNode(id="A", label="A", annotation="<<interface>>", members=())
        _, h_no = measure_class_box(node_no_ann)
        _, h_ann = measure_class_box(node_ann)
        assert h_ann > h_no


# ============================================================================
# Renderer tests
# ============================================================================


class TestRenderer:
    """Test SVG rendering of class diagrams."""

    def _render(self, text: str) -> str:
        diag = parse_class_diagram(text)
        measurer = TextMeasurer()
        layout = layout_class_diagram(diag, measure_fn=measurer.measure)
        return render_class_diagram(diag, layout)

    def _parse_svg(self, svg: str) -> ET.Element:
        return ET.fromstring(svg)

    def test_renders_valid_svg(self):
        svg = self._render("classDiagram\n  class Animal")
        root = self._parse_svg(svg)
        assert root.tag == "{http://www.w3.org/2000/svg}svg" or root.tag == "svg"

    def test_class_node_has_rect(self):
        svg = self._render("classDiagram\n  class Animal")
        assert "rect" in svg

    def test_class_node_has_name_text(self):
        svg = self._render("classDiagram\n  class Animal")
        assert "Animal" in svg

    def test_three_section_box(self):
        """Verify divider lines are rendered."""
        text = """classDiagram
    class Animal {
        +name: string
        +makeSound()
    }"""
        svg = self._render(text)
        root = self._parse_svg(svg)
        # Should have divider lines
        ns = {"svg": "http://www.w3.org/2000/svg"}
        lines = root.findall(".//svg:g[@class='class-node']//svg:line", ns)
        # At least 2 divider lines (after header, after fields)
        assert len(lines) >= 2

    def test_visibility_markers_in_output(self):
        text = """classDiagram
    class Foo {
        +publicField: int
        -privateField: string
        #protectedMethod()
        ~packageMethod()
    }"""
        svg = self._render(text)
        assert "+publicField" in svg
        assert "-privateField" in svg
        assert "#protectedMethod()" in svg
        assert "~packageMethod()" in svg

    def test_annotation_rendered(self):
        text = """classDiagram
    class Flyable {
        <<interface>>
        +fly()
    }"""
        svg = self._render(text)
        assert "&lt;&lt;interface&gt;&gt;" in svg or "<<interface>>" in svg

    def test_relationship_edge_rendered(self):
        text = """classDiagram
    A --> B"""
        svg = self._render(text)
        assert "class-edge" in svg

    def test_dashed_line_for_dependency(self):
        text = """classDiagram
    A ..> B"""
        svg = self._render(text)
        assert "stroke-dasharray" in svg

    def test_dashed_line_for_realization(self):
        text = """classDiagram
    A ..|> B"""
        svg = self._render(text)
        assert "stroke-dasharray" in svg

    def test_marker_defs_present(self):
        text = """classDiagram
    A <|-- B"""
        svg = self._render(text)
        assert "inherit-arrow" in svg

    def test_relationship_label_rendered(self):
        text = """classDiagram
    A --> B : uses"""
        svg = self._render(text)
        assert "uses" in svg

    def test_cardinality_rendered(self):
        text = 'classDiagram\n  Customer "1" --> "*" Order'
        svg = self._render(text)
        # Cardinality text should appear in SVG
        assert '"1"' in svg or ">1<" in svg
        assert '"*"' in svg or ">*<" in svg

    def test_all_six_marker_types(self):
        """Verify all 6 relationship marker definitions are created."""
        text = """classDiagram
    A <|-- B
    C *-- D
    E o-- F
    G --> H
    I ..> J
    K ..|> L"""
        svg = self._render(text)
        assert "inherit-arrow" in svg
        assert "composition-arrow" in svg
        assert "aggregation-arrow" in svg
        assert "association-arrow" in svg
        assert "dependency-arrow" in svg
        assert "realization-arrow" in svg

    def test_theme_colors_applied(self):
        from pymermaid.theme import Theme

        text = "classDiagram\n  class A"
        diag = parse_class_diagram(text)
        measurer = TextMeasurer()
        layout = layout_class_diagram(diag, measure_fn=measurer.measure)
        custom_theme = Theme(node_fill="#FF0000")
        svg = render_class_diagram(diag, layout, theme=custom_theme)
        assert "#FF0000" in svg


# ============================================================================
# Integration tests
# ============================================================================


class TestIntegration:
    """End-to-end integration tests."""

    def test_complex_diagram(self):
        """Test a realistic class diagram with multiple features."""
        text = """classDiagram
    class Animal {
        <<abstract>>
        +name: string
        +age: int
        +makeSound()
        +move()
    }
    class Dog {
        +breed: string
        +bark()
        +fetch()
    }
    class Cat {
        -indoor: boolean
        +purr()
    }
    class Flyable {
        <<interface>>
        +fly()
    }
    class Duck {
        +swim()
    }
    Animal <|-- Dog
    Animal <|-- Cat
    Animal <|-- Duck
    Duck ..|> Flyable
    Dog --> Bone : chews"""
        diag = parse_class_diagram(text)
        assert len(diag.classes) >= 5  # Animal, Dog, Cat, Flyable, Duck + maybe Bone
        assert len(diag.relations) == 5

        measurer = TextMeasurer()
        layout = layout_class_diagram(diag, measure_fn=measurer.measure)
        svg = render_class_diagram(diag, layout)

        # Verify key elements are present
        assert "Animal" in svg
        assert "Dog" in svg
        assert "Cat" in svg
        assert "Flyable" in svg
        assert "Duck" in svg
        assert "class-node" in svg
        assert "class-edge" in svg

    def test_full_pipeline(self):
        """Test the full parse -> layout -> render pipeline."""
        text = """classDiagram
    class A
    class B
    A --> B"""
        diag = parse_class_diagram(text)
        measurer = TextMeasurer()
        layout = layout_class_diagram(diag, measure_fn=measurer.measure)
        svg = render_class_diagram(diag, layout)
        assert "<svg" in svg
        assert "A" in svg
        assert "B" in svg

    def test_enumeration_annotation(self):
        text = """classDiagram
    class Color {
        <<enumeration>>
        +RED
        +GREEN
        +BLUE
    }"""
        diag = parse_class_diagram(text)
        assert diag.classes[0].annotation == "<<enumeration>>"
        assert len(diag.classes[0].members) == 3
