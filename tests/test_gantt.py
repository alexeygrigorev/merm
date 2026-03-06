"""Tests for Gantt chart parser, IR, and renderer."""

import re
from datetime import date
from pathlib import Path

import pytest

from merm import render_diagram
from merm.ir.gantt import GanttChart, GanttSection, GanttTask
from merm.parser.flowchart import ParseError
from merm.parser.gantt import parse_gantt
from merm.render.gantt import render_gantt_svg

FIXTURES_DIR = (
    Path(__file__).parent / "fixtures" / "corpus" / "gantt"
)

D = date  # short alias for readability

def _task(
    name: str = "T",
    tid: str | None = None,
    mods: frozenset[str] | None = None,
    start: date = D(2024, 1, 1),
    end: date = D(2024, 1, 11),
    days: int = 10,
) -> GanttTask:
    """Helper to build a GanttTask concisely."""
    return GanttTask(
        name=name,
        id=tid,
        modifiers=mods or frozenset(),
        start_date=start,
        end_date=end,
        duration_days=days,
    )

def _extract_rect_attrs(svg: str) -> dict[str, dict[str, str]]:
    """Extract {task_id: {attr: value}} from rect elements."""
    result: dict[str, dict[str, str]] = {}
    for m in re.finditer(r"<rect\s([^>]+)/>", svg):
        attrs_str = m.group(1)
        id_m = re.search(r'data-task-id="(\w+)"', attrs_str)
        if not id_m:
            continue
        tid = id_m.group(1)
        attrs: dict[str, str] = {}
        for am in re.finditer(r'(\w[\w-]*)="([^"]*)"', attrs_str):
            attrs[am.group(1)] = am.group(2)
        result[tid] = attrs
    return result

# --- IR dataclass tests ---

class TestGanttIR:
    def test_gantt_task_creation(self):
        task = GanttTask(
            name="Research",
            id="a1",
            modifiers=frozenset({"done"}),
            start_date=D(2024, 1, 1),
            end_date=D(2024, 1, 31),
            duration_days=30,
        )
        assert task.name == "Research"
        assert task.id == "a1"
        assert "done" in task.modifiers
        assert task.start_date == D(2024, 1, 1)
        assert task.end_date == D(2024, 1, 31)
        assert task.duration_days == 30

    def test_gantt_section_creation(self):
        t1 = _task("A", "a1", days=9, end=D(2024, 1, 10))
        t2 = _task(
            "B", "b1", days=10,
            start=D(2024, 1, 10), end=D(2024, 1, 20),
        )
        section = GanttSection(name="Dev", tasks=(t1, t2))
        assert section.name == "Dev"
        assert len(section.tasks) == 2
        assert section.tasks[0].name == "A"

    def test_gantt_chart_creation(self):
        task = _task("X", days=4, end=D(2024, 1, 5))
        section = GanttSection(name="S1", tasks=(task,))
        chart = GanttChart(
            title="My Plan",
            date_format="YYYY-MM-DD",
            sections=(section,),
        )
        assert chart.title == "My Plan"
        assert chart.date_format == "YYYY-MM-DD"
        assert len(chart.sections) == 1

    def test_frozen_immutability(self):
        task = _task("X", days=4, end=D(2024, 1, 5))
        with pytest.raises(AttributeError):
            task.name = "changed"  # type: ignore[misc]

# --- Parser: basic parsing ---

