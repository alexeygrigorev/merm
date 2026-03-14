"""Targeted mutant-killing tests for the flowchart parser.

These tests exercise specific boundary conditions, edge cases, and code
paths in src/merm/parser/flowchart.py that mutmut identifies as under-tested.

Baseline mutation score: 807/1086 killed = 74.3%  (+ 19 timeouts)
Target: improve by at least 3 percentage points (to ~77.3%+)

Each test docstring documents the specific mutation it kills.
"""

import pytest

from merm.ir import (
    ArrowType,
    Direction,
    EdgeType,
    NodeShape,
)
from merm.parser.flowchart import (
    ParseError,
    _decode_entities,
    _find_delimiter,
    _parse_edge_operator,
    _parse_node_def,
    _parse_style_props,
    _split_ampersand,
    _split_semicolons,
    _strip_comment,
    _unquote,
    _valid_id,
    parse_flowchart,
)

# ---------------------------------------------------------------------------
# _decode_entities: HTML and Mermaid entity code decoding
# ---------------------------------------------------------------------------


@pytest.mark.mutation
class TestDecodeEntitiesMutants:
    """Kill mutants in _decode_entities that remove html.unescape or _ENTITY_RE.sub."""

    def test_html_entity_amp(self):
        """Kills mutant that removes html.unescape call."""
        assert _decode_entities("&amp;") == "&"

    def test_html_entity_lt(self):
        """Kills mutant that removes html.unescape call."""
        assert _decode_entities("&lt;") == "<"

    def test_mermaid_entity_hash(self):
        """Kills mutant that removes _ENTITY_RE.sub call -- #35; is '#'."""
        assert _decode_entities("#35;") == "#"

    def test_mermaid_entity_space(self):
        """Kills mutant that changes int() conversion or chr() call in sub lambda."""
        assert _decode_entities("#32;") == " "

    def test_passthrough_plain_text(self):
        """Kills mutant that replaces return value with empty string."""
        assert _decode_entities("hello") == "hello"

    def test_combined_html_and_mermaid(self):
        """Kills mutant that reorders html.unescape and Mermaid decoding."""
        # &#38; is HTML for & -- html.unescape must run first to avoid
        # the Mermaid regex matching inside &#38;
        result = _decode_entities("&#38;")
        assert result == "&"


# ---------------------------------------------------------------------------
# _strip_comment: comment removal respecting quotes
# ---------------------------------------------------------------------------


@pytest.mark.mutation
class TestStripCommentMutants:
    """Kill mutants in _strip_comment that alter quote or %% detection."""

    def test_comment_removed(self):
        """Kills mutant that removes the return line[:i].rstrip() branch."""
        assert _strip_comment("A --> B %% comment") == "A --> B"

    def test_no_comment_passthrough(self):
        """Kills mutant that always returns empty string."""
        assert _strip_comment("A --> B") == "A --> B"

    def test_percent_inside_double_quotes(self):
        """Kills mutant that removes double-quote tracking (in_quote)."""
        result = _strip_comment('A["has %% inside"]')
        assert "%%" in result

    def test_percent_inside_single_quotes(self):
        """Kills mutant that removes single-quote handling."""
        result = _strip_comment("A['has %% inside']")
        assert "%%" in result

    def test_single_percent_not_comment(self):
        """Kills mutant that changes i + 1 < len(line) to i + 1 <= len(line)."""
        assert _strip_comment("50%") == "50%"

    def test_comment_at_start(self):
        """Kills mutant that changes return line[:i] to line[:i+1]."""
        result = _strip_comment("%% full line comment")
        assert result == ""


# ---------------------------------------------------------------------------
# _split_semicolons: splitting on unquoted/unbracketed semicolons
# ---------------------------------------------------------------------------


