"""Tests for API documentation accuracy (issue 80).

Verifies that all documented public API functions exist, have correct
signatures, and behave as documented.
"""

from pathlib import Path

import pytest

import merm
from merm import (
    DEFAULT_THEME,
    ParseError,
    Theme,
    get_theme,
    parse_class_diagram,
    parse_flowchart,
    parse_sequence,
    parse_state_diagram,
    render_diagram,
    render_to_file,
    render_to_png,
)

# ---------------------------------------------------------------------------
# __all__ completeness
# ---------------------------------------------------------------------------


class TestAllExports:
    """Verify that __all__ contains every public symbol documented."""

    def test_all_contains_render_diagram(self):
        assert "render_diagram" in merm.__all__

    def test_all_contains_render_to_file(self):
        assert "render_to_file" in merm.__all__

    def test_all_contains_render_to_png(self):
        assert "render_to_png" in merm.__all__

    def test_all_contains_render_svg(self):
        assert "render_svg" in merm.__all__

    def test_all_contains_theme(self):
        assert "Theme" in merm.__all__

    def test_all_contains_default_theme(self):
        assert "DEFAULT_THEME" in merm.__all__

    def test_all_contains_get_theme(self):
        assert "get_theme" in merm.__all__

    def test_all_contains_parse_error(self):
        assert "ParseError" in merm.__all__

    def test_all_contains_parse_flowchart(self):
        assert "parse_flowchart" in merm.__all__

    def test_all_contains_parse_sequence(self):
        assert "parse_sequence" in merm.__all__

    def test_all_contains_parse_class_diagram(self):
        assert "parse_class_diagram" in merm.__all__

    def test_all_contains_parse_state_diagram(self):
        assert "parse_state_diagram" in merm.__all__


# ---------------------------------------------------------------------------
# Docstrings present on all public functions
# ---------------------------------------------------------------------------


class TestDocstrings:
    """Every public API function must have a docstring."""

    @pytest.mark.parametrize(
        "name",
        [
            "render_diagram",
            "render_to_file",
            "render_to_png",
        ],
    )
    def test_public_function_has_docstring(self, name):
        fn = getattr(merm, name)
        assert fn.__doc__ is not None, f"{name} is missing a docstring"
        assert len(fn.__doc__) > 20, f"{name} docstring is too short"

    def test_theme_class_has_docstring(self):
        assert Theme.__doc__ is not None
        assert len(Theme.__doc__) > 20

    def test_parse_error_has_docstring(self):
        assert ParseError.__doc__ is not None

    def test_get_theme_has_docstring(self):
        assert get_theme.__doc__ is not None


# ---------------------------------------------------------------------------
# render_diagram signature and behavior
# ---------------------------------------------------------------------------


class TestRenderDiagram:
    """Verify render_diagram works as documented."""

    def test_returns_svg_string(self):
        svg = render_diagram("flowchart TD\n    A --> B")
        assert isinstance(svg, str)
        assert "<svg" in svg

    def test_theme_as_string(self):
        svg = render_diagram("flowchart TD\n    A --> B", theme="dark")
        assert "<svg" in svg

    def test_theme_as_instance(self):
        t = Theme(node_fill="#ff0000")
        svg = render_diagram("flowchart TD\n    A --> B", theme=t)
        assert "<svg" in svg

    def test_theme_none_uses_default(self):
        svg = render_diagram("flowchart TD\n    A --> B", theme=None)
        assert "<svg" in svg

    def test_empty_source_raises_value_error(self):
        with pytest.raises(ValueError):
            render_diagram("")

    def test_whitespace_source_raises_value_error(self):
        with pytest.raises(ValueError):
            render_diagram("   \n  ")

    def test_sequence_diagram(self):
        svg = render_diagram("sequenceDiagram\n    Alice->>Bob: Hello")
        assert "<svg" in svg

    def test_class_diagram(self):
        svg = render_diagram("classDiagram\n    class Animal")
        assert "<svg" in svg

    def test_state_diagram(self):
        svg = render_diagram("stateDiagram-v2\n    [*] --> Active")
        assert "<svg" in svg

    def test_er_diagram(self):
        svg = render_diagram(
            "erDiagram\n    CUSTOMER ||--o{ ORDER : places"
        )
        assert "<svg" in svg

    def test_pie_chart(self):
        svg = render_diagram('pie\n    "Dogs" : 40\n    "Cats" : 60')
        assert "<svg" in svg

    def test_mindmap(self):
        svg = render_diagram("mindmap\n  root\n    Child A\n    Child B")
        assert "<svg" in svg

    def test_gantt(self):
        svg = render_diagram(
            "gantt\n    title Plan\n    section A\n"
            "    Task1 :a1, 2024-01-01, 30d"
        )
        assert "<svg" in svg

    def test_gitgraph(self):
        svg = render_diagram('gitGraph\n    commit id: "Init"')
        assert "<svg" in svg

    def test_theme_directive_auto_detected(self):
        source = (
            "%%{init: {'theme': 'dark'}}%%\n"
            "flowchart TD\n    A --> B"
        )
        svg = render_diagram(source)
        assert "<svg" in svg


