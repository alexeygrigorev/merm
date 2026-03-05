"""Flowchart parser: Mermaid flowchart syntax -> IR Diagram."""

import html
import re
from dataclasses import dataclass, field

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

class ParseError(Exception):
    """Raised when the parser encounters invalid Mermaid syntax."""

    def __init__(self, message: str, line: int | None = None) -> None:
        self.line = line
        if line is not None:
            message = f"Line {line}: {message}"
        super().__init__(message)

# ---------------------------------------------------------------------------
# Entity code decoding
# ---------------------------------------------------------------------------

_ENTITY_RE = re.compile(r"#(\d+);")

def _decode_entities(text: str) -> str:
    """Decode Mermaid entity codes and standard HTML entities."""
    # First decode standard HTML entities (&amp; &lt; &gt; &quot; &#38; &#x26; etc.)
    # This must run before Mermaid-specific decoding to avoid partial matches
    # (e.g. &#38; contains #38; which would be matched by the Mermaid regex)
    text = html.unescape(text)
    # Then decode Mermaid-specific numeric codes (#35; style without &)
    text = _ENTITY_RE.sub(lambda m: chr(int(m.group(1))), text)
    return text

# ---------------------------------------------------------------------------
# Pre-processing: strip comments, split on semicolons
# ---------------------------------------------------------------------------

def _preprocess(text: str) -> list[tuple[int, str]]:
    """Return list of (original_line_number, stripped_line)."""
    raw_lines = text.split("\n")
    result: list[tuple[int, str]] = []
    for lineno_0, raw in enumerate(raw_lines, start=1):
        # Strip inline %% comments (but not inside quoted strings - simple approach)
        stripped = _strip_comment(raw)
        # Split on semicolons (respecting quoted strings and brackets)
        parts = _split_semicolons(stripped)
        for part in parts:
            p = part.strip()
            if p:
                result.append((lineno_0, p))
    return result

def _strip_comment(line: str) -> str:
    """Remove ``%%`` comments from a line, respecting quoted strings."""
    # Find %% that is not inside quotes
    in_quote: str | None = None
    i = 0
    while i < len(line):
        ch = line[i]
        if in_quote:
            if ch == in_quote:
                in_quote = None
        else:
            if ch in ('"', "'"):
                in_quote = ch
            elif ch == "%" and i + 1 < len(line) and line[i + 1] == "%":
                return line[:i].rstrip()
        i += 1
    return line

def _split_semicolons(line: str) -> list[str]:
    """Split *line* on semicolons that are not inside quoted strings or brackets."""
    parts: list[str] = []
    current: list[str] = []
    in_quote = False
    depth = 0
    for ch in line:
        if in_quote:
            current.append(ch)
            if ch == '"':
                in_quote = False
            continue
        if ch == '"':
            in_quote = True
            current.append(ch)
            continue
        if ch in ("(", "[", "{"):
            depth += 1
        elif ch in (")", "]", "}"):
            depth -= 1
        if ch == ";" and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    parts.append("".join(current))
    return parts

# ---------------------------------------------------------------------------
# Node shape parsing
# ---------------------------------------------------------------------------

# Order matters: longer/more-specific delimiters must come first.
_SHAPE_PATTERNS: list[tuple[str, str, NodeShape]] = [
    ("(((",  ")))",  NodeShape.double_circle),
    ("((",   "))",   NodeShape.circle),
    ("([",   "])",   NodeShape.stadium),
    ("(",    ")",    NodeShape.rounded),
    ("[[",   "]]",   NodeShape.subroutine),
    ("[(",   ")]",   NodeShape.cylinder),
    ("[/",   "/]",   NodeShape.parallelogram),
    ("[\\",  "\\]",  NodeShape.parallelogram_alt),
    ("[/",   "\\]",  NodeShape.trapezoid),
    ("[\\",  "/]",   NodeShape.trapezoid_alt),
    ("[",    "]",    NodeShape.rect),
    ("{{",   "}}",   NodeShape.hexagon),
    ("{",    "}",    NodeShape.diamond),
]

@dataclass
class _NodeDef:
    id: str
    label: str
    shape: NodeShape
    css_classes: list[str] = field(default_factory=list)

