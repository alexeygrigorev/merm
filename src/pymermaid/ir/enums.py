"""Enumeration types for the intermediate representation.

Defines DiagramType, Direction, NodeShape, EdgeType, and ArrowType enums
used throughout the pymermaid pipeline.
"""

from enum import Enum


class DiagramType(Enum):
    """Supported diagram types."""

    flowchart = "flowchart"
    sequence = "sequence"
    class_diagram = "class_diagram"
    state = "state"
    er = "er"
    gantt = "gantt"
    pie = "pie"
    mindmap = "mindmap"
    git_graph = "git_graph"

class Direction(Enum):
    """Graph direction / orientation."""

    TB = "TB"
    TD = "TD"
    BT = "BT"
    LR = "LR"
    RL = "RL"

class NodeShape(Enum):
    """Node shape types for flowchart nodes."""

    rect = "rect"
    rounded = "rounded"
    stadium = "stadium"
    subroutine = "subroutine"
    cylinder = "cylinder"
    circle = "circle"
    asymmetric = "asymmetric"
    diamond = "diamond"
    hexagon = "hexagon"
    parallelogram = "parallelogram"
    parallelogram_alt = "parallelogram_alt"
    trapezoid = "trapezoid"
    trapezoid_alt = "trapezoid_alt"
    double_circle = "double_circle"

class EdgeType(Enum):
    """Edge line style types."""

    arrow = "arrow"
    open = "open"
    dotted = "dotted"
    dotted_arrow = "dotted_arrow"
    thick = "thick"
    thick_arrow = "thick_arrow"
    invisible = "invisible"

class ArrowType(Enum):
    """Arrow endpoint marker types."""

    none = "none"
    arrow = "arrow"
    circle = "circle"
    cross = "cross"
