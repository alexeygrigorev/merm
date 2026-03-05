"""Mermaid syntax parser."""

from pymermaid.parser.classdiag import parse_class_diagram
from pymermaid.parser.erdiag import parse_er_diagram
from pymermaid.parser.flowchart import ParseError, parse_flowchart
from pymermaid.parser.gantt import parse_gantt
from pymermaid.parser.pie import parse_pie
from pymermaid.parser.statediag import parse_state_diagram

__all__ = [
    "ParseError",
    "parse_class_diagram",
    "parse_er_diagram",
    "parse_flowchart",
    "parse_gantt",
    "parse_pie",
    "parse_state_diagram",
]
