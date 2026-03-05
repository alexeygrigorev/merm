"""Intermediate representation for UML class diagrams.

Defines Visibility, ClassMember, ClassNode, RelationType, ClassRelation,
and ClassDiagram dataclasses used by the class diagram parser, layout,
and renderer.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Visibility(Enum):
    """Member visibility modifiers."""

    PUBLIC = "+"
    PRIVATE = "-"
    PROTECTED = "#"
    PACKAGE = "~"


@dataclass(frozen=True)
class ClassMember:
    """A field or method belonging to a class."""

    name: str
    type_str: str  # return type or field type
    visibility: Visibility
    is_method: bool  # True if has ()


@dataclass(frozen=True)
class ClassNode:
    """A class in the diagram."""

    id: str
    label: str
    annotation: str | None  # <<interface>>, <<abstract>>, etc.
    members: tuple[ClassMember, ...]


class RelationType(Enum):
    """UML relationship types between classes."""

    INHERITANCE = "inheritance"       # <|--
    COMPOSITION = "composition"       # *--
    AGGREGATION = "aggregation"       # o--
    ASSOCIATION = "association"       # -->
    DEPENDENCY = "dependency"         # ..>
    REALIZATION = "realization"       # ..|>


@dataclass(frozen=True)
class ClassRelation:
    """A relationship between two classes."""

    source: str
    target: str
    rel_type: RelationType
    label: str = ""
    source_cardinality: str = ""
    target_cardinality: str = ""


@dataclass(frozen=True)
class ClassDiagram:
    """Top-level class diagram representation."""

    classes: tuple[ClassNode, ...]
    relations: tuple[ClassRelation, ...]


__all__ = [
    "ClassDiagram",
    "ClassMember",
    "ClassNode",
    "ClassRelation",
    "RelationType",
    "Visibility",
]