# ---------------------------------------------------------------------------
# render_to_file
# ---------------------------------------------------------------------------


class TestRenderToFile:
    """Verify render_to_file works as documented."""

    def test_writes_svg_file(self, tmp_path):
        out = tmp_path / "test.svg"
        render_to_file("flowchart TD\n    A --> B", out)
        content = out.read_text()
        assert "<svg" in content

    def test_parent_dir_must_exist(self):
        with pytest.raises(FileNotFoundError):
            render_to_file(
                "flowchart TD\n    A --> B",
                "/nonexistent/dir/out.svg",
            )

    def test_accepts_string_path(self, tmp_path):
        out = str(tmp_path / "test.svg")
        render_to_file("flowchart TD\n    A --> B", out)
        assert Path(out).exists()

    def test_with_theme(self, tmp_path):
        out = tmp_path / "dark.svg"
        render_to_file("flowchart TD\n    A --> B", out, theme="dark")
        assert out.exists()


# ---------------------------------------------------------------------------
# render_to_png
# ---------------------------------------------------------------------------


class TestRenderToPng:
    """Verify render_to_png works as documented."""

    def test_returns_png_bytes(self):
        data = render_to_png("flowchart TD\n    A --> B")
        assert isinstance(data, bytes)
        # PNG magic bytes
        assert data[:4] == b"\x89PNG"

    def test_with_theme(self):
        data = render_to_png("flowchart TD\n    A --> B", theme="forest")
        assert data[:4] == b"\x89PNG"


# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------


class TestTheme:
    """Verify Theme dataclass works as documented."""

    def test_is_frozen(self):
        t = Theme()
        with pytest.raises(AttributeError):
            t.node_fill = "#000000"  # type: ignore[misc]

    def test_default_values(self):
        t = Theme()
        assert t.node_fill == "#ECECFF"
        assert t.node_stroke == "#9370DB"
        assert t.background_color == "white"

    def test_replace_returns_new(self):
        original = Theme()
        modified = original.replace(node_fill="#ff0000")
        assert modified.node_fill == "#ff0000"
        assert original.node_fill == "#ECECFF"  # unchanged

    def test_default_theme_singleton(self):
        assert DEFAULT_THEME.node_fill == "#ECECFF"


# ---------------------------------------------------------------------------
# get_theme
# ---------------------------------------------------------------------------


class TestGetTheme:
    """Verify get_theme works as documented."""

    @pytest.mark.parametrize("name", ["default", "dark", "forest", "neutral"])
    def test_valid_names(self, name):
        t = get_theme(name)
        assert isinstance(t, Theme)

    def test_invalid_name_raises(self):
        with pytest.raises(ValueError):
            get_theme("nonexistent")


# ---------------------------------------------------------------------------
# ParseError
# ---------------------------------------------------------------------------


