"""Parser for Mermaid gantt chart syntax."""

import re
from datetime import date, timedelta

from merm.ir.gantt import GanttChart, GanttSection, GanttTask
from merm.parser.flowchart import ParseError

# Known modifiers that can appear before id/start in a task line
_MODIFIERS = {"done", "active", "crit"}

# Pattern for duration: integer followed by 'd'
_DURATION_RE = re.compile(r"^(\d+)d$")

# Pattern for ISO date
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Pattern for 'after <id>'
_AFTER_RE = re.compile(r"^after\s+(\S+)$")

def parse_gantt(text: str) -> GanttChart:
    """Parse Mermaid gantt chart syntax into a GanttChart IR.

    Raises ParseError on invalid input.
    """
    if not text or not text.strip():
        raise ParseError("Empty input")

    # Strip %% comments
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.split("%%")[0]
        lines.append(stripped)

    # Find the 'gantt' keyword
    header_idx: int | None = None
    for i, line in enumerate(lines):
        if re.match(r"^\s*gantt\b", line):
            header_idx = i
            break

    if header_idx is None:
        raise ParseError("Missing 'gantt' keyword")

    title = ""
    date_format = "YYYY-MM-DD"

    # Collect sections as list of (name, [task_tuples])
    # task_tuples are raw parsed data before resolving 'after' refs
    sections_raw: list[tuple[str, list[_RawTask]]] = []
    current_section_name = ""
    current_tasks: list[_RawTask] = []

    for i in range(header_idx + 1, len(lines)):
        line = lines[i].strip()
        if not line:
            continue

        # Title directive
        m = re.match(r"^title\s+(.*)", line)
        if m:
            title = m.group(1).strip()
            continue

        # dateFormat directive
        m = re.match(r"^dateFormat\s+(.*)", line)
        if m:
            date_format = m.group(1).strip()
            continue

        # excludes directive (ignored for v1)
        if line.startswith("excludes"):
            continue

        # Section header
        m = re.match(r"^section\s+(.*)", line)
        if m:
            # Save previous section if it has tasks
            if current_tasks:
                sections_raw.append((current_section_name, current_tasks))
                current_tasks = []
            current_section_name = m.group(1).strip()
            continue

        # Try to parse as a task line: "TaskName :fields..."
        if ":" in line:
            raw = _parse_task_line(line, i + 1)
            current_tasks.append(raw)
            continue

        # Ignore unrecognized lines silently

    # Save last section
    if current_tasks:
        sections_raw.append((current_section_name, current_tasks))

    # Resolve 'after' references
    task_registry: dict[str, GanttTask] = {}
    sections: list[GanttSection] = []

    for section_name, raw_tasks in sections_raw:
        resolved: list[GanttTask] = []
        for raw in raw_tasks:
            task = _resolve_task(raw, task_registry)
            if task.id:
                task_registry[task.id] = task
            resolved.append(task)
        sections.append(GanttSection(name=section_name, tasks=tuple(resolved)))

    return GanttChart(
        title=title,
        date_format=date_format,
        sections=tuple(sections),
    )

class _RawTask:
    """Intermediate representation of a parsed but unresolved task."""

    __slots__ = ("name", "id", "modifiers", "start_spec", "duration_days", "line_num")

    def __init__(
        self,
        name: str,
        id: str | None,
        modifiers: frozenset[str],
        start_spec: str,  # either ISO date string or 'after <id>'
        duration_days: int,
        line_num: int,
    ) -> None:
        self.name = name
        self.id = id
        self.modifiers = modifiers
        self.start_spec = start_spec
        self.duration_days = duration_days
        self.line_num = line_num

def _parse_task_line(line: str, line_num: int) -> _RawTask:
    """Parse a single task line into a _RawTask.

    Format: TaskName : [modifiers,] [id,] start, duration
    """
    colon_idx = line.index(":")
    task_name = line[:colon_idx].strip()
    fields_str = line[colon_idx + 1:].strip()

    if not task_name:
        raise ParseError("Task name is empty", line=line_num)

    if not fields_str:
        raise ParseError(f"Malformed task line (no fields): {line}", line=line_num)

    fields = [f.strip() for f in fields_str.split(",")]
    fields = [f for f in fields if f]  # remove empty

    if len(fields) < 2:
        raise ParseError(
            f"Malformed task line (need at least start and duration): {line}",
            line=line_num,
        )

    # Last field must be duration
    duration_match = _DURATION_RE.match(fields[-1])
    if not duration_match:
        raise ParseError(
            f"Malformed task line (missing or invalid duration): {line}",
            line=line_num,
        )
    duration_days = int(duration_match.group(1))

    # Second-to-last field must be start (date or 'after <id>')
    start_spec = fields[-2]
    if not _DATE_RE.match(start_spec) and not _AFTER_RE.match(start_spec):
        raise ParseError(
            f"Invalid start specification '{start_spec}' in task line: {line}",
            line=line_num,
        )

    # Remaining fields (before start) are modifiers and/or id
    prefix_fields = fields[:-2]
    modifiers: set[str] = set()
    task_id: str | None = None

    for f in prefix_fields:
        if f in _MODIFIERS:
            modifiers.add(f)
        elif task_id is None:
            # Treat as task id (alphanumeric)
            task_id = f
        else:
            raise ParseError(
                f"Unexpected field '{f}' in task line: {line}",
                line=line_num,
            )

    return _RawTask(
        name=task_name,
        id=task_id,
        modifiers=frozenset(modifiers),
        start_spec=start_spec,
        duration_days=duration_days,
        line_num=line_num,
    )

def _resolve_task(raw: _RawTask, registry: dict[str, GanttTask]) -> GanttTask:
    """Resolve a raw task's start_spec into concrete dates."""
    after_match = _AFTER_RE.match(raw.start_spec)
    if after_match:
        ref_id = after_match.group(1)
        if ref_id not in registry:
            raise ParseError(
                f"Unknown task reference 'after {ref_id}'",
                line=raw.line_num,
            )
        start = registry[ref_id].end_date
    else:
        start = date.fromisoformat(raw.start_spec)

    end = start + timedelta(days=raw.duration_days)

    return GanttTask(
        name=raw.name,
        id=raw.id,
        modifiers=raw.modifiers,
        start_date=start,
        end_date=end,
        duration_days=raw.duration_days,
    )

__all__ = ["parse_gantt"]