@pytest.mark.mutation
class TestSplitSemicolonsMutants:
    """Kill mutants in _split_semicolons that alter depth or quote tracking."""

    def test_basic_split(self):
        """Kills mutant that removes the semicolon check."""
        assert _split_semicolons("A;B") == ["A", "B"]

    def test_no_split(self):
        """Kills mutant that always splits."""
        assert _split_semicolons("A --> B") == ["A --> B"]

    def test_semicolon_inside_brackets(self):
        """Kills mutant that removes depth tracking for brackets."""
        result = _split_semicolons("A[text;more]")
        assert len(result) == 1
        assert "text;more" in result[0]

    def test_semicolon_inside_parens(self):
        """Kills mutant that removes paren tracking from depth."""
        result = _split_semicolons("A(text;more)")
        assert len(result) == 1

    def test_semicolon_inside_braces(self):
        """Kills mutant that removes brace tracking from depth."""
        result = _split_semicolons("A{text;more}")
        assert len(result) == 1

    def test_semicolon_inside_quotes(self):
        """Kills mutant that removes in_quote tracking."""
        result = _split_semicolons('"a;b"')
        assert len(result) == 1

    def test_depth_increment_opening(self):
        """Kills mutant that changes depth += 1 to depth -= 1."""
        result = _split_semicolons("([;])")
        assert len(result) == 1  # semicolon is at depth > 0

    def test_depth_decrement_closing(self):
        """Kills mutant that changes depth -= 1 to depth += 1."""
        result = _split_semicolons("[a];B")
        assert len(result) == 2  # after ] depth is back to 0


# ---------------------------------------------------------------------------
# _valid_id: node ID validation
# ---------------------------------------------------------------------------


@pytest.mark.mutation
class TestValidIdMutants:
    """Kill mutants that alter _valid_id's regex or empty-check."""

    def test_empty_string_invalid(self):
        """Kills mutant that removes bool(s) check."""
        assert _valid_id("") is False

    def test_simple_alpha(self):
        """Kills mutant that changes regex to never match."""
        assert _valid_id("abc") is True

    def test_starts_with_digit(self):
        """Kills mutant that changes [A-Za-z_\\d] to [A-Za-z_] (no digit start)."""
        assert _valid_id("1abc") is True

    def test_underscore_start(self):
        """Kills mutant that removes _ from character class."""
        assert _valid_id("_node") is True

    def test_special_char_invalid(self):
        """Kills mutant that makes regex too permissive."""
        assert _valid_id("a-b") is False

    def test_space_invalid(self):
        """Kills mutant that makes regex too permissive."""
        assert _valid_id("a b") is False


# ---------------------------------------------------------------------------
# _unquote: remove surrounding double quotes
# ---------------------------------------------------------------------------


@pytest.mark.mutation
class TestUnquoteMutants:
    """Kill mutants in _unquote boundary checks."""

    def test_quoted(self):
        """Kills mutant that removes the s[1:-1] return."""
        assert _unquote('"hello"') == "hello"

    def test_unquoted(self):
        """Kills mutant that always strips quotes."""
        assert _unquote("hello") == "hello"

    def test_single_char(self):
        """Kills mutant that changes len(s) >= 2 to len(s) >= 1."""
        assert _unquote('"') == '"'

    def test_empty(self):
        """Kills mutant that changes len(s) >= 2 to len(s) >= 0."""
        assert _unquote("") == ""

    def test_only_opening_quote(self):
        """Kills mutant that removes s[-1] == '\"' check."""
        assert _unquote('"hello') == '"hello'

    def test_only_closing_quote(self):
        """Kills mutant that removes s[0] == '\"' check."""
        assert _unquote('hello"') == 'hello"'


# ---------------------------------------------------------------------------
# _find_delimiter: locating opening delimiter after ID
# ---------------------------------------------------------------------------


