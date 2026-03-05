"""Parser for Mermaid pie chart syntax."""

from __future__ import annotations

import re

from pymermaid.ir.pie import PieChart, PieSlice
from pymermaid.parser.flowchart import ParseError

# Pattern for a data entry: "Label" : number
_SLICE_RE = re.compile(r'^\s*"([^"]+)"\s*:\s*([0-9]*\.?[0-9]+)\s*$')


def parse_pie(text: str) -> PieChart:
    """Parse Mermaid pie chart syntax into a PieChart IR.

    Raises ParseError on invalid input.
    """
    if not text or not text.strip():
        raise ParseError("Empty input")

    # Strip %% comments
    lines = []
    for line in text.splitlines():
        stripped = line.split("%%")[0]
        lines.append(stripped)

    # Find the 'pie' directive line
    header_idx = None
    for i, line in enumerate(lines):
        if re.match(r"^\s*pie\b", line):
            header_idx = i
            break

    if header_idx is None:
        raise ParseError("Missing 'pie' keyword")

    # Parse header line and subsequent lines for title and showData
    title = ""
    show_data = False

    # Process from header line onward looking for title/showData before slices
    # First check the header line itself
    header_line = lines[header_idx]
    # Remove the 'pie' keyword
    rest = re.sub(r"^\s*pie\b", "", header_line).strip()

    # Check for showData
    if rest.startswith("showData"):
        show_data = True
        rest = rest[len("showData"):].strip()

    # Check for title on the same line
    title_match = re.match(r"title\s+(.*)", rest)
    if title_match:
        title = title_match.group(1).strip()
        rest = ""

    # Process remaining lines for title/showData and slices
    slices: list[PieSlice] = []
    for i in range(header_idx + 1, len(lines)):
        line = lines[i].strip()
        if not line:
            continue

        # Check for showData on its own line
        if line == "showData":
            show_data = True
            continue

        # Check for title on its own line
        title_line_match = re.match(r"title\s+(.*)", line)
        if title_line_match:
            title = title_line_match.group(1).strip()
            continue

        # Try to parse as a slice
        slice_match = _SLICE_RE.match(lines[i])
        if slice_match:
            label = slice_match.group(1)
            value = float(slice_match.group(2))
            if value < 0:
                raise ParseError(f"Negative value for slice '{label}': {value}", line=i + 1)
            slices.append(PieSlice(label=label, value=value))
            continue

        # Check if this looks like a malformed slice (has quotes but bad format)
        if '"' in line:
            raise ParseError(f"Malformed slice entry: {line}", line=i + 1)

    if not slices:
        raise ParseError("No slices found in pie chart")

    return PieChart(title=title, show_data=show_data, slices=tuple(slices))


__all__ = ["parse_pie"]
