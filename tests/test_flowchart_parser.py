"""Tests for the flowchart parser.

At least 50 test cases covering diagram declarations, node shapes, edge types,
edge labels, inline node definitions, chained/multi-target edges, subgraphs,
styling, comments/special characters, and error handling.
"""

import pytest

from merm.ir import (
    ArrowType,
    DiagramType,
    Direction,
    EdgeType,
    NodeShape,
)
from merm.parser import ParseError, parse_flowchart

# ---------- Diagram declaration ----------

class TestDiagramDeclaration:
    def test_graph_td(self):
        d = parse_flowchart("graph TD\n  A --> B")
        assert d.direction == Direction.TD

    def test_graph_lr(self):
        d = parse_flowchart("graph LR\n  A --> B")
        assert d.direction == Direction.LR

    def test_flowchart_bt(self):
        d = parse_flowchart("flowchart BT\n  A --> B")
        assert d.direction == Direction.BT

    def test_flowchart_rl(self):
        d = parse_flowchart("flowchart RL\n  A --> B")
        assert d.direction == Direction.RL

    def test_tb_synonym_for_td(self):
        d = parse_flowchart("graph TB\n  A --> B")
        assert d.direction == Direction.TD

    def test_missing_direction_defaults_to_tb(self):
        d = parse_flowchart("graph\n  A --> B")
        assert d.direction == Direction.TB

    def test_diagram_type_is_flowchart(self):
        d = parse_flowchart("graph TD\n  A --> B")
        assert d.type == DiagramType.flowchart

# ---------- Node shapes (15 tests) ----------

class TestNodeShapes:
    def _node(self, node_text: str):
        d = parse_flowchart(f"graph TD\n  {node_text}")
        return d.nodes[0]

    def test_bare_id(self):
        n = self._node("A")
        assert n.shape == NodeShape.rect
        assert n.label == "A"

    def test_rect(self):
        n = self._node("A[text]")
        assert n.shape == NodeShape.rect
        assert n.label == "text"

    def test_rounded(self):
        n = self._node('A("text")')
        assert n.shape == NodeShape.rounded
        assert n.label == "text"

    def test_stadium(self):
        n = self._node('A(["text"])')
        assert n.shape == NodeShape.stadium
        assert n.label == "text"

    def test_subroutine(self):
        n = self._node('A[["text"]]')
        assert n.shape == NodeShape.subroutine
        assert n.label == "text"

    def test_cylinder(self):
        n = self._node('A[("text")]')
        assert n.shape == NodeShape.cylinder
        assert n.label == "text"

    def test_circle(self):
        n = self._node('A(("text"))')
        assert n.shape == NodeShape.circle
        assert n.label == "text"

    def test_asymmetric(self):
        n = self._node("A)text(")
        assert n.shape == NodeShape.asymmetric
        assert n.label == "text"

    def test_diamond(self):
        n = self._node('A{"text"}')
        assert n.shape == NodeShape.diamond
        assert n.label == "text"

    def test_hexagon(self):
        n = self._node('A{{"text"}}')
        assert n.shape == NodeShape.hexagon
        assert n.label == "text"

    def test_parallelogram(self):
        n = self._node('A[/"text"/]')
        assert n.shape == NodeShape.parallelogram
        assert n.label == "text"

    def test_parallelogram_alt(self):
        n = self._node('A[\\"text"\\]')
        assert n.shape == NodeShape.parallelogram_alt
        assert n.label == "text"

    def test_trapezoid(self):
        n = self._node('A[/"text"\\]')
        assert n.shape == NodeShape.trapezoid
        assert n.label == "text"

    def test_trapezoid_alt(self):
        n = self._node('A[\\"text"/]')
        assert n.shape == NodeShape.trapezoid_alt
        assert n.label == "text"

    def test_double_circle(self):
        n = self._node('A((("text")))')
        assert n.shape == NodeShape.double_circle
        assert n.label == "text"

# ---------- Edge types (11 tests) ----------

