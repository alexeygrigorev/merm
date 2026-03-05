"""Intermediate representation for diagram graphs."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


def _hash_dict(d: dict | None) -> int:
    """Return a stable hash for a dict (or None) by converting to sorted items tuple."""
    if d is None:
        return hash(None)
    return hash(tuple(sorted(d.items())))


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


@dataclass(frozen=True)
class Node:
    """A node in the diagram graph."""

    id: str
    label: str
    shape: NodeShape = NodeShape.rect
    css_classes: tuple[str, ...] = ()
    inline_style: dict[str, str] | None = None

    def __hash__(self) -> int:
        return hash((
            self.id, self.label, self.shape,
            self.css_classes, _hash_dict(self.inline_style),
        ))


@dataclass(frozen=True)
class Edge:
    """An edge connecting two nodes."""

    source: str
    target: str
    label: str | None = None
    edge_type: EdgeType = EdgeType.arrow
    source_arrow: ArrowType = ArrowType.none
    target_arrow: ArrowType = ArrowType.arrow
    extra_length: int = 0


@dataclass(frozen=True)
class StyleDef:
    """A style definition targeting a node or class."""

    target_id: str
    properties: dict[str, str] = field(default_factory=dict)

    def __hash__(self) -> int:
        return hash((self.target_id, _hash_dict(self.properties)))


@dataclass(frozen=True)
class Subgraph:
    """A subgraph grouping nodes together."""

    id: str
    title: str | None = None
    direction: Direction | None = None
    node_ids: tuple[str, ...] = ()
    subgraphs: tuple[Subgraph, ...] = ()


@dataclass(frozen=True)
class Diagram:
    """Top-level diagram representation."""

    type: DiagramType = DiagramType.flowchart
    direction: Direction = Direction.TB
    nodes: tuple[Node, ...] = ()
    edges: tuple[Edge, ...] = ()
    subgraphs: tuple[Subgraph, ...] = ()
    styles: tuple[StyleDef, ...] = ()
    classes: dict[str, dict[str, str]] = field(default_factory=dict)

    def __hash__(self) -> int:
        classes_hash = hash(
            tuple(
                sorted(
                    (k, tuple(sorted(v.items())))
                    for k, v in self.classes.items()
                )
            )
        )
        return hash((
            self.type,
            self.direction,
            self.nodes,
            self.edges,
            self.subgraphs,
            self.styles,
            classes_hash,
        ))


__all__ = [
    "ArrowType",
    "Diagram",
    "DiagramType",
    "Direction",
    "Edge",
    "EdgeType",
    "Node",
    "NodeShape",
    "StyleDef",
    "Subgraph",
]
