"""Tests for the intermediate representation data model."""

import dataclasses

import pytest

from pymermaid.ir import (
    ArrowType,
    Diagram,
    DiagramType,
    Direction,
    Edge,
    EdgeType,
    Node,
    NodeShape,
    StyleDef,
    Subgraph,
)

# ---------- Enum completeness ----------


class TestEnumCompleteness:
    def test_diagram_type_has_at_least_9_members(self):
        assert len(DiagramType) >= 9

    def test_diagram_type_members(self):
        expected = {
            "flowchart",
            "sequence",
            "class_diagram",
            "state",
            "er",
            "gantt",
            "pie",
            "mindmap",
            "git_graph",
        }
        assert {m.name for m in DiagramType} >= expected

    def test_direction_has_exactly_5_members(self):
        assert len(Direction) == 5

    def test_direction_members(self):
        for name in ("TB", "TD", "BT", "LR", "RL"):
            assert Direction[name] is not None

    def test_node_shape_has_exactly_14_members(self):
        assert len(NodeShape) == 14

    def test_node_shape_members(self):
        expected = {
            "rect",
            "rounded",
            "stadium",
            "subroutine",
            "cylinder",
            "circle",
            "asymmetric",
            "diamond",
            "hexagon",
            "parallelogram",
            "parallelogram_alt",
            "trapezoid",
            "trapezoid_alt",
            "double_circle",
        }
        assert {m.name for m in NodeShape} == expected

    def test_edge_type_has_exactly_7_members(self):
        assert len(EdgeType) == 7

    def test_edge_type_members(self):
        for name in (
            "arrow",
            "open",
            "dotted",
            "dotted_arrow",
            "thick",
            "thick_arrow",
            "invisible",
        ):
            assert EdgeType[name] is not None

    def test_arrow_type_has_exactly_4_members(self):
        assert len(ArrowType) == 4

    def test_arrow_type_members(self):
        for name in ("none", "arrow", "circle", "cross"):
            assert ArrowType[name] is not None

    def test_enum_member_access_by_name(self):
        assert NodeShape.diamond == NodeShape["diamond"]
        assert EdgeType.dotted_arrow == EdgeType["dotted_arrow"]


# ---------- Node ----------


class TestNode:
    def test_node_all_fields(self):
        node = Node(
            id="A",
            label="Label A",
            shape=NodeShape.diamond,
            css_classes=("cls1", "cls2"),
            inline_style={"fill": "#f9f"},
        )
        assert node.id == "A"
        assert node.label == "Label A"
        assert node.shape == NodeShape.diamond
        assert node.css_classes == ("cls1", "cls2")
        assert node.inline_style == {"fill": "#f9f"}

    def test_node_defaults(self):
        node = Node("A", "Label A")
        assert node.shape == NodeShape.rect
        assert node.css_classes == ()
        assert node.inline_style is None

    def test_node_is_frozen(self):
        node = Node("A", "Label A")
        with pytest.raises(dataclasses.FrozenInstanceError):
            node.label = "X"  # type: ignore[misc]

    def test_node_equality(self):
        a = Node("A", "Label")
        b = Node("A", "Label")
        assert a == b

    def test_node_hashable(self):
        a = Node("A", "Label")
        b = Node("B", "Other")
        s = {a, b}
        assert len(s) == 2
        assert a in s


# ---------- Edge ----------


class TestEdge:
    def test_edge_all_fields(self):
        edge = Edge(
            source="A",
            target="B",
            label="goes to",
            edge_type=EdgeType.dotted_arrow,
            source_arrow=ArrowType.circle,
            target_arrow=ArrowType.cross,
            extra_length=2,
        )
        assert edge.source == "A"
        assert edge.target == "B"
        assert edge.label == "goes to"
        assert edge.edge_type == EdgeType.dotted_arrow
        assert edge.source_arrow == ArrowType.circle
        assert edge.target_arrow == ArrowType.cross
        assert edge.extra_length == 2

    def test_edge_defaults(self):
        edge = Edge("A", "B")
        assert edge.label is None
        assert edge.edge_type == EdgeType.arrow
        assert edge.source_arrow == ArrowType.none
        assert edge.target_arrow == ArrowType.arrow
        assert edge.extra_length == 0

    def test_edge_is_frozen(self):
        edge = Edge("A", "B")
        with pytest.raises(dataclasses.FrozenInstanceError):
            edge.label = "X"  # type: ignore[misc]

    def test_edge_extra_length(self):
        edge = Edge("A", "B", extra_length=3)
        assert edge.extra_length == 3

    def test_edge_equality(self):
        a = Edge("A", "B", label="x")
        b = Edge("A", "B", label="x")
        assert a == b

    def test_edge_hashable(self):
        a = Edge("A", "B")
        b = Edge("C", "D")
        s = {a, b}
        assert len(s) == 2