@pytest.mark.mutation
class TestFindDelimiterMutants:
    """Kill mutants in _find_delimiter loop and return."""

    def test_finds_bracket(self):
        """Kills mutant that always returns None."""
        assert _find_delimiter("abc[", "[") == 3

    def test_finds_paren(self):
        """Kills mutant that changes startswith check."""
        assert _find_delimiter("node(", "(") == 4

    def test_no_delimiter(self):
        """Kills mutant that returns 0 instead of None."""
        assert _find_delimiter("abc", "[") is None

    def test_delimiter_at_start(self):
        """Kills mutant that changes while condition boundary."""
        assert _find_delimiter("[text]", "[") == 0

    def test_underscore_in_id(self):
        """Kills mutant removing '_' from id character check."""
        assert _find_delimiter("a_b[text]", "[") == 3

    def test_digit_in_id(self):
        """Kills mutant removing isalnum() call."""
        assert _find_delimiter("node1[text]", "[") == 5


# ---------------------------------------------------------------------------
# _parse_edge_operator: edge type and extra_length calculations
# ---------------------------------------------------------------------------


@pytest.mark.mutation
class TestParseEdgeOperatorMutants:
    """Kill mutants in _parse_edge_operator's type classification and arithmetic."""

    def test_normal_arrow_basic(self):
        """Kills mutant that changes EdgeType.arrow to another type."""
        info = _parse_edge_operator("-->")
        assert info.edge_type == EdgeType.arrow
        assert info.target_arrow == ArrowType.arrow
        assert info.extra_length == 0

    def test_normal_arrow_extra_length(self):
        """Kills mutant that changes len(body) - 2 to len(body) - 3."""
        info = _parse_edge_operator("--->")
        assert info.extra_length == 1

    def test_normal_arrow_extra_length_2(self):
        """Kills mutant that changes base_len = 2 to base_len = 3."""
        info = _parse_edge_operator("---->")
        assert info.extra_length == 2

    def test_open_link(self):
        """Kills mutant that changes EdgeType.open to EdgeType.arrow."""
        info = _parse_edge_operator("---")
        assert info.edge_type == EdgeType.open
        assert info.target_arrow == ArrowType.none

    def test_circle_endpoint(self):
        """Kills mutant that changes ArrowType.circle to ArrowType.arrow."""
        info = _parse_edge_operator("--o")
        assert info.target_arrow == ArrowType.circle

    def test_cross_endpoint(self):
        """Kills mutant that changes ArrowType.cross to ArrowType.arrow."""
        info = _parse_edge_operator("--x")
        assert info.target_arrow == ArrowType.cross

    def test_dotted_arrow(self):
        """Kills mutant that changes EdgeType.dotted_arrow to EdgeType.dotted."""
        info = _parse_edge_operator("-.->")
        assert info.edge_type == EdgeType.dotted_arrow
        assert info.target_arrow == ArrowType.arrow

    def test_dotted_open(self):
        """Kills mutant that changes EdgeType.dotted to EdgeType.dotted_arrow."""
        info = _parse_edge_operator("-.-")
        assert info.edge_type == EdgeType.dotted
        assert info.target_arrow == ArrowType.none

    def test_dotted_extra_length(self):
        """Kills mutant that changes len(body) - 2 to len(body) - 1 in dotted."""
        info = _parse_edge_operator("-.->")
        assert info.extra_length == 0  # "-." is 2 chars, so 2-2=0
        info2 = _parse_edge_operator("-..->")
        assert info2.extra_length == 1  # "-.." is 3 chars, so 3-2=1

    def test_thick_arrow(self):
        """Kills mutant that changes EdgeType.thick_arrow to EdgeType.thick."""
        info = _parse_edge_operator("==>")
        assert info.edge_type == EdgeType.thick_arrow
        assert info.target_arrow == ArrowType.arrow

    def test_thick_open(self):
        """Kills mutant that changes EdgeType.thick to EdgeType.thick_arrow."""
        info = _parse_edge_operator("===")
        assert info.edge_type == EdgeType.thick
        assert info.target_arrow == ArrowType.none

    def test_thick_extra_length(self):
        """Kills mutant that changes len(body) - 2 arithmetic for thick."""
        info = _parse_edge_operator("==>")
        assert info.extra_length == 0  # "==" is 2, so 2-2=0
        info2 = _parse_edge_operator("===>")
        assert info2.extra_length == 1  # "===" is 3, so 3-2=1

    def test_invisible_extra_length_zero(self):
        """Kills mutant that changes len(invis) - 3 to len(invis) - 2."""
        info = _parse_edge_operator("~~~")
        assert info.extra_length == 0

    def test_invisible_extra_length_one(self):
        """Kills mutant that changes - 3 to + 3 in invisible extra calc."""
        info = _parse_edge_operator("~~~~")
        assert info.extra_length == 1

    def test_bidirectional_arrow(self):
        """Kills mutant that removes src_arrow detection."""
        info = _parse_edge_operator("<-->")
        assert info.source_arrow == ArrowType.arrow
        assert info.target_arrow == ArrowType.arrow

    def test_unidirectional_no_src_arrow(self):
        """Kills mutant that always sets src_arrow to arrow."""
        info = _parse_edge_operator("-->")
        assert info.source_arrow == ArrowType.none

    def test_invalid_operator_raises(self):
        """Kills mutant that removes ValueError raise."""
        with pytest.raises(ValueError):
            _parse_edge_operator("abc")


