"""Intermediate representation for pie charts."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PieSlice:
    """A single slice in a pie chart."""

    label: str
    value: float


@dataclass(frozen=True)
class PieChart:
    """Top-level pie chart representation."""

    title: str  # empty string if no title
    show_data: bool  # whether showData was specified
    slices: tuple[PieSlice, ...]


__all__ = ["PieChart", "PieSlice"]