def _parse_node_def(token: str) -> _NodeDef:
    """Parse a node definition token like ``A[text]`` or ``A:::cls``.

    Returns a _NodeDef with extracted id, label, shape, and css_classes.
    """
    # Handle inline class syntax  A:::className  (may be combined with shape)
    css_classes: list[str] = []
    # The ::: can appear after the shape brackets
    # e.g.  A[text]:::cls  or  A:::cls
    class_match = re.search(r":::(\w+)$", token)
    if class_match:
        css_classes.append(class_match.group(1))
        token = token[: class_match.start()]

    # Asymmetric shape is special: A)text(
    # The id is everything before the first ')' and the label is between ')' and '('
    asym_match = re.match(r"^([A-Za-z_\d][A-Za-z_\d]*)\)(.+)\($", token)
    if asym_match:
        nid = asym_match.group(1)
        label = asym_match.group(2).strip()
        label = _unquote(label)
        label = _decode_entities(label)
        return _NodeDef(nid, label, NodeShape.asymmetric, css_classes)

    # Try each shape pattern
    for open_delim, close_delim, shape in _SHAPE_PATTERNS:
        # Handle ambiguity between [/ /] (parallelogram) and [/ \] (trapezoid)
        # Find the id part (everything before the opening delimiter)
        idx = _find_delimiter(token, open_delim)
        if idx is None or idx == 0 and not token[0].isalpha() and token[0] != "_":
            continue
        if idx == 0:
            continue  # no id part
        nid = token[:idx]
        if not _valid_id(nid):
            continue
        rest = token[idx:]
        if not rest.startswith(open_delim):
            continue
        if not rest.endswith(close_delim):
            continue
        # Make sure the delimiters are properly matched (not just substring)
        inner = rest[len(open_delim) : len(rest) - len(close_delim)]
        # For shapes like [/ ... /] vs [/ ... \], we need to check
        # that we haven't matched a longer delimiter pair
        # Verify no better match exists with same open but different close
        label = _unquote(inner.strip())
        label = _decode_entities(label)
        return _NodeDef(nid, label, shape, css_classes)

    # Bare id -- just a word
    if _valid_id(token):
        return _NodeDef(token, token, NodeShape.rect, css_classes)

    raise ValueError(f"Cannot parse node definition: {token!r}")

def _find_delimiter(text: str, delim: str) -> int | None:
    """Find position of *delim* in *text*, skipping id characters."""
    # The delimiter starts after the id.
    # id is [A-Za-z_0-9]+
    i = 0
    while i < len(text) and (text[i].isalnum() or text[i] == "_"):
        i += 1
    if i < len(text) and text[i:].startswith(delim):
        return i
    return None

def _valid_id(s: str) -> bool:
    return bool(s) and bool(re.match(r"^[A-Za-z_\d][A-Za-z_\d]*$", s))

def _unquote(s: str) -> str:
    """Remove surrounding double quotes if present."""
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return s[1:-1]
    return s

# ---------------------------------------------------------------------------
# Edge parsing
# ---------------------------------------------------------------------------

# Regex that matches edge operators.
# Groups: (source_arrow)(body)(target_endpoint)
# Body determines line style; target endpoint determines arrow type.
#
# We match from the most specific patterns first.

_EDGE_RE = re.compile(
    r"""
    (?P<src_arrow><)?           # optional < for bidirectional
    (?:
      (?P<dotted_body>-\.+)     # dotted: -.  -..  etc
      (?P<dotted_end>->|-)      # dotted ending
    |
      (?P<thick_body>={2,})     # thick: == === etc
      (?P<thick_end>>?)         # thick ending > or nothing
    |
      (?P<invis>~{3,})          # invisible: ~~~ ~~~~
    |
      (?P<normal_body>-{2,})    # normal: -- --- ---- etc
      (?P<normal_end>>|o|x|-)   # ending: > o x or - (for open extra)
    )
    """,
    re.VERBOSE,
)

@dataclass
class _EdgeInfo:
    edge_type: EdgeType
    source_arrow: ArrowType
    target_arrow: ArrowType
    extra_length: int
    label: str | None