# ---------------------------------------------------------------------------
# _parse_node_def: node shape detection, ID validation
# ---------------------------------------------------------------------------


@pytest.mark.mutation
class TestParseNodeDefMutants:
    """Kill mutants in _parse_node_def shape matching and ID handling."""

    def test_rect_shape(self):
        """Kills mutant that changes NodeShape.rect default."""
        ndef = _parse_node_def("A[text]")
        assert ndef.shape == NodeShape.rect
        assert ndef.label == "text"

    def test_rounded_shape(self):
        """Kills mutant that changes NodeShape.rounded to NodeShape.rect."""
        ndef = _parse_node_def("A(text)")
        assert ndef.shape == NodeShape.rounded

    def test_stadium_shape(self):
        """Kills mutant that changes NodeShape.stadium to another shape."""
        ndef = _parse_node_def("A([text])")
        assert ndef.shape == NodeShape.stadium

    def test_circle_shape(self):
        """Kills mutant confusing circle and double_circle."""
        ndef = _parse_node_def("A((text))")
        assert ndef.shape == NodeShape.circle

    def test_double_circle_shape(self):
        """Kills mutant confusing double_circle and circle."""
        ndef = _parse_node_def("A(((text)))")
        assert ndef.shape == NodeShape.double_circle

    def test_diamond_shape(self):
        """Kills mutant confusing diamond and hexagon."""
        ndef = _parse_node_def("A{text}")
        assert ndef.shape == NodeShape.diamond

    def test_hexagon_shape(self):
        """Kills mutant confusing hexagon and diamond."""
        ndef = _parse_node_def("A{{text}}")
        assert ndef.shape == NodeShape.hexagon

    def test_subroutine_shape(self):
        """Kills mutant changing NodeShape.subroutine."""
        ndef = _parse_node_def("A[[text]]")
        assert ndef.shape == NodeShape.subroutine

    def test_cylinder_shape(self):
        """Kills mutant changing NodeShape.cylinder."""
        ndef = _parse_node_def("A[(text)]")
        assert ndef.shape == NodeShape.cylinder

    def test_bare_id_defaults_to_rect(self):
        """Kills mutant that changes default shape for bare IDs."""
        ndef = _parse_node_def("myNode")
        assert ndef.shape == NodeShape.rect
        assert ndef.label == "myNode"  # label equals id for bare nodes

    def test_css_class_extraction(self):
        """Kills mutant that removes :::class parsing."""
        ndef = _parse_node_def("A[text]:::highlight")
        assert "highlight" in ndef.css_classes

    def test_css_class_stripped_from_token(self):
        """Kills mutant that doesn't strip :::class from token before shape parse."""
        ndef = _parse_node_def("A[text]:::myClass")
        assert ndef.label == "text"
        assert ndef.shape == NodeShape.rect

    def test_quoted_label(self):
        """Kills mutant that removes _unquote call inside shape parsing."""
        ndef = _parse_node_def('A["quoted text"]')
        assert ndef.label == "quoted text"

    def test_entity_decoded_label(self):
        """Kills mutant that removes _decode_entities call."""
        ndef = _parse_node_def("A[text &amp; more]")
        assert "&" in ndef.label

    def test_invalid_token_raises(self):
        """Kills mutant that removes ValueError raise for unparseable tokens."""
        with pytest.raises(ValueError):
            _parse_node_def("!!!invalid!!!")


