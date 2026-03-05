"""Intermediate representation for Gantt charts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class GanttTask:
    """A single task in a Gantt chart."""

    name: str
    id: str | None  # optional identifier like 'a1'
    modifiers: frozenset[str]  # e.g. {'done', 'crit', 'active'}
    start_date: date
    end_date: date
    duration_days: int


@dataclass(frozen=True)
class GanttSection:
    """A named section containing tasks."""

    name: str
    tasks: tuple[GanttTask, ...]


@dataclass(frozen=True)
class GanttChart:
    """Top-level Gantt chart representation."""

    title: str  # empty string if no title
    date_format: str  # e.g. 'YYYY-MM-DD'
    sections: tuple[GanttSection, ...]


__all__ = ["GanttChart", "GanttSection", "GanttTask"]
