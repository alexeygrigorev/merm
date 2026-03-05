"""Mermaid syntax parser."""

from pymermaid.parser.classdiag import parse_class_diagram
from pymermaid.parser.flowchart import ParseError, parse_flowchart
from pymermaid.parser.statediag import parse_state_diagram

__all__ = [
    "ParseError",
    "parse_class_diagram",
    "parse_flowchart",
    "parse_state_diagram",
]
