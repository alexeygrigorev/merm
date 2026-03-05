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
    def test_edge_is_frozen(self):
        edge = Edge("A", "B")
        with pytest.raises(dataclasses.FrozenInstanceError):
            edge.label = "X"  # type: ignore[misc]

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
    def test_subgraph_nested(self):
        inner = Subgraph("inner", node_ids=("X",))
        outer = Subgraph("outer", subgraphs=(inner,))
        assert len(outer.subgraphs) == 1
        assert outer.subgraphs[0].id == "inner"

    def test_subgraph_self_referencing_nesting(self):
        sg = Subgraph("outer", subgraphs=(Subgraph("inner"),))
        assert sg.subgraphs[0].id == "inner"

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
    def test_styledef_is_frozen(self):
        sd = StyleDef(target_id="A", properties={"fill": "red"})
        with pytest.raises(dataclasses.FrozenInstanceError):
            sd.target_id = "B"  # type: ignore[misc]

# ---------- Diagram ----------

class TestDiagram:
    def test_diagram_is_frozen(self):
        d = Diagram()
        with pytest.raises(dataclasses.FrozenInstanceError):
            d.direction = Direction.LR  # type: ignore[misc]

    def test_diagram_hashable(self):
        d = Diagram()
        s = {d}
        assert d in s