class TestEdgeTypes:
    def _edge(self, edge_text: str):
        d = parse_flowchart(f"graph TD\n  {edge_text}")
        return d.edges[0]

    def test_arrow(self):
        e = self._edge("A --> B")
        assert e.edge_type == EdgeType.arrow
        assert e.target_arrow == ArrowType.arrow
        assert e.source_arrow == ArrowType.none

    def test_open(self):
        e = self._edge("A --- B")
        assert e.edge_type == EdgeType.open
        assert e.target_arrow == ArrowType.none

    def test_dotted_arrow(self):
        e = self._edge("A -.-> B")
        assert e.edge_type == EdgeType.dotted_arrow
        assert e.target_arrow == ArrowType.arrow

    def test_dotted(self):
        e = self._edge("A -.- B")
        assert e.edge_type == EdgeType.dotted
        assert e.target_arrow == ArrowType.none

    def test_thick_arrow(self):
        e = self._edge("A ==> B")
        assert e.edge_type == EdgeType.thick_arrow
        assert e.target_arrow == ArrowType.arrow

    def test_thick(self):
        e = self._edge("A === B")
        assert e.edge_type == EdgeType.thick
        assert e.target_arrow == ArrowType.none

    def test_invisible(self):
        e = self._edge("A ~~~ B")
        assert e.edge_type == EdgeType.invisible
        assert e.target_arrow == ArrowType.none

    def test_circle_end(self):
        e = self._edge("A --o B")
        assert e.target_arrow == ArrowType.circle

    def test_cross_end(self):
        e = self._edge("A --x B")
        assert e.target_arrow == ArrowType.cross

    def test_bidirectional(self):
        e = self._edge("A <--> B")
        assert e.source_arrow == ArrowType.arrow
        assert e.target_arrow == ArrowType.arrow

    def test_extra_length(self):
        e = self._edge("A ----> B")
        assert e.extra_length == 2

# ---------- Edge labels ----------

class TestEdgeLabels:
    def test_pipe_syntax(self):
        d = parse_flowchart("graph TD\n  A -->|some label| B")
        assert d.edges[0].label == "some label"

    def test_inline_syntax(self):
        d = parse_flowchart("graph TD\n  A -- some label --> B")
        assert d.edges[0].label == "some label"

    def test_dotted_label(self):
        d = parse_flowchart("graph TD\n  A -. label .-> B")
        assert d.edges[0].label == "label"
        assert d.edges[0].edge_type == EdgeType.dotted_arrow

    def test_thick_label(self):
        d = parse_flowchart("graph TD\n  A == label ==> B")
        assert d.edges[0].label == "label"
        assert d.edges[0].edge_type == EdgeType.thick_arrow

    def test_empty_pipe_label(self):
        d = parse_flowchart("graph TD\n  A -->|| B")
        assert d.edges[0].label == ""

# ---------- Inline node definitions ----------

class TestInlineNodeDefinitions:
    def test_both_nodes_with_labels(self):
        d = parse_flowchart("graph TD\n  A[Start] --> B[End]")
        nodes = {n.id: n for n in d.nodes}
        assert nodes["A"].label == "Start"
        assert nodes["B"].label == "End"
        assert d.edges[0].source == "A"
        assert d.edges[0].target == "B"

    def test_one_labeled_one_bare(self):
        d = parse_flowchart("graph TD\n  A[Start] --> B")
        nodes = {n.id: n for n in d.nodes}
        assert nodes["A"].label == "Start"
        assert nodes["B"].label == "B"

    def test_redefinition_second_label_wins(self):
        d = parse_flowchart("graph TD\n  A[First]\n  A[Second]")
        nodes = {n.id: n for n in d.nodes}
        assert nodes["A"].label == "Second"

# ---------- Chained edges ----------

class TestChainedEdges:
    def test_two_chained(self):
        d = parse_flowchart("graph TD\n  A --> B --> C")
        assert len(d.edges) == 2
        assert d.edges[0].source == "A"
        assert d.edges[0].target == "B"
        assert d.edges[1].source == "B"
        assert d.edges[1].target == "C"

    def test_three_chained(self):
        d = parse_flowchart("graph TD\n  A --> B --> C --> D")
        assert len(d.edges) == 3

    def test_chained_with_labels(self):
        d = parse_flowchart("graph TD\n  A -->|yes| B -->|no| C")
        assert d.edges[0].label == "yes"
        assert d.edges[1].label == "no"

# ---------- Multi-target edges ----------

