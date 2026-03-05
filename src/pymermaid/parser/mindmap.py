"""Parser for Mermaid mindmap syntax."""

import re

from pymermaid.ir.mindmap import MindmapDiagram, MindmapNode, MindmapShape
from pymermaid.parser.flowchart import ParseError

# Patterns for node shape detection (id prefix is optional)
_CIRCLE_RE = re.compile(r"^(.*?)\(\((.+)\)\)$")
_ROUNDED_RE = re.compile(r"^(.*?)\((.+)\)$")
_RECT_RE = re.compile(r"^(.*?)\[(.+)\]$")
_CLOUD_RE = re.compile(r"^(.*?)\)\)(.+)\(\($")

# For nodes that are just bare label (possibly with id prefix)
_BARE_LABEL_RE = re.compile(r"^(.+)$")

def _parse_node_text(raw: str) -> tuple[str, str, MindmapShape]:
    """Parse raw node text into (id, label, shape).

    Returns the id, display label, and detected shape.
    """
    raw = raw.strip()

    # Circle: id((text)) or ((text))
    m = _CIRCLE_RE.match(raw)
    if m:
        node_id = m.group(1).strip() or m.group(2).strip()
        label = m.group(2).strip()
        return node_id, label, MindmapShape.CIRCLE

    # Cloud: id))text(( or ))text((
    m = _CLOUD_RE.match(raw)
    if m:
        node_id = m.group(1).strip() or m.group(2).strip()
        label = m.group(2).strip()
        return node_id, label, MindmapShape.CLOUD

    # Rounded rect: id(text) or (text)
    m = _ROUNDED_RE.match(raw)
    if m:
        node_id = m.group(1).strip() or m.group(2).strip()
        label = m.group(2).strip()
        return node_id, label, MindmapShape.ROUNDED_RECT

    # Rectangle: id[text] or [text]
    m = _RECT_RE.match(raw)
    if m:
        node_id = m.group(1).strip() or m.group(2).strip()
        label = m.group(2).strip()
        return node_id, label, MindmapShape.RECT

    # Default: bare text
    node_id = raw.replace(" ", "_")
    return node_id, raw, MindmapShape.DEFAULT

def parse_mindmap(text: str) -> MindmapDiagram:
    """Parse Mermaid mindmap syntax into a MindmapDiagram IR.

    Raises ParseError on invalid input.
    """
    if not text or not text.strip():
        raise ParseError("Empty input")

    # Strip %% comments and find content lines
    lines: list[str] = []
    for line in text.splitlines():
        # Remove comment portions
        comment_idx = line.find("%%")
        if comment_idx >= 0:
            line = line[:comment_idx]
        lines.append(line)

    # Find the 'mindmap' keyword line
    header_idx = None
    for i, line in enumerate(lines):
        if re.match(r"^\s*mindmap\s*$", line):
            header_idx = i
            break

    if header_idx is None:
        raise ParseError("Missing 'mindmap' keyword")

    # Collect content lines after the header
    content_lines: list[tuple[int, int, str]] = []  # (line_num, indent, text)
    for i in range(header_idx + 1, len(lines)):
        line = lines[i]
        if not line.strip():
            continue
        # Compute indentation
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        content_lines.append((i + 1, indent, stripped))

    if not content_lines:
        raise ParseError("No root node found in mindmap")

    # Build tree using indentation stack
    # The stack holds (indent_level, MindmapNode_builder) pairs
    # We build bottom-up: parse all lines, then assemble the tree

    # First pass: parse all nodes as flat list with indent info
    parsed_nodes: list[tuple[int, str, str, MindmapShape]] = []
    for line_num, indent, raw_text in content_lines:
        node_id, label, shape = _parse_node_text(raw_text)
        parsed_nodes.append((indent, node_id, label, shape))

    # Build tree recursively using a stack-based approach
    def _build_tree(
        nodes: list[tuple[int, str, str, MindmapShape]], start: int
    ) -> tuple[MindmapNode, int]:
        """Build a subtree starting at index `start`.

        Returns (node, next_index) where next_index is the index after all
        children of this node have been consumed.
        """
        indent, node_id, label, shape = nodes[start]
        children: list[MindmapNode] = []
        idx = start + 1

        while idx < len(nodes):
            child_indent = nodes[idx][0]
            if child_indent <= indent:
                # Same or lesser indent means sibling or ancestor
                break
            if child_indent > indent:
                child, idx = _build_tree(nodes, idx)
                children.append(child)

        return (
            MindmapNode(
                id=node_id, label=label, shape=shape, children=tuple(children)
            ),
            idx,
        )

    root, _ = _build_tree(parsed_nodes, 0)
    return MindmapDiagram(root=root)

__all__ = ["parse_mindmap"]