def _parse_edge_operator(op: str) -> _EdgeInfo:
    """Parse an edge operator string like ``-->``, ``-.->`` etc."""
    m = re.fullmatch(_EDGE_RE, op)
    if not m:
        raise ValueError(f"Invalid edge operator: {op!r}")

    src_arrow = ArrowType.arrow if m.group("src_arrow") else ArrowType.none

    if m.group("invis") is not None:
        extra = len(m.group("invis")) - 3
        return _EdgeInfo(
            EdgeType.invisible, ArrowType.none, ArrowType.none, extra, None,
        )

    if m.group("dotted_body") is not None:
        body = m.group("dotted_body")
        end = m.group("dotted_end")
        extra = len(body) - 2  # "-." is minimum
        if end == "->":
            return _EdgeInfo(
                EdgeType.dotted_arrow, src_arrow, ArrowType.arrow, extra, None,
            )
        else:
            return _EdgeInfo(
                EdgeType.dotted, src_arrow, ArrowType.none, extra, None,
            )

    if m.group("thick_body") is not None:
        body = m.group("thick_body")
        end = m.group("thick_end")
        extra = len(body) - 2  # "==" is minimum
        if end == ">":
            return _EdgeInfo(
                EdgeType.thick_arrow, src_arrow, ArrowType.arrow, extra, None,
            )
        else:
            return _EdgeInfo(
                EdgeType.thick, src_arrow, ArrowType.none, extra, None,
            )

    if m.group("normal_body") is not None:
        body = m.group("normal_body")
        end = m.group("normal_end")
        # minimum is "--" (2 dashes) for open or "-->" (2 dashes + >) for arrow
        base_len = 2
        extra = len(body) - base_len
        match end:
            case ">":
                return _EdgeInfo(
                    EdgeType.arrow, src_arrow, ArrowType.arrow, extra, None,
                )
            case "o":
                return _EdgeInfo(
                    EdgeType.arrow, src_arrow, ArrowType.circle, extra, None,
                )
            case "x":
                return _EdgeInfo(
                    EdgeType.arrow, src_arrow, ArrowType.cross, extra, None,
                )
            case "-":
                # open link: --- minimum (body "--" end "-")
                return _EdgeInfo(
                    EdgeType.open, src_arrow, ArrowType.none, extra, None,
                )
            case _:
                raise ValueError(f"Unknown edge ending: {end!r}")

    raise ValueError(f"Invalid edge operator: {op!r}")

# ---------------------------------------------------------------------------
# Statement-level line parser
# ---------------------------------------------------------------------------

# Edge operator patterns used for splitting lines into node/edge tokens.
# Order: longer patterns first to avoid partial matches.
_EDGE_OPERATORS = [
    # Dotted
    re.compile(r"<?\-\.+-\>"),   # <-.-> -.->
    re.compile(r"<?\-\.+-"),     # <-.- -.-
    # Thick
    re.compile(r"<?\={2,}\>"),   # <==> ==>
    re.compile(r"<?\={2,}"),     # <== ===
    # Invisible
    re.compile(r"\~{3,}"),       # ~~~
    # Normal arrow/open/circle/cross
    re.compile(r"<?\-{2,}\>"),   # <--> --> --->
    re.compile(r"<?\-{2,}[ox]"), # --o --x
    re.compile(r"<?\-{2,}\-"),   # --- ----
]

# Combined pattern to find edge operators in a line
_EDGE_OP_PATTERN = re.compile(
    r"""
    (?<!\w)                          # not preceded by word char
    (?:
      <?\-\.+->                      # dotted arrow  -.->  -..->
    | <?\-\.+-(?!>)                  # dotted open   -.-  -..-
    | <?\={2,}>                      # thick arrow   ==>  ===>
    | <?\={2,}(?!>)                  # thick open    ===  ====
    | ~{3,}                          # invisible     ~~~  ~~~~
    | <?\-{2,}>                      # normal arrow  -->  --->
    | <?\-{2,}[ox]                   # circle/cross  --o  --x
    | <?\-{2,}-(?![>\-ox\w])         # open link     ---  ----
    )
    (?!\w)                           # not followed by word char
    """,
    re.VERBOSE,
)

