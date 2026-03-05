"""Intermediate representation for Entity-Relationship diagrams.

Defines ERAttributeKey, ERAttribute, EREntity, ERCardinality, ERLineStyle,
ERRelationship, and ERDiagram dataclasses used by the ER diagram parser,
layout, and renderer.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ERAttributeKey(Enum):
    """Attribute key constraint type."""

    NONE = "NONE"
    PK = "PK"
    FK = "FK"
    UK = "UK"


@dataclass(frozen=True)
class ERAttribute:
    """An attribute belonging to an entity."""

    type_str: str
    name: str
    key: ERAttributeKey = ERAttributeKey.NONE


@dataclass(frozen=True)
class EREntity:
    """An entity in the ER diagram."""

    id: str
    attributes: tuple[ERAttribute, ...]


class ERCardinality(Enum):
    """Relationship cardinality markers."""

    EXACTLY_ONE = "EXACTLY_ONE"
    ZERO_OR_ONE = "ZERO_OR_ONE"
    ONE_OR_MORE = "ONE_OR_MORE"
    ZERO_OR_MORE = "ZERO_OR_MORE"


class ERLineStyle(Enum):
    """Relationship line style."""

    SOLID = "SOLID"
    DASHED = "DASHED"


@dataclass(frozen=True)
class ERRelationship:
    """A relationship between two entities."""

    source: str
    target: str
    source_cardinality: ERCardinality
    target_cardinality: ERCardinality
    line_style: ERLineStyle
    label: str


@dataclass(frozen=True)
class ERDiagram:
    """Top-level ER diagram representation."""

    entities: tuple[EREntity, ...]
    relationships: tuple[ERRelationship, ...]


__all__ = [
    "ERAttribute",
    "ERAttributeKey",
    "ERCardinality",
    "ERDiagram",
    "EREntity",
    "ERLineStyle",
    "ERRelationship",
]
