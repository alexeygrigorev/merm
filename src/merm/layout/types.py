"""Layout data structures.

Defines Point, NodeLayout, EdgeLayout, SubgraphLayout, and LayoutResult
dataclasses used as input/output of the layout algorithm.
"""

from dataclasses import dataclass

@dataclass(frozen=True)
class Point:
    """A 2D point."""

    x: float
    y: float

@dataclass(frozen=True)
class NodeLayout:
    """Positioned node with dimensions."""

    x: float
    y: float
    width: float
    height: float

@dataclass(frozen=True)
class EdgeLayout:
    """Routed edge as a polyline."""

    points: list[Point]
    source: str
    target: str

@dataclass(frozen=True)
class SubgraphLayout:
    """Bounding box for a laid-out subgraph."""

    id: str
    x: float
    y: float
    width: float
    height: float
    title: str | None = None

@dataclass(frozen=True)
class LayoutResult:
    """Complete layout output."""

    nodes: dict[str, NodeLayout]
    edges: list[EdgeLayout]
    width: float
    height: float
    subgraphs: dict[str, SubgraphLayout] | None = None
