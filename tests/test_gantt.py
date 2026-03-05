"""Tests for Gantt chart parser, IR, and renderer."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pytest

from pymermaid import render_diagram
from pymermaid.ir.gantt import GanttChart, GanttSection, GanttTask
from pymermaid.parser.flowchart import ParseError
from pymermaid.parser.gantt import parse_gantt
from pymermaid.render.gantt import render_gantt_svg

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "corpus" / "gantt"


# --- IR dataclass tests ---


class TestGanttIR:
    def test_gantt_task_creation(self):
        task = GanttTask(
            name="Research",
            id="a1",
            modifiers=frozenset({"done"}),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            duration_days=30,
        )
        assert task.name == "Research"
        assert task.id == "a1"
        assert "done" in task.modifiers
        assert task.start_date == date(2024, 1, 1)
        assert task.end_date == date(2024, 1, 31)
        assert task.duration_days == 30

    def test_gantt_section_creation(self):
        t1 = GanttTask("A", "a1", frozenset(), date(2024, 1, 1), date(2024, 1, 10), 9)
        t2 = GanttTask("B", "b1", frozenset(), date(2024, 1, 10), date(2024, 1, 20), 10)
        section = GanttSection(name="Dev", tasks=(t1, t2))
        assert section.name == "Dev"
        assert len(section.tasks) == 2
        assert section.tasks[0].name == "A"

    def test_gantt_chart_creation(self):
        task = GanttTask("X", None, frozenset(), date(2024, 1, 1), date(2024, 1, 5), 4)
        section = GanttSection(name="S1", tasks=(task,))
        chart = GanttChart(title="My Plan", date_format="YYYY-MM-DD", sections=(section,))
        assert chart.title == "My Plan"
        assert chart.date_format == "YYYY-MM-DD"
        assert len(chart.sections) == 1

    def test_frozen_immutability(self):
        task = GanttTask("X", None, frozenset(), date(2024, 1, 1), date(2024, 1, 5), 4)
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
        assert chart.sections[0].tasks[0].name == "Task1"
        assert chart.sections[0].tasks[0].start_date == date(2024, 1, 1)
        assert chart.sections[0].tasks[0].end_date == date(2024, 1, 11)

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
        assert chart.sections[0].name == ""  # default unnamed section
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
        assert task.start_date == date(2024, 1, 1)
        assert task.duration_days == 30
        assert task.end_date == date(2024, 1, 31)

    def test_after_dependency(self):
        source = """gantt
    section S
        A :a1, 2024-01-01, 10d
        B :a2, after a1, 20d
"""
        chart = parse_gantt(source)
        task_b = chart.sections[0].tasks[1]
        assert task_b.start_date == date(2024, 1, 11)
        assert task_b.end_date == date(2024, 1, 31)

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
        assert task.start_date == date(2024, 1, 1)

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
        assert task_b.start_date == date(2024, 1, 11)


# --- Parser: error cases ---


class TestParserErrors:
    def test_empty_input(self):
        with pytest.raises(ParseError):
            parse_gantt("")

    def test_missing_gantt_keyword(self):
        with pytest.raises(ParseError, match="Missing 'gantt' keyword"):
            parse_gantt("title Something\nsection S\n    Task :2024-01-01, 5d")

    def test_unknown_after_reference(self):
        source = """gantt
    section S
        A :a1, after nonexistent, 10d