# ---------- Subgraph ----------


class TestSubgraph:
    def test_subgraph_flat(self):
        sg = Subgraph("sg1", title="My Group", node_ids=("A", "B", "C"))
        assert sg.id == "sg1"
        assert sg.title == "My Group"
        assert sg.node_ids == ("A", "B", "C")
        assert sg.subgraphs == ()
        assert sg.direction is None

    def test_subgraph_nested(self):
        inner = Subgraph("inner", node_ids=("X",))
        outer = Subgraph("outer", subgraphs=(inner,))
        assert len(outer.subgraphs) == 1
        assert outer.subgraphs[0].id == "inner"

    def test_subgraph_self_referencing_nesting(self):
        sg = Subgraph("outer", subgraphs=(Subgraph("inner"),))
        assert sg.subgraphs[0].id == "inner"

    def test_subgraph_direction_override(self):
        sg = Subgraph("sg1", direction=Direction.LR)
        assert sg.direction == Direction.LR

    def test_subgraph_is_frozen(self):
        sg = Subgraph("sg1")
        with pytest.raises(dataclasses.FrozenInstanceError):
            sg.title = "X"  # type: ignore[misc]

    def test_subgraph_hashable(self):
        sg = Subgraph("sg1")
        s = {sg}
        assert sg in s


# ---------- StyleDef ----------


class TestStyleDef:
    def test_styledef_construction(self):
        sd = StyleDef(target_id="A", properties={"fill": "#f9f", "stroke": "#333"})
        assert sd.target_id == "A"
        assert sd.properties == {"fill": "#f9f", "stroke": "#333"}

    def test_styledef_default_properties(self):
        sd = StyleDef(target_id="default")
        assert sd.properties == {}

    def test_styledef_is_frozen(self):
        sd = StyleDef(target_id="A", properties={"fill": "red"})
        with pytest.raises(dataclasses.FrozenInstanceError):
            sd.target_id = "B"  # type: ignore[misc]


# ---------- Diagram ----------


class TestDiagram:
    def test_empty_diagram_defaults(self):
        d = Diagram()
        assert d.type == DiagramType.flowchart
        assert d.direction == Direction.TB
        assert d.nodes == ()
        assert d.edges == ()
        assert d.subgraphs == ()
        assert d.styles == ()
        assert d.classes == {}

    def test_diagram_with_content(self):
        d = Diagram(
            type=DiagramType.sequence,
            direction=Direction.LR,
            nodes=(Node("A", "Hello"), Node("B", "World")),
            edges=(Edge("A", "B"),),
            subgraphs=(Subgraph("sg1", node_ids=("A",)),),
            styles=(StyleDef("A", {"fill": "red"}),),
            classes={"highlight": {"fill": "#ff0", "stroke": "#000"}},
        )
        assert d.type == DiagramType.sequence
        assert d.direction == Direction.LR
        assert len(d.nodes) == 2
        assert len(d.edges) == 1
        assert len(d.subgraphs) == 1
        assert len(d.styles) == 1
        assert "highlight" in d.classes

    def test_diagram_nodes_and_edges(self):
        d = Diagram(nodes=(Node("A", "Hello"),), edges=(Edge("A", "B"),))
        assert d.nodes[0].id == "A"
        assert d.edges[0].source == "A"
        assert d.edges[0].target == "B"

    def test_diagram_is_frozen(self):
        d = Diagram()
        with pytest.raises(dataclasses.FrozenInstanceError):
            d.direction = Direction.LR  # type: ignore[misc]

    def test_diagram_all_directions(self):
        for direction in Direction:
            d = Diagram(direction=direction)
            assert d.direction == direction

    def test_diagram_hashable(self):
        d = Diagram()
        s = {d}
        assert d in s
