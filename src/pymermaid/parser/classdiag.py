"""Class diagram parser: Mermaid classDiagram syntax -> ClassDiagram IR.

Handles:
- classDiagram declaration
- Class definitions: class Animal { +name: string\\n +makeSound() }
- Shorthand: class Animal, Animal : +name string, Animal : +makeSound()
- Relationships: <|--, *--, o--, -->, ..>, ..|>
- Labels on relationships: A --> B : uses
- Cardinality: A "1" --> "*" B
- Annotations: <<interface>>, <<abstract>>, <<enumeration>>
- Visibility markers: + public, - private, # protected, ~ package
- Auto-creation of classes from relationship references
"""

import re
from dataclasses import dataclass, field

from pymermaid.ir.classdiag import (
    ClassDiagram,
    ClassMember,
    ClassNode,
    ClassRelation,
    RelationType,
    Visibility,
)
from pymermaid.parser.flowchart import ParseError

# ---------------------------------------------------------------------------
# Relationship pattern matching
# ---------------------------------------------------------------------------

# Order matters: longer/more specific patterns first.
# Each tuple: (regex_pattern, rel_type, is_reversed)
# "reversed" means the arrow points left, so source/target are swapped.
_REL_PATTERNS: list[tuple[str, RelationType, bool]] = [
    # Inheritance: <|-- and --|>
    (r"<\|--", RelationType.INHERITANCE, True),
    (r"--\|>", RelationType.INHERITANCE, False),
    # Realization: <|.. and ..|>
    (r"<\|\.\.", RelationType.REALIZATION, True),
    (r"\.\.\|>", RelationType.REALIZATION, False),
    # Composition: *-- and --*
    (r"\*--", RelationType.COMPOSITION, True),
    (r"--\*", RelationType.COMPOSITION, False),
    # Aggregation: o-- and --o
    (r"o--", RelationType.AGGREGATION, True),
    (r"--o", RelationType.AGGREGATION, False),
    # Dependency: <.. and ..>
    (r"<\.\.", RelationType.DEPENDENCY, True),
    (r"\.\.>", RelationType.DEPENDENCY, False),
    # Association: <-- and -->
    (r"<--", RelationType.ASSOCIATION, True),
    (r"-->", RelationType.ASSOCIATION, False),
    # Plain solid line (association without arrow): --
    (r"--", RelationType.ASSOCIATION, False),
    # Plain dashed line (dependency without arrow): ..
    (r"\.\.", RelationType.DEPENDENCY, False),
]

# Build a combined regex that matches any relationship operator.
_REL_COMBINED = "|".join(
    f"(?P<rel{i}>{pat})" for i, (pat, _, _) in enumerate(_REL_PATTERNS)
)
_REL_RE = re.compile(_REL_COMBINED)

def _match_relationship(text: str) -> tuple[RelationType, bool, int, int] | None:
    """Try to find a relationship operator in *text*.

    Returns (rel_type, is_reversed, match_start, match_end) or None.
    """
    m = _REL_RE.search(text)
    if m is None:
        return None
    for i, (_, rel_type, is_reversed) in enumerate(_REL_PATTERNS):
        if m.group(f"rel{i}") is not None:
            return rel_type, is_reversed, m.start(), m.end()
    return None

# ---------------------------------------------------------------------------
# Member parsing
# ---------------------------------------------------------------------------

_VISIBILITY_MAP = {
    "+": Visibility.PUBLIC,
    "-": Visibility.PRIVATE,
    "#": Visibility.PROTECTED,
    "~": Visibility.PACKAGE,
}

def _parse_member(text: str) -> ClassMember:
    """Parse a single member string like ``+name: string`` or ``-makeSound() void``."""
    text = text.strip()

    # Detect visibility prefix
    visibility = Visibility.PUBLIC
    if text and text[0] in _VISIBILITY_MAP:
        visibility = _VISIBILITY_MAP[text[0]]
        text = text[1:].strip()

    # Detect method vs field
    is_method = "()" in text or "(" in text

    if is_method:
        # Strip parentheses content for name extraction
        # Pattern: name(args) return_type  or  name() return_type  or  name()
        m = re.match(r"(\w+)\([^)]*\)\s*(.*)", text)
        if m:
            name = m.group(1)
            type_str = m.group(2).strip()
        else:
            name = text
            type_str = ""
    else:
        # Field: name: type  or  name type  or  just name
        if ":" in text:
            parts = text.split(":", 1)
            name = parts[0].strip()
            type_str = parts[1].strip()
        elif " " in text:
            parts = text.split(None, 1)
            name = parts[0]
            type_str = parts[1].strip() if len(parts) > 1 else ""
        else:
            name = text
            type_str = ""

    return ClassMember(
        name=name,
        type_str=type_str,
        visibility=visibility,
        is_method=is_method,
    )

# ---------------------------------------------------------------------------
# Preprocessing
# ---------------------------------------------------------------------------