# ---------------------------------------------------------------------------
# _parse_style_props: CSS property parsing
# ---------------------------------------------------------------------------


@pytest.mark.mutation
class TestParseStylePropsMutants:
    """Kill mutants in _parse_style_props splitting logic."""

    def test_single_prop(self):
        """Kills mutant that removes colon splitting."""
        result = _parse_style_props("fill:#f9f")
        assert result == {"fill": "#f9f"}

    def test_multiple_props(self):
        """Kills mutant that removes comma splitting."""
        result = _parse_style_props("fill:#f9f,stroke:#333")
        assert result == {"fill": "#f9f", "stroke": "#333"}

    def test_no_colon_skipped(self):
        """Kills mutant that removes 'if colon in part' check."""
        result = _parse_style_props("fill:#f9f,badentry")
        assert "fill" in result
        assert len(result) == 1

    def test_whitespace_stripped(self):
        """Kills mutant that removes strip() calls."""
        result = _parse_style_props("fill : #f9f , stroke : #333")
        assert result["fill"] == "#f9f"
        assert result["stroke"] == "#333"


# ---------------------------------------------------------------------------
# _split_ampersand: multi-node group splitting
# ---------------------------------------------------------------------------


@pytest.mark.mutation
class TestSplitAmpersandMutants:
    """Kill mutants in _split_ampersand depth and quote tracking."""

    def test_basic_split(self):
        """Kills mutant that removes & check."""
        assert _split_ampersand("A & B") == ["A", "B"]

    def test_no_ampersand(self):
        """Kills mutant that always splits."""
        assert _split_ampersand("A") == ["A"]

    def test_ampersand_inside_brackets(self):
        """Kills mutant that removes depth tracking."""
        result = _split_ampersand("A[a & b]")
        assert len(result) == 1

    def test_ampersand_inside_quotes(self):
        """Kills mutant that removes in_quote tracking."""
        result = _split_ampersand('"a & b"')
        assert len(result) == 1

    def test_multiple_targets(self):
        """Kills mutant that only splits once."""
        result = _split_ampersand("A & B & C")
        assert len(result) == 3

    def test_empty_parts_skipped(self):
        """Kills mutant that includes empty strings in result."""
        result = _split_ampersand("A &")
        # trailing empty part should be skipped because of `if rest:` check
        assert result == ["A"]


# ---------------------------------------------------------------------------
# Full parser: edge labels, style, classDef, class assignment
# ---------------------------------------------------------------------------