class TestParseError:
    """Verify ParseError works as documented."""

    def test_is_exception(self):
        assert issubclass(ParseError, Exception)

    def test_has_line_attribute(self):
        e = ParseError("bad syntax", line=5)
        assert e.line == 5

    def test_line_none_by_default(self):
        e = ParseError("bad syntax")
        assert e.line is None

    def test_line_included_in_message(self):
        e = ParseError("bad syntax", line=5)
        assert "Line 5" in str(e)


# ---------------------------------------------------------------------------
# Individual parsers
# ---------------------------------------------------------------------------


class TestParsers:
    """Verify individual parsers are importable and callable."""

    def test_parse_flowchart(self):
        diagram = parse_flowchart("flowchart TD\n    A --> B")
        assert hasattr(diagram, "nodes")
        assert hasattr(diagram, "edges")

    def test_parse_sequence(self):
        diagram = parse_sequence("sequenceDiagram\n    Alice->>Bob: Hi")
        assert diagram is not None

    def test_parse_class_diagram(self):
        diagram = parse_class_diagram("classDiagram\n    class Animal")
        assert diagram is not None

    def test_parse_state_diagram(self):
        diagram = parse_state_diagram(
            "stateDiagram-v2\n    [*] --> Active"
        )
        assert diagram is not None

    def test_parse_er_diagram(self):
        from merm.parser import parse_er_diagram

        diagram = parse_er_diagram(
            "erDiagram\n    CUSTOMER ||--o{ ORDER : places"
        )
        assert diagram is not None

    def test_parse_pie(self):
        from merm.parser.pie import parse_pie

        chart = parse_pie('pie\n    "Dogs" : 40\n    "Cats" : 60')
        assert chart is not None

    def test_parse_gantt(self):
        from merm.parser.gantt import parse_gantt

        chart = parse_gantt(
            "gantt\n    title Plan\n    section A\n"
            "    Task1 :a1, 2024-01-01, 30d"
        )
        assert chart is not None

    def test_parse_mindmap(self):
        from merm.parser.mindmap import parse_mindmap

        diagram = parse_mindmap("mindmap\n  root\n    Child A")
        assert diagram is not None

    def test_parse_gitgraph(self):
        from merm.parser.gitgraph import parse_gitgraph

        graph = parse_gitgraph('gitGraph\n    commit id: "Init"')
        assert graph is not None


# ---------------------------------------------------------------------------
# API docs file exists
# ---------------------------------------------------------------------------


class TestApiDocsFile:
    """Verify the API documentation file exists and covers key items."""

    @pytest.fixture
    def api_doc(self):
        path = Path(__file__).parent.parent / "docs" / "api.md"
        assert path.exists(), "docs/api.md must exist"
        return path.read_text()

    def test_documents_render_diagram(self, api_doc):
        assert "render_diagram" in api_doc

    def test_documents_render_to_file(self, api_doc):
        assert "render_to_file" in api_doc

    def test_documents_render_to_png(self, api_doc):
        assert "render_to_png" in api_doc

    def test_documents_theme(self, api_doc):
        assert "Theme" in api_doc

    def test_documents_parse_error(self, api_doc):
        assert "ParseError" in api_doc

    def test_documents_cli(self, api_doc):
        assert "Command-Line Interface" in api_doc

    def test_documents_all_themes(self, api_doc):
        for name in ["default", "dark", "forest", "neutral"]:
            assert name in api_doc

    def test_documents_all_diagram_types(self, api_doc):
        for dtype in [
            "flowchart",
            "sequenceDiagram",
            "classDiagram",
            "stateDiagram",
            "erDiagram",
            "pie",
            "mindmap",
            "gantt",
            "gitGraph",
        ]:
            assert dtype in api_doc

    def test_documents_cli_flags(self, api_doc):
        for flag in ["--output", "--format", "--theme", "--version", "--help"]:
            assert flag in api_doc

    def test_includes_usage_examples(self, api_doc):
        # Must have code blocks with examples
        assert "```python" in api_doc
        assert "```bash" in api_doc