class TestParserBasic:
    def test_minimal_gantt(self):
        source = """gantt
    section S1
        Task1 :t1, 2024-01-01, 10d
"""
        chart = parse_gantt(source)
        assert len(chart.sections) == 1
        assert chart.sections[0].name == "S1"
        t = chart.sections[0].tasks[0]
        assert t.name == "Task1"
        assert t.start_date == D(2024, 1, 1)
        assert t.end_date == D(2024, 1, 11)

    def test_title_directive(self):
        source = """gantt
    title My Project
    section S
        T :t1, 2024-01-01, 5d
"""
        chart = parse_gantt(source)
        assert chart.title == "My Project"

    def test_date_format_directive(self):
        source = """gantt
    dateFormat YYYY-MM-DD
    section S
        T :t1, 2024-01-01, 5d
"""
        chart = parse_gantt(source)
        assert chart.date_format == "YYYY-MM-DD"

    def test_no_title(self):
        source = """gantt
    section S
        T :t1, 2024-01-01, 5d
"""
        chart = parse_gantt(source)
        assert chart.title == ""

    def test_tasks_without_section(self):
        source = """gantt
    title No Section
        TaskA :a1, 2024-01-01, 10d
"""
        chart = parse_gantt(source)
        assert len(chart.sections) == 1
        # default unnamed section
        assert chart.sections[0].name == ""
        assert chart.sections[0].tasks[0].name == "TaskA"

# --- Parser: task line variants ---

class TestParserTaskVariants:
    def test_explicit_date_and_duration(self):
        source = """gantt
    section S
        Research :a1, 2024-01-01, 30d
"""
        chart = parse_gantt(source)
        task = chart.sections[0].tasks[0]
        assert task.id == "a1"
        assert task.start_date == D(2024, 1, 1)
        assert task.duration_days == 30
        assert task.end_date == D(2024, 1, 31)

    def test_after_dependency(self):
        source = """gantt
    section S
        A :a1, 2024-01-01, 10d
        B :a2, after a1, 20d
"""
        chart = parse_gantt(source)
        task_b = chart.sections[0].tasks[1]
        assert task_b.start_date == D(2024, 1, 11)
        assert task_b.end_date == D(2024, 1, 31)

    def test_modifiers(self):
        source = """gantt
    section S
        Backend :crit, done, b1, 2024-02-01, 10d
"""
        chart = parse_gantt(source)
        task = chart.sections[0].tasks[0]
        assert "crit" in task.modifiers
        assert "done" in task.modifiers
        assert task.id == "b1"

    def test_task_without_id(self):
        source = """gantt
    section S
        Simple Task :2024-01-01, 5d
"""
        chart = parse_gantt(source)
        task = chart.sections[0].tasks[0]
        assert task.id is None
        assert task.name == "Simple Task"
        assert task.start_date == D(2024, 1, 1)

    def test_task_no_id_no_modifiers(self):
        source = """gantt
    section S
        Basic :2024-03-15, 7d
"""
        chart = parse_gantt(source)
        task = chart.sections[0].tasks[0]
        assert task.id is None
        assert task.modifiers == frozenset()
        assert task.duration_days == 7

    def test_modifier_with_after(self):
        source = """gantt
    section S
        A :a1, 2024-01-01, 10d
        B :active, b1, after a1, 5d
"""
        chart = parse_gantt(source)
        task_b = chart.sections[0].tasks[1]
        assert "active" in task_b.modifiers
        assert task_b.start_date == D(2024, 1, 11)

# --- Parser: error cases ---

class TestParserErrors:
    def test_empty_input(self):
        with pytest.raises(ParseError):
            parse_gantt("")

    def test_missing_gantt_keyword(self):
        with pytest.raises(
            ParseError, match="Missing 'gantt' keyword"
        ):
            parse_gantt(
                "title Something\n"
                "section S\n"
                "    Task :2024-01-01, 5d"
            )

    def test_unknown_after_reference(self):
        source = """gantt
    section S
        A :a1, after nonexistent, 10d
"""
        with pytest.raises(
            ParseError, match="Unknown task reference"
        ):
            parse_gantt(source)

    def test_malformed_task_missing_duration(self):
        source = """gantt
    section S
        Bad :2024-01-01
"""
        with pytest.raises(ParseError):
            parse_gantt(source)

    def test_malformed_task_bad_duration(self):
        source = """gantt
    section S
        Bad :2024-01-01, xyz
"""
        with pytest.raises(ParseError):
            parse_gantt(source)

# --- Parser: comments ---