@pytest.mark.mutation
class TestParserEdgeLabelsMutants:
    """Kill mutants in _parse_edge_token label handling."""

    def test_pipe_label(self):
        """Kills mutant that removes pipe label extraction."""
        d = parse_flowchart("graph TD\n  A -->|yes| B\n")
        assert len(d.edges) == 1
        assert d.edges[0].label == "yes"

    def test_pipe_label_empty(self):
        """Kills mutant that changes empty label handling."""
        d = parse_flowchart("graph TD\n  A -->|| B\n")
        assert d.edges[0].label == ""

    def test_inline_label_normal(self):
        """Kills mutant that removes inline label reconstruction for --."""
        d = parse_flowchart("graph TD\n  A -- text --> B\n")
        assert d.edges[0].label == "text"
        assert d.edges[0].edge_type == EdgeType.arrow

    def test_inline_label_dotted(self):
        """Kills mutant that removes inline label reconstruction for dotted."""
        d = parse_flowchart("graph TD\n  A -. text .-> B\n")
        assert d.edges[0].label == "text"
        assert d.edges[0].edge_type == EdgeType.dotted_arrow

    def test_inline_label_thick(self):
        """Kills mutant that removes inline label reconstruction for thick."""
        d = parse_flowchart("graph TD\n  A == text ==> B\n")
        assert d.edges[0].label == "text"
        assert d.edges[0].edge_type == EdgeType.thick_arrow

    def test_label_with_special_chars(self):
        """Kills mutant that changes label extraction from pipe match group."""
        d = parse_flowchart("graph TD\n  A -->|label text| B\n")
        assert d.edges[0].label == "label text"
        assert d.edges[0].edge_type == EdgeType.arrow


@pytest.mark.mutation
class TestParserClassDefMutants:
    """Kill mutants in classDef and class assignment parsing."""

    def test_classdef_parsed(self):
        """Kills mutant that removes classDef matching."""
        d = parse_flowchart("graph TD\n  classDef red fill:#f00\n  A:::red\n")
        assert "red" in d.classes
        assert d.classes["red"]["fill"] == "#f00"

    def test_class_assignment(self):
        """Kills mutant that removes class assignment matching."""
        d = parse_flowchart("graph TD\n  A[text]\n  class A myStyle\n")
        nodes = {n.id: n for n in d.nodes}
        assert "myStyle" in nodes["A"].css_classes

    def test_class_assignment_creates_node(self):
        """Kills mutant that removes node creation in class assignment."""
        d = parse_flowchart("graph TD\n  class X myStyle\n")
        nodes = {n.id: n for n in d.nodes}
        assert "X" in nodes
        assert "myStyle" in nodes["X"].css_classes


@pytest.mark.mutation
class TestParserStyleDirectiveMutants:
    """Kill mutants in style directive parsing."""

    def test_style_directive(self):
        """Kills mutant that removes style matching."""
        d = parse_flowchart("graph TD\n  A[text]\n  style A fill:#f00\n")
        assert len(d.styles) >= 1
        style = [s for s in d.styles if s.target_id == "A"]
        assert len(style) == 1
        assert style[0].properties["fill"] == "#f00"


# ---------------------------------------------------------------------------
# Full parser: subgraph nesting and edge cases
# ---------------------------------------------------------------------------


@pytest.mark.mutation
class TestParserSubgraphNestingMutants:
    """Kill mutants in subgraph nesting logic."""

    def test_nested_subgraph(self):
        """Kills mutant that removes child_subgraphs.append in _handle_subgraph_end."""
        d = parse_flowchart(
            "graph TD\n"
            "  subgraph outer[Outer]\n"
            "    subgraph inner[Inner]\n"
            "      A --> B\n"
            "    end\n"
            "  end\n"
        )
        assert len(d.subgraphs) == 1
        assert d.subgraphs[0].id == "outer"
        assert len(d.subgraphs[0].subgraphs) == 1
        assert d.subgraphs[0].subgraphs[0].id == "inner"

    def test_unclosed_subgraph_raises(self):
        """Kills mutant that removes unclosed subgraph check."""
        with pytest.raises(ParseError):
            parse_flowchart(
                "graph TD\n"
                "  subgraph sg1[Title]\n"
                "    A --> B\n"
            )

    def test_end_without_subgraph_raises(self):
        """Kills mutant that removes 'end without subgraph' check."""
        with pytest.raises(ParseError):
            parse_flowchart("graph TD\n  A --> B\n  end\n")

    def test_subgraph_bare_title(self):
        """Kills mutant that removes bare-word title fallback."""
        d = parse_flowchart(
            "graph TD\n"
            "  subgraph sg1 My Title\n"
            "    A --> B\n"
            "  end\n"
        )
        sg = [s for s in d.subgraphs if s.id == "sg1"]
        assert len(sg) == 1
        assert sg[0].title == "My Title"

    def test_subgraph_no_title(self):
        """Kills mutant that always sets title to non-None."""
        d = parse_flowchart(
            "graph TD\n"
            "  subgraph sg1\n"
            "    A --> B\n"
            "  end\n"
        )
        sg = [s for s in d.subgraphs if s.id == "sg1"]
        assert len(sg) == 1
        assert sg[0].title is None


