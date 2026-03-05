"""ER diagram parser: Mermaid erDiagram syntax -> ERDiagram IR.

Handles:
- erDiagram declaration
- Entity definitions with typed attributes and optional key constraints
- Relationships with cardinality markers, line styles, and labels
- Comments (%%)
- Auto-creation of entities referenced in relationships
"""

import re
from dataclasses import dataclass, field

from pymermaid.ir.erdiag import (
    ERAttribute,
    ERAttributeKey,
    ERCardinality,
    ERDiagram,
    EREntity,
    ERLineStyle,
    ERRelationship,
)
from pymermaid.parser.flowchart import ParseError

# ---------------------------------------------------------------------------
# Cardinality parsing
# ---------------------------------------------------------------------------

# Source-side (left) cardinality markers: appear before the line style (--..)
# In "A ||--o{ B", the source marker is "||" (before --)
_SOURCE_CARDINALITY = {
    "||": ERCardinality.EXACTLY_ONE,
    "o|": ERCardinality.ZERO_OR_ONE,
    "}|": ERCardinality.ONE_OR_MORE,
    "}o": ERCardinality.ZERO_OR_MORE,
}

# Target-side (right) cardinality markers: appear after the line style (--..)
# In "A ||--o{ B", the target marker is "o{" (after --)
_TARGET_CARDINALITY = {
    "||": ERCardinality.EXACTLY_ONE,
    "|o": ERCardinality.ZERO_OR_ONE,
    "|{": ERCardinality.ONE_OR_MORE,
    "o{": ERCardinality.ZERO_OR_MORE,
}

# Line styles
_LINE_STYLES = {
    "--": ERLineStyle.SOLID,
    "..": ERLineStyle.DASHED,
}

# Entity name pattern: alphanumeric plus hyphens
_ENTITY_NAME = r"[A-Za-z][A-Za-z0-9_-]*"

# Full relationship line regex
# Source markers (before --/..): ||  o|  }|  }o
# Target markers (after --/..): ||  |o  |{  o{
_REL_LINE_RE = re.compile(
    rf"^\s*({_ENTITY_NAME})\s+"
    r"(\|\||o\||\}\||\}o)"    # source cardinality
    r"(--|\.\.)"              # line style
    r"(\|\||\|o|\|\{|o\{)"    # target cardinality
    rf"\s+({_ENTITY_NAME})"
    r"\s*:\s*"
    r'("[^"]*"|[^\s].*?)'    # label (quoted or unquoted)
    r"\s*$"
)

# Attribute key pattern
_KEY_MAP = {
    "PK": ERAttributeKey.PK,
    "FK": ERAttributeKey.FK,
    "UK": ERAttributeKey.UK,
}

# ---------------------------------------------------------------------------
# Preprocessing
# ---------------------------------------------------------------------------

def _strip_comment(line: str) -> str:
    """Remove %% comments from a line."""
    idx = line.find("%%")
    if idx >= 0:
        return line[:idx].rstrip()
    return line

# ---------------------------------------------------------------------------
# Parser state
# ---------------------------------------------------------------------------

@dataclass
class _EntityBuilder:
    """Mutable entity accumulator."""

    id: str
    attributes: list[ERAttribute] = field(default_factory=list)

    def build(self) -> EREntity:
        return EREntity(
            id=self.id,
            attributes=tuple(self.attributes),
        )

@dataclass
class _ParserState:
    """Mutable state during parsing."""

    entities: dict[str, _EntityBuilder] = field(default_factory=dict)
    relationships: list[ERRelationship] = field(default_factory=list)

    def ensure_entity(self, name: str) -> _EntityBuilder:
        """Get or create an entity builder for *name*."""
        if name not in self.entities:
            self.entities[name] = _EntityBuilder(id=name)
        return self.entities[name]

# ---------------------------------------------------------------------------
# Attribute parsing
# ---------------------------------------------------------------------------