class TestParserComments:
    def test_comments_stripped(self):
        source = """gantt
    %% This is a comment
    title With Comments
    section S
        Task1 :t1, 2024-01-01, 10d  %% inline comment
"""
        chart = parse_gantt(source)
        assert chart.title == "With Comments"
        assert len(chart.sections[0].tasks) == 1

# --- Renderer: SVG structure ---

class TestRendererStructure:
    def _simple_chart(
        self, title: str = "Test Chart",
    ) -> GanttChart:
        task = _task("Task1", "t1")
        section = GanttSection("Section1", (task,))
        return GanttChart(
            title=title,
            date_format="YYYY-MM-DD",
            sections=(section,),
        )

    def test_svg_wrapper(self):
        svg = render_gantt_svg(self._simple_chart())
        assert svg.strip().startswith("<svg")
        assert svg.strip().endswith("</svg>")

    def test_title_present(self):
        svg = render_gantt_svg(self._simple_chart("My Gantt"))
        assert "My Gantt" in svg
        assert 'class="gantt-title"' in svg

    def test_title_absent_when_empty(self):
        svg = render_gantt_svg(self._simple_chart(""))
        # Remove style block, then check no title element
        no_style = re.sub(
            r"<style>.*?</style>", "", svg, flags=re.DOTALL
        )
        assert "gantt-title" not in no_style

    def test_task_rect_with_data_id(self):
        svg = render_gantt_svg(self._simple_chart())
        assert 'data-task-id="t1"' in svg
        assert "<rect" in svg

    def test_section_label_present(self):
        svg = render_gantt_svg(self._simple_chart())
        assert "Section1" in svg

# --- Renderer: proportional bar widths ---

class TestRendererProportions:
    def test_wider_bar_for_longer_task(self):
        t_short = _task(
            "Short", "s1", days=15, end=D(2024, 1, 16),
        )
        t_long = _task(
            "Long", "l1", days=30, end=D(2024, 1, 31),
        )
        section = GanttSection("S", (t_short, t_long))
        chart = GanttChart(
            title="",
            date_format="YYYY-MM-DD",
            sections=(section,),
        )
        svg = render_gantt_svg(chart)

        rects = _extract_rect_attrs(svg)
        assert "s1" in rects
        assert "l1" in rects
        w_short = float(rects["s1"]["width"])
        w_long = float(rects["l1"]["width"])
        # 30d bar should be ~2x the 15d bar
        ratio = w_long / w_short
        assert 1.8 < ratio < 2.2

# --- Renderer: modifier styling ---

class TestRendererModifiers:
    def test_distinct_fill_colors(self):
        t_def = _task("Def", "d1")
        t_crit = _task(
            "Crit", "c1",
            mods=frozenset({"crit"}),
            start=D(2024, 1, 11), end=D(2024, 1, 21),
        )
        t_done = _task(
            "Done", "dn1",
            mods=frozenset({"done"}),
            start=D(2024, 1, 21), end=D(2024, 1, 31),
        )
        t_active = _task(
            "Act", "ac1",
            mods=frozenset({"active"}),
            start=D(2024, 1, 31), end=D(2024, 2, 10),
        )

        section = GanttSection(
            "S", (t_def, t_crit, t_done, t_active),
        )
        chart = GanttChart(
            title="",
            date_format="YYYY-MM-DD",
            sections=(section,),
        )
        svg = render_gantt_svg(chart)

        rects = _extract_rect_attrs(svg)
        fills = {k: v["fill"] for k, v in rects.items()}

        assert fills["d1"] != fills["c1"]
        assert fills["d1"] != fills["dn1"]
        assert fills["d1"] != fills["ac1"]
        assert fills["c1"] != fills["dn1"]

# --- Renderer: time axis ---

class TestRendererTimeAxis:
    def test_tick_labels_present(self):
        task = _task(
            "T", "t1", days=31,
            end=D(2024, 2, 1),
        )
        section = GanttSection("S", (task,))
        chart = GanttChart(
            title="",
            date_format="YYYY-MM-DD",
            sections=(section,),
        )
        svg = render_gantt_svg(chart)

        assert 'class="gantt-tick"' in svg
        assert "2024-01-01" in svg