class TestMultiTargetEdges:
    def test_one_to_many(self):
        d = parse_flowchart("graph TD\n  A --> B & C")
        assert len(d.edges) == 2
        sources = {e.source for e in d.edges}
        targets = {e.target for e in d.edges}
        assert sources == {"A"}
        assert targets == {"B", "C"}

    def test_many_to_one(self):
        d = parse_flowchart("graph TD\n  A & B --> C")
        assert len(d.edges) == 2
        sources = {e.source for e in d.edges}
        targets = {e.target for e in d.edges}
        assert sources == {"A", "B"}
        assert targets == {"C"}

    def test_many_to_many(self):
        d = parse_flowchart("graph TD\n  A & B --> C & D")
        assert len(d.edges) == 4
        edge_pairs = {(e.source, e.target) for e in d.edges}
        assert edge_pairs == {("A", "C"), ("A", "D"), ("B", "C"), ("B", "D")}

# ---------- Subgraphs ----------

class TestSubgraphs:
    def test_simple_subgraph_with_title(self):
        d = parse_flowchart("graph TD\n  subgraph sg1[Title]\n    A --> B\n  end")
        assert len(d.subgraphs) == 1
        sg = d.subgraphs[0]
        assert sg.id == "sg1"
        assert sg.title == "Title"
        assert "A" in sg.node_ids
        assert "B" in sg.node_ids

    def test_subgraph_without_title(self):
        d = parse_flowchart("graph TD\n  subgraph sg1\n    A\n  end")
        sg = d.subgraphs[0]
        assert sg.id == "sg1"
        assert sg.title is None

    def test_nested_subgraph(self):
        text = (
            "graph TD\n  subgraph outer\n"
            "    subgraph inner\n      A --> B\n    end\n  end"
        )
        d = parse_flowchart(text)
        assert len(d.subgraphs) == 1
        outer = d.subgraphs[0]
        assert outer.id == "outer"
        assert len(outer.subgraphs) == 1
        inner = outer.subgraphs[0]
        assert inner.id == "inner"

    def test_direction_override(self):
        text = "graph TD\n  subgraph sg1\n    direction LR\n    A --> B\n  end"
        d = parse_flowchart(text)
        assert d.subgraphs[0].direction == Direction.LR

    def test_edge_inside_to_outside(self):
        text = "graph TD\n  subgraph sg1\n    A\n  end\n  A --> B"
        d = parse_flowchart(text)
        assert len(d.edges) == 1
        assert d.edges[0].source == "A"
        assert d.edges[0].target == "B"

    def test_edge_between_subgraphs(self):
        text = (
            "graph TD\n"
            "  subgraph sg1\n    A\n  end\n"
            "  subgraph sg2\n    B\n  end\n"
            "  A --> B"
        )
        d = parse_flowchart(text)
        assert len(d.edges) == 1

# ---------- Styling ----------

class TestStyling:
    def test_style_directive(self):
        d = parse_flowchart("graph TD\n  A --> B\n  style A fill:#f9f,stroke:#333")
        assert len(d.styles) == 1
        assert d.styles[0].target_id == "A"
        assert d.styles[0].properties == {"fill": "#f9f", "stroke": "#333"}

    def test_classdef(self):
        d = parse_flowchart("graph TD\n  A --> B\n  classDef red fill:#f9f,stroke:#333")
        assert "red" in d.classes
        assert d.classes["red"] == {"fill": "#f9f", "stroke": "#333"}

    def test_class_assignment(self):
        d = parse_flowchart("graph TD\n  A --> B\n  class A,B red")
        nodes = {n.id: n for n in d.nodes}
        assert "red" in nodes["A"].css_classes
        assert "red" in nodes["B"].css_classes

    def test_inline_class_syntax(self):
        d = parse_flowchart("graph TD\n  A:::myClass --> B")
        nodes = {n.id: n for n in d.nodes}
        assert "myClass" in nodes["A"].css_classes

    def test_classdef_default(self):
        d = parse_flowchart("graph TD\n  A\n  classDef default fill:#f9f")
        assert "default" in d.classes

# ---------- Comments and special characters ----------

class TestCommentsAndSpecialChars:
    def test_full_line_comment(self):
        d = parse_flowchart("graph TD\n  %% this is a comment\n  A --> B")
        assert len(d.edges) == 1

    def test_inline_comment(self):
        d = parse_flowchart("graph TD\n  A --> B %% comment")
        assert len(d.edges) == 1

    def test_semicolon_separator(self):
        d = parse_flowchart("graph TD\n  A --> B; C --> D")
        assert len(d.edges) == 2

    def test_entity_code_hash(self):
        d = parse_flowchart('graph TD\n  A["text #35; here"]')
        assert d.nodes[0].label == "text # here"

    def test_br_tag_preserved(self):
        d = parse_flowchart('graph TD\n  A["line1<br/>line2"]')
        assert "<br/>" in d.nodes[0].label

    def test_quoted_label_with_special_chars(self):
        d = parse_flowchart('graph TD\n  A["(special)"]')
        assert d.nodes[0].label == "(special)"