def _tokenize_statement(line: str) -> list[str]:
    """Split a node-edge statement into alternating node-group and edge-operator tokens.

    For example: ``A[Start] --> B[End]`` -> [``A[Start]``, ``-->``, ``B[End]``]
    And: ``A -->|label| B`` -> [``A``, ``-->|label|``, ``B``]
    And: ``A -- label --> B`` -> [``A``, ``-- label -->``, ``B``]
    """
    # Strategy: scan through the line finding edge operators. Everything between
    # operators is a node group (possibly with & for multi-target).
    tokens: list[str] = []
    pos = 0
    line_stripped = line.strip()

    while pos < len(line_stripped):
        # Skip whitespace
        while pos < len(line_stripped) and line_stripped[pos] == " ":
            pos += 1
        if pos >= len(line_stripped):
            break

        # Check inline label syntax FIRST: -- label --> etc.
        # Must precede plain edge match to avoid consuming == as thick
        inline_match = _try_match_inline_label_edge(line_stripped, pos)
        if inline_match:
            edge_str, end_pos = inline_match
            tokens.append(edge_str.strip())
            pos = end_pos
            continue

        # Try to match an edge operator at current position
        edge_match = _try_match_edge(line_stripped, pos)
        if edge_match:
            edge_str, end_pos = edge_match
            # Check for pipe label: -->|label|
            after = line_stripped[end_pos:]
            pipe_match = re.match(r"\|([^|]*)\|", after)
            if pipe_match:
                edge_str += pipe_match.group(0)
                end_pos += pipe_match.end()
            tokens.append(edge_str.strip())
            pos = end_pos
            continue

        # Otherwise, consume a node group token (until we hit an edge operator)
        node_token, end_pos = _consume_node_group(line_stripped, pos)
        if node_token:
            tokens.append(node_token.strip())
        pos = end_pos

    return tokens

def _try_match_edge(line: str, pos: int) -> tuple[str, int] | None:
    """Try to match an edge operator at position *pos* in *line*."""
    m = _EDGE_OP_PATTERN.match(line, pos)
    if m:
        return m.group(0), m.end()
    return None

def _try_match_inline_label_edge(line: str, pos: int) -> tuple[str, int] | None:
    """Match inline label edge syntax like ``-- label -->``."""
    # Pattern: -- text --> or -. text .-> or == text ==>
    patterns = [
        # -- label --> (normal)
        re.compile(r"--\s+(.+?)\s+(--+>|--+[ox]|--+-)"),
        # -. label .-> (dotted)
        re.compile(r"-\.\s+(.+?)\s+(\.->|\.-)"),
        # == label ==> (thick)
        re.compile(r"==\s+(.+?)\s+(==>|==)"),
    ]
    for pat in patterns:
        m = pat.match(line, pos)
        if m:
            return m.group(0), m.end()
    return None

def _consume_node_group(line: str, pos: int) -> tuple[str, int]:
    """Consume characters forming a node group (possibly with & separator).

    Handles balanced brackets/parens/braces and quoted strings.
    """
    start = pos
    depth = 0  # track nesting
    in_quote = False

    while pos < len(line):
        ch = line[pos]

        if in_quote:
            if ch == '"':
                in_quote = False
            pos += 1
            continue

        if ch == '"':
            in_quote = True
            pos += 1
            continue

        if ch in ("(", "[", "{"):
            depth += 1
            pos += 1
            continue
        if ch in (")", "]", "}"):
            depth -= 1
            pos += 1
            continue

        if depth > 0:
            pos += 1
            continue

        # At depth 0, check if we're about to hit an edge operator
        # We need to look ahead to avoid consuming edge operators as node text
        if ch in ("-", "=", "~", "<"):
            edge_match = _try_match_edge(line, pos)
            if edge_match:
                break
            inline_match = _try_match_inline_label_edge(line, pos)
            if inline_match:
                break

        # Whitespace at depth 0 before an edge op means stop
        if ch == " " and pos + 1 < len(line):
            # Look ahead past whitespace to see if an edge operator follows
            rest = line[pos:].lstrip()
            rest_pos = line.index(rest[0], pos) if rest else len(line)
            edge_match = _try_match_edge(line, rest_pos)
            if edge_match:
                break
            inline_match = _try_match_inline_label_edge(line, rest_pos)
            if inline_match:
                break

        pos += 1

    return line[start:pos], pos

# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------