# ---------------------------------------------------------------------------
# Full parser: _register_node update logic
# ---------------------------------------------------------------------------


@pytest.mark.mutation
class TestRegisterNodeMutants:
    """Kill mutants in _register_node's existing-node update logic."""

    def test_later_definition_updates_shape(self):
        """Kills mutant that removes the shape/label update condition.
        When a node is first seen as bare 'A' then later as 'A[text]',
        the shape and label should update.
        """
        d = parse_flowchart("graph TD\n  A --> B\n  A[Updated]\n")
        nodes = {n.id: n for n in d.nodes}
        assert nodes["A"].label == "Updated"
        assert nodes["A"].shape == NodeShape.rect

    def test_bare_reference_does_not_overwrite(self):
        """Kills mutant that always overwrites label/shape.
        If node was defined as A[text] and later referenced as bare A,
        the original label/shape should be preserved.
        """
        d = parse_flowchart("graph TD\n  A[Original] --> B\n  A --> C\n")
        nodes = {n.id: n for n in d.nodes}
        assert nodes["A"].label == "Original"

    def test_node_registered_in_subgraph(self):
        """Kills mutant that removes subgraph node registration."""
        d = parse_flowchart(
            "graph TD\n"
            "  subgraph sg1[Group]\n"
            "    A --> B\n"
            "  end\n"
        )
        sg = [s for s in d.subgraphs if s.id == "sg1"]
        assert "A" in sg[0].node_ids
        assert "B" in sg[0].node_ids

    def test_node_not_duplicated_in_subgraph(self):
        """Kills mutant that removes 'if ndef.id not in sg.node_ids' check."""
        d = parse_flowchart(
            "graph TD\n"
            "  subgraph sg1[Group]\n"
            "    A --> B\n"
            "    A --> C\n"
            "  end\n"
        )
        sg = [s for s in d.subgraphs if s.id == "sg1"]
        # A should appear only once in node_ids
        assert sg[0].node_ids.count("A") == 1


# ---------------------------------------------------------------------------
# Full parser: declaration edge cases
# ---------------------------------------------------------------------------


@pytest.mark.mutation
class TestParserDeclarationMutants:
    """Kill mutants in _parse_declaration."""

    def test_case_insensitive_graph(self):
        """Kills mutant that removes re.IGNORECASE in declaration regex."""
        d = parse_flowchart("GRAPH TD\n  A --> B\n")
        assert d.direction == Direction.TD

    def test_case_insensitive_flowchart(self):
        """Kills mutant that removes re.IGNORECASE in declaration regex."""
        d = parse_flowchart("FLOWCHART LR\n  A --> B\n")
        assert d.direction == Direction.LR

    def test_invalid_declaration_raises(self):
        """Kills mutant that removes ParseError for bad declaration."""
        with pytest.raises(ParseError):
            parse_flowchart("diagram TD\n  A --> B\n")

    def test_direction_uppercased(self):
        """Kills mutant that removes .upper() on direction string."""
        d = parse_flowchart("graph td\n  A --> B\n")
        assert d.direction == Direction.TD

    def test_unknown_direction_raises(self):
        """Kills mutant that removes KeyError catch for Direction enum."""
        with pytest.raises(ParseError, match="Unknown direction"):
            parse_flowchart("graph XX\n  A --> B\n")


