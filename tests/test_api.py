"""Tests for the public Python API (issue 76)."""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FLOWCHART_SRC = "graph LR\n  A --> B"
SEQUENCE_SRC = "sequenceDiagram\n  Alice->>Bob: Hello"
CLASS_SRC = "classDiagram\n  class Animal"
STATE_SRC = "stateDiagram-v2\n  [*] --> Still"


# ---------------------------------------------------------------------------
# render_to_file -- SVG
# ---------------------------------------------------------------------------


class TestRenderToFileSvg:
    def test_flowchart_svg(self, tmp_path: Path) -> None:
        from merm import render_to_file

        out = tmp_path / "flowchart.svg"
        render_to_file(FLOWCHART_SRC, out)
        content = out.read_text()
        assert "<svg" in content

    def test_sequence_svg(self, tmp_path: Path) -> None:
        from merm import render_to_file

        out = tmp_path / "seq.svg"
        render_to_file(SEQUENCE_SRC, out)
        content = out.read_text()
        assert "<svg" in content

    def test_accepts_str_path(self, tmp_path: Path) -> None:
        from merm import render_to_file

        out = str(tmp_path / "str_path.svg")
        render_to_file(FLOWCHART_SRC, out)
        assert Path(out).exists()
        assert "<svg" in Path(out).read_text()

    def test_accepts_pathlib_path(self, tmp_path: Path) -> None:
        from merm import render_to_file

        out = tmp_path / "pathlib_path.svg"
        render_to_file(FLOWCHART_SRC, out)
        assert out.exists()


# ---------------------------------------------------------------------------
# render_to_file -- PNG
# ---------------------------------------------------------------------------


class TestRenderToFilePng:
    def test_flowchart_png_magic_bytes(self, tmp_path: Path) -> None:
        from merm import render_to_file

        out = tmp_path / "flowchart.png"
        render_to_file(FLOWCHART_SRC, out)
        data = out.read_bytes()
        assert data[:4] == b"\x89PNG"

    def test_sequence_png_nonempty(self, tmp_path: Path) -> None:
        from merm import render_to_file

        out = tmp_path / "seq.png"
        render_to_file(SEQUENCE_SRC, out)
        assert out.stat().st_size > 0


# ---------------------------------------------------------------------------
# render_to_file -- errors
# ---------------------------------------------------------------------------


class TestRenderToFileErrors:
    def test_parent_dir_not_exists(self) -> None:
        from merm import render_to_file

        with pytest.raises(FileNotFoundError):
            render_to_file(FLOWCHART_SRC, "/nonexistent/dir/out.svg")

    def test_png_without_cairosvg(self, tmp_path: Path) -> None:
        from merm import render_to_file

        with mock.patch.dict("sys.modules", {"cairosvg": None}):
            # Force re-import to hit the ImportError
            with pytest.raises(ImportError, match="cairosvg"):
                render_to_file(FLOWCHART_SRC, tmp_path / "out.png")


# ---------------------------------------------------------------------------
# render_to_png
# ---------------------------------------------------------------------------


class TestRenderToPng:
    def test_returns_bytes_with_png_header(self) -> None:
        from merm import render_to_png

        result = render_to_png(FLOWCHART_SRC)
        assert isinstance(result, bytes)
        assert result[:4] == b"\x89PNG"

    def test_empty_source_raises(self) -> None:
        from merm import render_to_png

        with pytest.raises(ValueError, match="[Ee]mpty"):
            render_to_png("")


# ---------------------------------------------------------------------------
# Re-exported parsers
# ---------------------------------------------------------------------------


class TestReExportedParsers:
    def test_parse_flowchart(self) -> None:
        from merm import parse_flowchart

        result = parse_flowchart(FLOWCHART_SRC)
        assert result is not None

    def test_parse_sequence(self) -> None:
        from merm import parse_sequence

        result = parse_sequence(SEQUENCE_SRC)
        assert result is not None

    def test_parse_class_diagram(self) -> None:
        from merm import parse_class_diagram

        result = parse_class_diagram(CLASS_SRC)
        assert result is not None

    def test_parse_state_diagram(self) -> None:
        from merm import parse_state_diagram

        result = parse_state_diagram(STATE_SRC)
        assert result is not None

    def test_parse_error_importable(self) -> None:
        from merm import ParseError

        assert issubclass(ParseError, Exception)

    def test_parse_error_catchable(self) -> None:
        from merm import ParseError, parse_flowchart

        with pytest.raises(ParseError):
            parse_flowchart("totally invalid %%%")


# ---------------------------------------------------------------------------
# Error messages
# ---------------------------------------------------------------------------


class TestErrorMessages:
    def test_empty_string(self) -> None:
        from merm import render_diagram

        with pytest.raises(ValueError, match="[Ee]mpty"):
            render_diagram("")

    def test_whitespace_only(self) -> None:
        from merm import render_diagram

        with pytest.raises(ValueError, match="[Ee]mpty"):
            render_diagram("   \n  ")


# ---------------------------------------------------------------------------
# __all__ completeness
# ---------------------------------------------------------------------------


class TestAllCompleteness:
    def test_all_items_importable(self) -> None:
        import merm

        for name in merm.__all__:
            assert hasattr(merm, name), f"{name} in __all__ but not importable"

    def test_required_names_in_all(self) -> None:
        import merm

        required = {
            "render_diagram",
            "render_svg",
            "render_to_file",
            "render_to_png",
            "ParseError",
            "parse_flowchart",
            "parse_sequence",
            "parse_class_diagram",
            "parse_state_diagram",
        }
        missing = required - set(merm.__all__)
        assert not missing, f"Missing from __all__: {missing}"


# ---------------------------------------------------------------------------
# Integration: round-trip
# ---------------------------------------------------------------------------


class TestIntegrationRoundTrip:
    def test_render_to_png_round_trip(self) -> None:
        from merm import render_to_png

        data = render_to_png("graph LR\n  A --> B")
        assert len(data) > 0
        assert data[:4] == b"\x89PNG"

    def test_png_file_round_trip(self, tmp_path: Path) -> None:
        from merm import render_to_file

        out = tmp_path / "round_trip.png"
        render_to_file("graph LR\n  A --> B", out)
        data = out.read_bytes()
        assert data[:4] == b"\x89PNG"