def _parse_attribute(line: str) -> ERAttribute:
    """Parse an attribute line like 'string name PK'."""
    parts = line.strip().split()
    if len(parts) < 2:
        raise ParseError(f"Invalid attribute: {line!r}")

    type_str = parts[0]
    name = parts[1]
    key = ERAttributeKey.NONE

    if len(parts) >= 3 and parts[2] in _KEY_MAP:
        key = _KEY_MAP[parts[2]]

    return ERAttribute(type_str=type_str, name=name, key=key)

# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------

def parse_er_diagram(text: str) -> ERDiagram:
    """Parse Mermaid erDiagram syntax into an ERDiagram IR.

    Parameters
    ----------
    text:
        Complete Mermaid ER diagram source, including the
        ``erDiagram`` declaration line.

    Returns
    -------
    ERDiagram
        Populated IR ER diagram.

    Raises
    ------
    ParseError
        On invalid syntax.
    """
    raw_lines = text.split("\n")
    lines: list[str] = []
    for raw in raw_lines:
        stripped = _strip_comment(raw).strip()
        if stripped:
            lines.append(stripped)

    if not lines:
        raise ParseError("Empty input")

    # First line must be the declaration
    if not re.match(r"^erDiagram\s*$", lines[0], re.IGNORECASE):
        raise ParseError(
            f"Expected 'erDiagram' declaration, got: {lines[0]!r}",
        )

    state = _ParserState()

    i = 1
    while i < len(lines):
        line = lines[i]

        # Check for entity block: ENTITY_NAME {
        entity_block_match = re.match(
            rf"^({_ENTITY_NAME})\s*\{{\s*$", line
        )
        if entity_block_match:
            entity_name = entity_block_match.group(1)
            builder = state.ensure_entity(entity_name)
            i += 1
            # Read attributes until closing brace
            while i < len(lines):
                attr_line = lines[i].strip()
                if attr_line == "}":
                    i += 1
                    break
                builder.attributes.append(_parse_attribute(attr_line))
                i += 1
            continue

        # Check for entity block on one line: ENTITY_NAME { ... }
        entity_inline_match = re.match(
            rf"^({_ENTITY_NAME})\s*\{{(.*)\}}\s*$", line
        )
        if entity_inline_match:
            entity_name = entity_inline_match.group(1)
            body = entity_inline_match.group(2).strip()
            builder = state.ensure_entity(entity_name)
            if body:
                # Attributes separated by newlines or semicolons
                for part in body.split(";"):
                    part = part.strip()
                    if part:
                        builder.attributes.append(_parse_attribute(part))
            i += 1
            continue

        # Check for relationship line
        rel_match = _REL_LINE_RE.match(line)
        if rel_match:
            source_name = rel_match.group(1)
            left_card_str = rel_match.group(2)
            line_style_str = rel_match.group(3)
            right_card_str = rel_match.group(4)
            target_name = rel_match.group(5)
            label = rel_match.group(6).strip()

            # Strip quotes from label
            if label.startswith('"') and label.endswith('"'):
                label = label[1:-1]

            source_card = _SOURCE_CARDINALITY[left_card_str]
            target_card = _TARGET_CARDINALITY[right_card_str]
            line_style = _LINE_STYLES[line_style_str]

            # Auto-create entities
            state.ensure_entity(source_name)
            state.ensure_entity(target_name)

            state.relationships.append(ERRelationship(
                source=source_name,
                target=target_name,
                source_cardinality=source_card,
                target_cardinality=target_card,
                line_style=line_style,
                label=label,
            ))
            i += 1
            continue

        # Unknown line -- skip gracefully
        i += 1

    # Build final ERDiagram
    entity_list = [builder.build() for builder in state.entities.values()]

    return ERDiagram(
        entities=tuple(entity_list),
        relationships=tuple(state.relationships),
    )

__all__ = ["parse_er_diagram"]