@dataclass
class _ParserState:
    """Mutable state accumulated during parsing."""

    direction: Direction = Direction.TB
    nodes: dict[str, _NodeDef] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    styles: list[StyleDef] = field(default_factory=list)
    classes: dict[str, dict[str, str]] = field(default_factory=dict)
    # Subgraph stack for nesting
    subgraph_stack: list["_SubgraphBuilder"] = field(default_factory=list)
    top_level_subgraphs: list[Subgraph] = field(default_factory=list)

@dataclass
class _SubgraphBuilder:
    id: str
    title: str | None
    direction: Direction | None = None
    node_ids: list[str] = field(default_factory=list)
    child_subgraphs: list[Subgraph] = field(default_factory=list)

    def build(self) -> Subgraph:
        return Subgraph(
            id=self.id,
            title=self.title,
            direction=self.direction,
            node_ids=tuple(self.node_ids),
            subgraphs=tuple(self.child_subgraphs),
        )

def parse_flowchart(text: str) -> Diagram:
    """Parse Mermaid flowchart syntax into a :class:`Diagram`.

    Parameters
    ----------
    text:
        Complete Mermaid flowchart source, including the
        ``graph``/``flowchart`` declaration line.

    Returns
    -------
    Diagram
        Populated IR diagram.

    Raises
    ------
    ParseError
        On invalid syntax.  The exception message includes the line number.
    """
    lines = _preprocess(text)
    if not lines:
        raise ParseError("Empty input")

    state = _ParserState()

    # First line must be the declaration
    first_lineno, first_line = lines[0]
    _parse_declaration(first_line, first_lineno, state)

    for lineno, line in lines[1:]:
        _parse_line(line, lineno, state)

    # Check for unclosed subgraphs
    if state.subgraph_stack:
        raise ParseError(
            f"Unclosed subgraph '{state.subgraph_stack[-1].id}'",
            line=None,
        )

    # Build the Diagram
    node_list: list[Node] = []
    for ndef in state.nodes.values():
        node_list.append(
            Node(
                id=ndef.id,
                label=ndef.label,
                shape=ndef.shape,
                css_classes=tuple(ndef.css_classes),
            )
        )

    return Diagram(
        type=DiagramType.flowchart,
        direction=state.direction,
        nodes=tuple(node_list),
        edges=tuple(state.edges),
        subgraphs=tuple(state.top_level_subgraphs),
        styles=tuple(state.styles),
        classes=dict(state.classes),
    )

def _parse_declaration(line: str, lineno: int, state: _ParserState) -> None:
    """Parse the ``graph TD`` or ``flowchart LR`` declaration."""
    m = re.match(r"^(graph|flowchart)\s*(\w*)$", line, re.IGNORECASE)
    if not m:
        raise ParseError(
            f"Expected 'graph' or 'flowchart' declaration, got: {line!r}",
            lineno,
        )
    keyword = m.group(1).lower()
    dir_str = m.group(2).upper() if m.group(2) else ""

    if keyword not in ("graph", "flowchart"):
        raise ParseError(f"Unknown diagram keyword: {keyword!r}", lineno)

    if not dir_str:
        state.direction = Direction.TB
        return

    # TB and TD are synonyms
    if dir_str == "TB":
        dir_str = "TD"

    try:
        state.direction = Direction[dir_str]
    except KeyError:
        raise ParseError(f"Unknown direction: {dir_str!r}", lineno) from None