"""
        with pytest.raises(ParseError, match="Unknown task reference"):
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
    def _simple_chart(self, title: str = "Test Chart") -> GanttChart:
        task = GanttTask("Task1", "t1", frozenset(), date(2024, 1, 1), date(2024, 1, 11), 10)
        section = GanttSection("Section1", (task,))
        return GanttChart(title=title, date_format="YYYY-MM-DD", sections=(section,))

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
        # No <text> element with gantt-title class should be rendered
        assert 'class="gantt-title"' not in svg or '<text' not in svg.split('class="gantt-title"')[0].rsplit('\n', 1)[-1]
        # Simpler: no title text element (check no <text...gantt-title> outside <style>)
        # Remove style block then check
        no_style = re.sub(r'<style>.*?</style>', '', svg, flags=re.DOTALL)
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
        t_short = GanttTask("Short", "s1", frozenset(), date(2024, 1, 1), date(2024, 1, 16), 15)
        t_long = GanttTask("Long", "l1", frozenset(), date(2024, 1, 1), date(2024, 1, 31), 30)
        section = GanttSection("S", (t_short, t_long))
        chart = GanttChart(title="", date_format="YYYY-MM-DD", sections=(section,))
        svg = render_gantt_svg(chart)

        # Extract widths from rect elements with data-task-id
        widths = {}
        for m in re.finditer(r'<rect\s([^>]+)/>', svg):
            attrs = m.group(1)
            id_match = re.search(r'data-task-id="(\w+)"', attrs)
            w_match = re.search(r'width="([\d.]+)"', attrs)
            if id_match and w_match:
                widths[id_match.group(1)] = float(w_match.group(1))

        assert "s1" in widths
        assert "l1" in widths
        # 30d bar should be ~2x the 15d bar
        ratio = widths["l1"] / widths["s1"]
        assert 1.8 < ratio < 2.2


# --- Renderer: modifier styling ---


class TestRendererModifiers:
    def test_distinct_fill_colors(self):
        t_default = GanttTask("Def", "d1", frozenset(), date(2024, 1, 1), date(2024, 1, 11), 10)
        t_crit = GanttTask("Crit", "c1", frozenset({"crit"}), date(2024, 1, 11), date(2024, 1, 21), 10)
        t_done = GanttTask("Done", "dn1", frozenset({"done"}), date(2024, 1, 21), date(2024, 1, 31), 10)
        t_active = GanttTask("Act", "ac1", frozenset({"active"}), date(2024, 1, 31), date(2024, 2, 10), 10)

        section = GanttSection("S", (t_default, t_crit, t_done, t_active))
        chart = GanttChart(title="", date_format="YYYY-MM-DD", sections=(section,))
        svg = render_gantt_svg(chart)

        # Extract fill colors for each task
        fills = {}
        for m in re.finditer(r'<rect\s([^>]+)/>', svg):
            attrs = m.group(1)
            id_match = re.search(r'data-task-id="(\w+)"', attrs)
            fill_match = re.search(r'fill="([^"]+)"', attrs)
            if id_match and fill_match:
                fills[id_match.group(1)] = fill_match.group(1)

        assert fills["d1"] != fills["c1"]  # default != crit
        assert fills["d1"] != fills["dn1"]  # default != done
        assert fills["d1"] != fills["ac1"]  # default != active
        assert fills["c1"] != fills["dn1"]  # crit != done


# --- Renderer: time axis ---


class TestRendererTimeAxis:
    def test_tick_labels_present(self):
        task = GanttTask("T", "t1", frozenset(), date(2024, 1, 1), date(2024, 2, 1), 31)
        section = GanttSection("S", (task,))
        chart = GanttChart(title="", date_format="YYYY-MM-DD", sections=(section,))
        svg = render_gantt_svg(chart)

        # Should contain tick date labels
        assert 'class="gantt-tick"' in svg
        assert "2024-01-01" in svg


# --- Integration: dispatch ---


class TestDispatch:
    def test_render_diagram_gantt(self):
        source = "gantt\n    title Test\n    section S\n        Task1 :t1, 2024-01-01, 10d\n"
        svg = render_diagram(source)
        assert svg.strip().startswith("<svg")
        assert svg.strip().endswith("</svg>")
        assert "Test" in svg


# --- Corpus: fixture rendering ---


class TestCorpusFixtures:
    @pytest.mark.parametrize("fixture", sorted(FIXTURES_DIR.glob("*.mmd")), ids=lambda p: p.stem)
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
        assert t2.start_date == date(2024, 1, 6)


class TestExcludesIgnored:
    def test_excludes_directive_ignored(self):
        source = """gantt
    excludes weekends
    section S
        T :t1, 2024-01-01, 5d
"""
        chart = parse_gantt(source)
        assert len(chart.sections[0].tasks) == 1