# ---------- Error handling ----------

class TestErrorHandling:
    def test_incomplete_edge(self):
        with pytest.raises(ParseError) as exc_info:
            parse_flowchart("graph TD\n  A -->")
        assert "2" in str(exc_info.value)

    def test_unclosed_subgraph(self):
        with pytest.raises(ParseError):
            parse_flowchart("graph TD\n  subgraph sg1\n    A --> B")

    def test_unknown_keyword(self):
        with pytest.raises(ParseError):
            parse_flowchart("chart TD\n  A --> B")

    def test_empty_input(self):
        with pytest.raises(ParseError):
            parse_flowchart("")

# ---------- Integration: multi-statement diagrams ----------

class TestIntegration:
    def test_complete_flowchart(self):
        text = """\
graph LR
  A[Start] --> B{Decision}
  B -->|yes| C[OK]
  B -->|no| D[Fail]
  subgraph results[Results]
    C
    D
  end
  style A fill:#9f9
  classDef highlight fill:#ff0
  class C highlight
"""
        d = parse_flowchart(text)
        assert d.direction == Direction.LR
        nodes = {n.id: n for n in d.nodes}
        assert nodes["A"].shape == NodeShape.rect
        assert nodes["A"].label == "Start"
        assert nodes["B"].shape == NodeShape.diamond
        assert nodes["B"].label == "Decision"
        assert len(d.edges) == 3
        assert d.subgraphs[0].id == "results"
        assert len(d.styles) == 1
        assert "highlight" in d.classes
        assert "highlight" in nodes["C"].css_classes

    def test_all_node_shapes(self):
        text = """\
graph TD
  A[rect]
  B("rounded")
  C(["stadium"])
  D[["subroutine"]]
  E[("cylinder")]
  F(("circle"))
  G)asymmetric(
  H{"diamond"}
  I{{"hexagon"}}
  J[/"para"/]
  K[\\"para_alt"\\]
  L[/"trap"\\]
  M[\\"trap_alt"/]
  N((("double")))
"""
        d = parse_flowchart(text)
        shapes = {n.id: n.shape for n in d.nodes}
        assert shapes["A"] == NodeShape.rect
        assert shapes["B"] == NodeShape.rounded
        assert shapes["C"] == NodeShape.stadium
        assert shapes["D"] == NodeShape.subroutine
        assert shapes["E"] == NodeShape.cylinder
        assert shapes["F"] == NodeShape.circle
        assert shapes["G"] == NodeShape.asymmetric
        assert shapes["H"] == NodeShape.diamond
        assert shapes["I"] == NodeShape.hexagon
        assert shapes["J"] == NodeShape.parallelogram
        assert shapes["K"] == NodeShape.parallelogram_alt
        assert shapes["L"] == NodeShape.trapezoid
        assert shapes["M"] == NodeShape.trapezoid_alt
        assert shapes["N"] == NodeShape.double_circle

    def test_all_edge_types(self):
        text = """\
graph TD
  A --> B
  B --- C
  C -.-> D
  D -.- E
  E ==> F
  F === G
  G ~~~ H
  H --o I
  I --x J
  J <--> K
"""
        d = parse_flowchart(text)
        edge_types = [e.edge_type for e in d.edges]
        assert EdgeType.arrow in edge_types
        assert EdgeType.open in edge_types
        assert EdgeType.dotted_arrow in edge_types
        assert EdgeType.dotted in edge_types
        assert EdgeType.thick_arrow in edge_types
        assert EdgeType.thick in edge_types
        assert EdgeType.invisible in edge_types

    def test_click_ignored(self):
        text = "graph TD\n  A --> B\n  click A href \"http://example.com\""
        d = parse_flowchart(text)
        assert len(d.edges) == 1

    def test_multiple_semicolons(self):
        d = parse_flowchart("graph TD\n  A --> B; B --> C; C --> D")
        assert len(d.edges) == 3

    def test_entity_code_numeric(self):
        d = parse_flowchart('graph TD\n  A["#38; ampersand"]')
        assert d.nodes[0].label == "& ampersand"