# ---------------------------------------------------------------------------
# Full parser: chained edges and multi-target
# ---------------------------------------------------------------------------


@pytest.mark.mutation
class TestParserChainedEdgeMutants:
    """Kill mutants in _parse_node_edge_statement chaining logic."""

    def test_chained_edges(self):
        """Kills mutant that changes range(0, len(tokens) - 2, 2) step."""
        d = parse_flowchart("graph TD\n  A --> B --> C\n")
        assert len(d.edges) == 2
        assert d.edges[0].source == "A"
        assert d.edges[0].target == "B"
        assert d.edges[1].source == "B"
        assert d.edges[1].target == "C"

    def test_multi_source_ampersand(self):
        """Kills mutant that removes _split_ampersand for sources."""
        d = parse_flowchart("graph TD\n  A & B --> C\n")
        assert len(d.edges) == 2
        sources = {e.source for e in d.edges}
        assert sources == {"A", "B"}

    def test_multi_target_ampersand(self):
        """Kills mutant that removes _split_ampersand for targets."""
        d = parse_flowchart("graph TD\n  A --> B & C\n")
        assert len(d.edges) == 2
        targets = {e.target for e in d.edges}
        assert targets == {"B", "C"}

    def test_single_node_no_edges(self):
        """Kills mutant that changes len(tokens) == 1 check."""
        d = parse_flowchart("graph TD\n  A[My Node]\n")
        assert len(d.nodes) == 1
        assert len(d.edges) == 0

    def test_incomplete_edge_raises(self):
        """Kills mutant that removes len(tokens) < 3 check."""
        with pytest.raises(ParseError):
            parse_flowchart("graph TD\n  A -->\n")


# ---------------------------------------------------------------------------
# Full parser: click directive ignored
# ---------------------------------------------------------------------------


@pytest.mark.mutation
class TestParserClickMutants:
    """Kill mutants that remove click directive handling."""

    def test_click_ignored(self):
        """Kills mutant that removes click directive early return."""
        d = parse_flowchart(
            "graph TD\n  A --> B\n  click A callback\n"
        )
        # Should not raise, and click should not affect nodes/edges
        assert len(d.edges) == 1


# ---------------------------------------------------------------------------
# Parser: direction override NOT inside subgraph
# ---------------------------------------------------------------------------


@pytest.mark.mutation
class TestParserDirectionOutsideSubgraph:
    """Kill mutant that removes 'if state.subgraph_stack:' guard on direction."""

    def test_direction_outside_subgraph_ignored(self):
        """Direction directive outside subgraph should not crash but
        should not affect the main diagram direction either
        (only subgraph directions are set via direction keyword).
        Kills mutant that removes the subgraph_stack check."""
        d = parse_flowchart("graph TD\n  direction LR\n  A --> B\n")
        # The main direction should remain TD (set in declaration)
        assert d.direction == Direction.TD


# ---------------------------------------------------------------------------
# Parser: preprocess splitting (semicolons as line separators)
# ---------------------------------------------------------------------------


@pytest.mark.mutation
class TestParserSemicolonSplit:
    """Kill mutants in _preprocess semicolon splitting."""

    def test_semicolon_splits_statements(self):
        """Kills mutant that removes semicolon splitting in preprocess."""
        d = parse_flowchart("graph TD\n  A --> B; C --> D\n")
        assert len(d.edges) == 2

    def test_multiple_semicolons(self):
        """Kills mutant that only splits on first semicolon."""
        d = parse_flowchart("graph TD\n  A[a]; B[b]; C[c]\n")
        assert len(d.nodes) == 3