def _strip_comment(line: str) -> str:
    """Remove %% comments from a line."""
    idx = line.find("%%")
    if idx >= 0:
        return line[:idx].rstrip()
    return line

def _preprocess(text: str) -> list[tuple[int, str]]:
    """Return list of (line_number, stripped_line), handling block class defs."""
    raw_lines = text.split("\n")
    result: list[tuple[int, str]] = []
    in_block = False
    block_lines: list[str] = []
    block_start = 0

    for lineno, raw in enumerate(raw_lines, start=1):
        stripped = _strip_comment(raw).strip()
        if not stripped:
            continue

        if in_block:
            if stripped == "}":
                # End of block: emit joined block
                result.append((block_start, " ".join(block_lines) + " }"))
                in_block = False
                block_lines = []
            else:
                block_lines.append(stripped)
            continue

        # Check if this line starts a block class definition
        if re.match(r"^class\s+\w+\s*\{", stripped) and "}" not in stripped:
            in_block = True
            block_start = lineno
            # Extract the "class Name {" part
            block_lines = [stripped]
            continue

        # Single-line block: class Name { ... }
        result.append((lineno, stripped))

    return result

# ---------------------------------------------------------------------------
# Parser state
# ---------------------------------------------------------------------------

@dataclass
class _ClassBuilder:
    """Mutable class accumulator."""

    id: str
    label: str
    annotation: str | None = None
    members: list[ClassMember] = field(default_factory=list)

    def build(self) -> ClassNode:
        return ClassNode(
            id=self.id,
            label=self.label,
            annotation=self.annotation,
            members=tuple(self.members),
        )

@dataclass
class _ParserState:
    """Mutable state during parsing."""

    classes: dict[str, _ClassBuilder] = field(default_factory=dict)
    relations: list[ClassRelation] = field(default_factory=list)

    def ensure_class(self, name: str) -> _ClassBuilder:
        """Get or create a class builder for *name*."""
        if name not in self.classes:
            self.classes[name] = _ClassBuilder(id=name, label=name)
        return self.classes[name]

# ---------------------------------------------------------------------------
# Line parsers
# ---------------------------------------------------------------------------

def _parse_class_block(line: str, lineno: int, state: _ParserState) -> bool:
    """Try to parse ``class Name { members... }``."""
    m = re.match(r"^class\s+(\w+)\s*\{(.*)\}\s*$", line)
    if not m:
        return False

    class_name = m.group(1)
    body = m.group(2).strip()

    builder = state.ensure_class(class_name)

    # Split members by semicolons or by the original lines (joined with space
    # during preprocessing -- members were separated by newlines, now spaces)
    # We use a heuristic: split on visibility markers that appear after a space
    if body:
        # Try splitting on common separators
        # Members in block are originally newline-separated, joined with space
        # Split on visibility markers at word boundaries, or by semicolons
        raw_members = _split_members(body)
        for raw in raw_members:
            raw = raw.strip()
            if not raw:
                continue
            # Check for annotation
            ann_match = re.match(r"^<<(\w+)>>$", raw)
            if ann_match:
                builder.annotation = f"<<{ann_match.group(1)}>>"
                continue
            builder.members.append(_parse_member(raw))

    return True

def _split_members(body: str) -> list[str]:
    """Split block body into individual member strings.

    Members are separated by semicolons or by detecting visibility-prefix
    boundaries when the body was joined from multiple lines.
    """
    # First try semicolons
    if ";" in body:
        return [p.strip() for p in body.split(";") if p.strip()]

    # Split on visibility markers that follow a closing paren or type chars
    # This handles the case where newlines were joined into spaces
    parts: list[str] = []
    current: list[str] = []
    tokens = body.split()

    for token in tokens:
        # If token starts with a visibility marker and we already have content,
        # start a new member
        if token and token[0] in "+-#~" and current:
            parts.append(" ".join(current))
            current = [token]
        elif re.match(r"^<<\w+>>$", token) and current:
            parts.append(" ".join(current))
            current = [token]
        else:
            current.append(token)

    if current:
        parts.append(" ".join(current))

    return parts

def _parse_class_shorthand(line: str, lineno: int, state: _ParserState) -> bool:
    """Try to parse ``class Name`` (without braces)."""
    m = re.match(r"^class\s+(\w+)\s*$", line)
    if not m:
        return False
    class_name = m.group(1)
    state.ensure_class(class_name)
    return True

def _parse_annotation_line(line: str, lineno: int, state: _ParserState) -> bool:
    """Try to parse ``<<interface>> ClassName``."""
    m = re.match(r"^<<(\w+)>>\s+(\w+)\s*$", line)
    if not m:
        return False
    annotation = f"<<{m.group(1)}>>"
    class_name = m.group(2)
    builder = state.ensure_class(class_name)
    builder.annotation = annotation
    return True

