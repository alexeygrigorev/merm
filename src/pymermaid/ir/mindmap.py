"""Intermediate representation for mindmap diagrams."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MindmapShape(Enum):
    """Shape types for mindmap nodes."""

    CIRCLE = "circle"
    ROUNDED_RECT = "rounded_rect"
    RECT = "rect"
    CLOUD = "cloud"
    DEFAULT = "default"


@dataclass(frozen=True)
class MindmapNode:
    """A single node in a mindmap tree."""

    id: str
    label: str
    shape: MindmapShape
    children: tuple[MindmapNode, ...] = ()


@dataclass(frozen=True)
class MindmapDiagram:
    """Top-level mindmap diagram representation."""

    root: MindmapNode


__all__ = ["MindmapDiagram", "MindmapNode", "MindmapShape"]
