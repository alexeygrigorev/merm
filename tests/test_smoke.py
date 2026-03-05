"""Smoke tests for project setup."""

import subprocess


class TestPublicAPI:
    """Test the public API is importable and callable."""

    def test_import_render_svg(self):
        from pymermaid import render_svg

        assert callable(render_svg)

    def test_render_svg_callable(self):
        from pymermaid.render import render_svg

        assert callable(render_svg)


class TestCLI:
    """Test CLI entry point."""

    def test_import_main(self):
        from pymermaid.cli import main

        assert callable(main)

    def test_cli_help(self):
        result = subprocess.run(
            ["uv", "run", "pymermaid", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        output = (result.stdout + result.stderr).lower()
        assert "pymermaid" in output or "usage" in output


class TestSubpackageImports:
    """Test all subpackages are importable."""

    def test_import_parser(self):
        import pymermaid.parser  # noqa: F401

    def test_import_ir(self):
        import pymermaid.ir  # noqa: F401

    def test_import_layout(self):
        import pymermaid.layout  # noqa: F401

    def test_import_measure(self):
        import pymermaid.measure  # noqa: F401

    def test_import_render(self):
        import pymermaid.render  # noqa: F401


class TestCLISubprocess:
    """Integration test: CLI via subprocess using installed entry point."""

    def test_pymermaid_help(self):
        result = subprocess.run(
            ["uv", "run", "pymermaid", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        output = (result.stdout + result.stderr).lower()
        assert "pymermaid" in output or "usage" in output
