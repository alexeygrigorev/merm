"""Mermaid syntax parser."""

from merm.parser.classdiag import parse_class_diagram
from merm.parser.erdiag import parse_er_diagram
from merm.parser.flowchart import ParseError, parse_flowchart
from merm.parser.gantt import parse_gantt
from merm.parser.pie import parse_pie
from merm.parser.statediag import parse_state_diagram

__all__ = [
    "ParseError",
    "parse_class_diagram",
    "parse_er_diagram",
    "parse_flowchart",
    "parse_gantt",
    "parse_pie",
    "parse_state_diagram",
]