# --- Integration: dispatch ---

class TestDispatch:
    def test_render_diagram_gantt(self):
        source = (
            "gantt\n"
            "    title Test\n"
            "    section S\n"
            "        Task1 :t1, 2024-01-01, 10d\n"
        )
        svg = render_diagram(source)
        assert svg.strip().startswith("<svg")
        assert svg.strip().endswith("</svg>")
        assert "Test" in svg

# --- Corpus: fixture rendering ---

class TestCorpusFixtures:
    @pytest.mark.parametrize(
        "fixture",
        sorted(FIXTURES_DIR.glob("*.mmd")),
        ids=lambda p: p.stem,
    )
    def test_fixture_renders(self, fixture: Path):
        source = fixture.read_text()
        svg = render_diagram(source)
        assert svg.strip().startswith("<svg")
        assert svg.strip().endswith("</svg>")

# --- Additional edge case tests ---

class TestMultipleSections:
    def test_multiple_sections_parsed(self):
        source = """gantt
    title Multi
    section A
        T1 :a1, 2024-01-01, 5d
    section B
        T2 :b1, 2024-02-01, 10d
"""
        chart = parse_gantt(source)
        assert len(chart.sections) == 2
        assert chart.sections[0].name == "A"
        assert chart.sections[1].name == "B"

    def test_cross_section_after_reference(self):
        source = """gantt
    section A
        T1 :a1, 2024-01-01, 5d
    section B
        T2 :b1, after a1, 10d
"""
        chart = parse_gantt(source)
        t2 = chart.sections[1].tasks[0]
        assert t2.start_date == D(2024, 1, 6)

class TestDateRangeFormat:
    """Tasks specified with start_date, end_date instead of duration."""

    def test_date_range_basic(self):
        source = """gantt
    section S
        Task1 :t1, 2014-01-06, 2014-01-08
"""
        chart = parse_gantt(source)
        task = chart.sections[0].tasks[0]
        assert task.start_date == D(2014, 1, 6)
        assert task.end_date == D(2014, 1, 8)
        assert task.duration_days == 2

    def test_date_range_with_modifiers(self):
        source = """gantt
    section S
        Completed :done, des1, 2014-01-06, 2014-01-08
"""
        chart = parse_gantt(source)
        task = chart.sections[0].tasks[0]
        assert "done" in task.modifiers
        assert task.id == "des1"
        assert task.start_date == D(2014, 1, 6)
        assert task.end_date == D(2014, 1, 8)

    def test_mixed_duration_and_date_range(self):
        """Same chart can mix duration and date-range formats."""
        source = """gantt
    section S
        A :done, a1, 2014-01-06, 2014-01-08
        B :active, b1, 2014-01-07, 3d
        C :c1, after a1, 1d
"""
        chart = parse_gantt(source)
        tasks = chart.sections[0].tasks
        assert tasks[0].duration_days == 2
        assert tasks[1].duration_days == 3
        assert tasks[2].start_date == D(2014, 1, 8)

    def test_mermaid_readme_example(self):
        """The exact gantt example from mermaid.js README."""
        source = (FIXTURES_DIR / "mermaid_readme.mmd").read_text()
        chart = parse_gantt(source)
        assert len(chart.sections) == 1
        assert len(chart.sections[0].tasks) == 6
        # First task uses date range format
        t0 = chart.sections[0].tasks[0]
        assert t0.start_date == D(2014, 1, 6)
        assert t0.end_date == D(2014, 1, 8)

    def test_date_range_renders(self):
        source = """gantt
    section S
        Task1 :t1, 2024-01-01, 2024-01-15
"""
        svg = render_diagram(source)
        assert "<svg" in svg
        assert 'data-task-id="t1"' in svg


class TestExcludesIgnored:
    def test_excludes_directive_ignored(self):
        source = """gantt
    excludes weekends
    section S
        T :t1, 2024-01-01, 5d
"""
        chart = parse_gantt(source)
        assert len(chart.sections[0].tasks) == 1