def _parse_line(line: str, lineno: int, state: _ParserState) -> None:
    """Parse a single logical line (after preprocessing)."""
    # subgraph start
    sg_match = re.match(r"^subgraph\s+(.*)$", line, re.IGNORECASE)
    if sg_match:
        _handle_subgraph_start(sg_match.group(1).strip(), lineno, state)
        return

    # subgraph end
    if re.match(r"^end\s*$", line, re.IGNORECASE):
        _handle_subgraph_end(lineno, state)
        return

    # direction override inside subgraph
    dir_match = re.match(r"^direction\s+(TB|TD|BT|LR|RL)\s*$", line, re.IGNORECASE)
    if dir_match:
        d = dir_match.group(1).upper()
        if d == "TB":
            d = "TD"
        if state.subgraph_stack:
            state.subgraph_stack[-1].direction = Direction[d]
        return

    # classDef
    cd_match = re.match(r"^classDef\s+(\S+)\s+(.+)$", line)
    if cd_match:
        cls_name = cd_match.group(1)
        props = _parse_style_props(cd_match.group(2))
        state.classes[cls_name] = props
        return

    # class assignment
    cls_match = re.match(r"^class\s+(\S+)\s+(\S+)$", line)
    if cls_match:
        node_ids_str = cls_match.group(1)
        cls_name = cls_match.group(2)
        for nid in node_ids_str.split(","):
            nid = nid.strip()
            if nid:
                if nid not in state.nodes:
                    state.nodes[nid] = _NodeDef(nid, nid, NodeShape.rect)
                state.nodes[nid].css_classes.append(cls_name)
        return

    # style directive
    style_match = re.match(r"^style\s+(\S+)\s+(.+)$", line)
    if style_match:
        target_id = style_match.group(1)
        props = _parse_style_props(style_match.group(2))
        state.styles.append(StyleDef(target_id=target_id, properties=props))
        return

    # click directive -- ignore gracefully
    if re.match(r"^click\s+", line, re.IGNORECASE):
        return

    # Node-edge statement
    _parse_node_edge_statement(line, lineno, state)

def _handle_subgraph_start(rest: str, lineno: int, state: _ParserState) -> None:
    """Handle ``subgraph id[Title]`` or ``subgraph id``."""
    # Parse: id[Title] or just id
    m = re.match(r"^([A-Za-z_][\w]*)\s*(?:\[([^\]]*)\])?\s*$", rest)
    if m:
        sg_id = m.group(1)
        title = m.group(2) if m.group(2) is not None else None
    else:
        # Bare word or quoted title
        parts = rest.split()
        if parts:
            sg_id = parts[0]
            title = " ".join(parts[1:]) if len(parts) > 1 else None
        else:
            sg_id = f"_sg_{lineno}"
            title = None

    builder = _SubgraphBuilder(id=sg_id, title=title)
    state.subgraph_stack.append(builder)

def _handle_subgraph_end(lineno: int, state: _ParserState) -> None:
    """Handle ``end`` keyword -- close current subgraph."""
    if not state.subgraph_stack:
        raise ParseError("'end' without matching 'subgraph'", lineno)

    builder = state.subgraph_stack.pop()
    sg = builder.build()

    if state.subgraph_stack:
        # Nested: add to parent
        state.subgraph_stack[-1].child_subgraphs.append(sg)
    else:
        state.top_level_subgraphs.append(sg)

def _parse_style_props(text: str) -> dict[str, str]:
    """Parse ``fill:#f9f,stroke:#333`` into a dict."""
    props: dict[str, str] = {}
    for part in text.split(","):
        part = part.strip()
        if ":" in part:
            k, v = part.split(":", 1)
            props[k.strip()] = v.strip()
    return props

def _register_node(ndef: _NodeDef, state: _ParserState) -> None:
    """Register a node definition, updating if it already exists."""
    existing = state.nodes.get(ndef.id)
    if existing:
        # Update label and shape if new definition provides them
        # (later definition wins)
        if ndef.label != ndef.id or ndef.shape != NodeShape.rect:
            existing.label = ndef.label
            existing.shape = ndef.shape
        existing.css_classes.extend(ndef.css_classes)
    else:
        state.nodes[ndef.id] = ndef

    # Register node in current subgraph
    if state.subgraph_stack:
        sg = state.subgraph_stack[-1]
        if ndef.id not in sg.node_ids:
            sg.node_ids.append(ndef.id)