def _parse_member_shorthand(line: str, lineno: int, state: _ParserState) -> bool:
    """Try to parse ``ClassName : +memberDef``."""
    m = re.match(r"^(\w+)\s*:\s+(.+)$", line)
    if not m:
        return False
    class_name = m.group(1)
    member_text = m.group(2).strip()

    # Don't match if this looks like a relationship label
    # (relationship lines are handled before this)

    builder = state.ensure_class(class_name)
    builder.members.append(_parse_member(member_text))
    return True

def _parse_relationship(line: str, lineno: int, state: _ParserState) -> bool:
    """Try to parse a relationship line like ``A <|-- B : label``."""
    # First try to extract cardinality: A "1" --> "*" B : label
    # Pattern: ClassName [cardinality] RELOP [cardinality] ClassName [: label]

    rel_match = _match_relationship(line)
    if rel_match is None:
        return False

    rel_type, is_reversed, rel_start, rel_end = rel_match

    left_part = line[:rel_start].strip()
    right_part = line[rel_end:].strip()

    # Extract label from right part: "ClassName : label"
    label = ""
    # Split right part on " : " to separate class name and label
    label_match = re.match(r"^(.+?)\s*:\s+(.+)$", right_part)
    if label_match:
        right_class_part = label_match.group(1).strip()
        label = label_match.group(2).strip()
    else:
        right_class_part = right_part

    # Extract cardinality from left part: 'ClassName "1"' or '"1" ClassName'
    left_cardinality = ""
    right_cardinality = ""

    # Left: ClassName "card"
    left_card_match = re.match(r'^(\w+)\s+"([^"]*)"$', left_part)
    if left_card_match:
        left_class = left_card_match.group(1)
        left_cardinality = left_card_match.group(2)
    else:
        # Left: "card" ClassName -- unlikely but handle it
        left_card_match2 = re.match(r'^"([^"]*)"\s+(\w+)$', left_part)
        if left_card_match2:
            left_cardinality = left_card_match2.group(1)
            left_class = left_card_match2.group(2)
        else:
            left_class = left_part.strip()

    # Right: "card" ClassName
    right_card_match = re.match(r'^"([^"]*)"\s+(\w+)$', right_class_part)
    if right_card_match:
        right_cardinality = right_card_match.group(1)
        right_class = right_card_match.group(2)
    else:
        # Right: ClassName "card"
        right_card_match2 = re.match(r'^(\w+)\s+"([^"]*)"$', right_class_part)
        if right_card_match2:
            right_class = right_card_match2.group(1)
            right_cardinality = right_card_match2.group(2)
        else:
            right_class = right_class_part.strip()

    # Validate class names
    if not re.match(r"^\w+$", left_class) or not re.match(r"^\w+$", right_class):
        return False

    # Determine source and target based on arrow direction
    if is_reversed:
        source = right_class
        target = left_class
        source_card = right_cardinality
        target_card = left_cardinality
    else:
        source = left_class
        target = right_class
        source_card = left_cardinality
        target_card = right_cardinality

    # Auto-create classes
    state.ensure_class(left_class)
    state.ensure_class(right_class)

    state.relations.append(ClassRelation(
        source=source,
        target=target,
        rel_type=rel_type,
        label=label,
        source_cardinality=source_card,
        target_cardinality=target_card,
    ))
    return True

# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------

def parse_class_diagram(text: str) -> ClassDiagram:
    """Parse Mermaid classDiagram syntax into a ClassDiagram IR.

    Parameters
    ----------
    text:
        Complete Mermaid class diagram source, including the
        ``classDiagram`` declaration line.

    Returns
    -------
    ClassDiagram
        Populated IR class diagram.

    Raises
    ------
    ParseError
        On invalid syntax.
    """
    lines = _preprocess(text)
    if not lines:
        raise ParseError("Empty input")

    state = _ParserState()

    # First line must be the declaration
    first_lineno, first_line = lines[0]
    if not re.match(r"^classDiagram\s*$", first_line, re.IGNORECASE):
        raise ParseError(
            f"Expected 'classDiagram' declaration, got: {first_line!r}",
            first_lineno,
        )

    for lineno, line in lines[1:]:
        # Skip empty lines
        if not line:
            continue

        # Try each parser in priority order
        if _parse_class_block(line, lineno, state):
            continue
        if _parse_class_shorthand(line, lineno, state):
            continue
        if _parse_annotation_line(line, lineno, state):
            continue
        if _parse_relationship(line, lineno, state):
            continue
        if _parse_member_shorthand(line, lineno, state):
            continue

        # Unknown line -- skip gracefully (matching mermaid.js behavior)

    # Build final ClassDiagram
    class_list = [builder.build() for builder in state.classes.values()]

    return ClassDiagram(
        classes=tuple(class_list),
        relations=tuple(state.relations),
    )

__all__ = ["parse_class_diagram"]