def _parse_node_edge_statement(line: str, lineno: int, state: _ParserState) -> None:
    """Parse a statement with nodes and edges."""
    tokens = _tokenize_statement(line)
    if not tokens:
        return

    # Classify tokens as node-groups or edge-operators
    # Tokens alternate: node_group, edge_op, node_group, edge_op, ...
    # First token should be a node group.

    # Check if we have just a node definition (no edges)
    if len(tokens) == 1:
        # Just a node definition
        node_group = tokens[0]
        for nid_token in _split_ampersand(node_group):
            try:
                ndef = _parse_node_def(nid_token.strip())
            except ValueError:
                raise ParseError(f"Cannot parse: {line!r}", lineno) from None
            _register_node(ndef, state)
        return

    # We should have an odd number of tokens: node, edge, node, edge, node...
    if len(tokens) < 3 or len(tokens) % 2 == 0:
        raise ParseError(f"Incomplete edge statement: {line!r}", lineno)

    # Process chained edges
    for i in range(0, len(tokens) - 2, 2):
        source_group = tokens[i]
        edge_token = tokens[i + 1]
        target_group = tokens[i + 2]

        # Parse edge info from the operator token
        edge_info = _parse_edge_token(edge_token, lineno)

        # Expand & in source and target groups
        sources = _split_ampersand(source_group)
        targets = _split_ampersand(target_group)

        for src_str in sources:
            try:
                src_def = _parse_node_def(src_str.strip())
            except ValueError:
                raise ParseError(f"Cannot parse node: {src_str!r}", lineno) from None
            _register_node(src_def, state)

            for tgt_str in targets:
                try:
                    tgt_def = _parse_node_def(tgt_str.strip())
                except ValueError:
                    raise ParseError(
                        f"Cannot parse node: {tgt_str!r}", lineno,
                    ) from None
                _register_node(tgt_def, state)

                state.edges.append(
                    Edge(
                        source=src_def.id,
                        target=tgt_def.id,
                        label=edge_info.label,
                        edge_type=edge_info.edge_type,
                        source_arrow=edge_info.source_arrow,
                        target_arrow=edge_info.target_arrow,
                        extra_length=edge_info.extra_length,
                    )
                )

def _parse_edge_token(token: str, lineno: int) -> _EdgeInfo:
    """Parse an edge token which may include a pipe label or inline label."""
    # Check for pipe label: -->|label|
    pipe_match = re.match(r"^(.+?)\|([^|]*)\|$", token)
    if pipe_match:
        op_str = pipe_match.group(1).strip()
        label = pipe_match.group(2)
        info = _parse_edge_operator(op_str)
        info.label = _decode_entities(label) if label else ""
        return info

    # Check for inline label: -- label --> or -. label .-> or == label ==>
    inline_patterns = [
        # -- text -->
        re.compile(r"^(--)\s+(.+?)\s+(--+>|--+[ox]|--+-)$"),
        # -. text .->
        re.compile(r"^(-\.)\s+(.+?)\s+(\.->|\.-)$"),
        # == text ==>
        re.compile(r"^(==)\s+(.+?)\s+(==>|==)$"),
    ]
    for pat in inline_patterns:
        m = pat.match(token)
        if m:
            prefix = m.group(1)
            label = m.group(2).strip()
            suffix = m.group(3)
            # Reconstruct the operator without the label
            if prefix == "--":
                # suffix is "-->" or "---" etc (already full)
                if suffix.startswith("--"):
                    op = suffix
                else:
                    op = "--" + suffix
            elif prefix == "-.":
                # -. label .-> => operator is -.->
                if suffix == ".->":
                    op = "-." + suffix
                else:  # .-
                    op = "-." + suffix
            elif prefix == "==":
                # == label ==> => operator is ==>
                op = suffix
                if not suffix.startswith("=="):
                    op = "==" + suffix
            else:
                op = prefix + suffix

            try:
                info = _parse_edge_operator(op)
            except ValueError:
                raise ParseError(f"Cannot parse edge: {token!r}", lineno) from None
            info.label = _decode_entities(label)
            return info

    # Plain edge operator
    try:
        return _parse_edge_operator(token.strip())
    except ValueError:
        raise ParseError(f"Cannot parse edge operator: {token!r}", lineno) from None

def _split_ampersand(group: str) -> list[str]:
    """Split a node group by ``&`` separator."""
    # Don't split & inside brackets/parens
    parts: list[str] = []
    current: list[str] = []
    depth = 0
    in_quote = False
    for ch in group:
        if in_quote:
            current.append(ch)
            if ch == '"':
                in_quote = False
            continue
        if ch == '"':
            in_quote = True
            current.append(ch)
            continue
        if ch in ("(", "[", "{"):
            depth += 1
        elif ch in (")", "]", "}"):
            depth -= 1
        if ch == "&" and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    rest = "".join(current).strip()
    if rest:
        parts.append(rest)
    return parts

__all__ = ["ParseError", "parse_flowchart"]
