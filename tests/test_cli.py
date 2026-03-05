"""Tests for the pymermaid CLI."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

# Helper to invoke the CLI as a subprocess.
CLI = [sys.executable, "-m", "pymermaid.cli"]


def run_cli(
    args: list[str] | None = None,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run the pymermaid CLI and return the CompletedProcess."""
    cmd = CLI + (args or [])
    return subprocess.run(
        cmd,
        input=input_text,
        capture_output=True,
        text=True,
        timeout=30,
    )


# ---- Argument parsing tests ----


def test_version():
    """--version prints version string containing '0.1.0' and exits 0."""
    result = run_cli(["--version"])
    assert result.returncode == 0
    assert "0.1.0" in result.stdout


def test_help():
    """--help exits 0 and output contains -i, -o, and --version."""
    result = run_cli(["--help"])
    assert result.returncode == 0
    assert "-i" in result.stdout
    assert "-o" in result.stdout
    assert "--version" in result.stdout


# ---- File input rendering ----


def test_file_input_file_output():
    """CLI reads .mmd file, renders SVG to output file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        infile = Path(tmpdir) / "test.mmd"
        outfile = Path(tmpdir) / "test.svg"
        infile.write_text("graph LR\n    A --> B")

        result = run_cli(["-i", str(infile), "-o", str(outfile)])
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert outfile.exists()

        svg = outfile.read_text()
        assert "<svg" in svg
        assert 'data-node-id="A"' in svg
        assert 'data-node-id="B"' in svg


def test_file_input_stdout():
    """-i without -o sends SVG to stdout."""
    with tempfile.TemporaryDirectory() as tmpdir:
        infile = Path(tmpdir) / "test.mmd"
        infile.write_text("graph LR\n    A --> B")

        result = run_cli(["-i", str(infile)])
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "<svg" in result.stdout
        assert 'data-node-id="A"' in result.stdout
        assert 'data-node-id="B"' in result.stdout


# ---- Stdin to stdout ----


def test_stdin_to_stdout():
    """Piping mermaid text on stdin produces SVG on stdout."""
    result = run_cli(input_text="graph LR\n    A --> B")
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "<svg" in result.stdout
    assert 'data-node-id="A"' in result.stdout
    assert 'data-node-id="B"' in result.stdout


# ---- Stdin to file ----


def test_stdin_to_file():
    """Stdin input with -o writes SVG to file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        outfile = Path(tmpdir) / "out.svg"
        result = run_cli(
            ["-o", str(outfile)],
            input_text="graph TD\n    X --> Y",
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert outfile.exists()

        svg = outfile.read_text()
        assert "<svg" in svg
        assert 'data-node-id="X"' in svg
        assert 'data-node-id="Y"' in svg


# ---- Error handling: file not found ----


def test_file_not_found():
    """Missing input file exits with code 2 and prints error to stderr."""
    result = run_cli(["-i", "/nonexistent/path.mmd"])
    assert result.returncode == 2
    assert "error" in result.stderr.lower()


# ---- Error handling: parse error ----


def test_parse_error():
    """Invalid mermaid syntax exits with code 1 and prints parse error to stderr."""
    result = run_cli(input_text="this is not mermaid")
    assert result.returncode == 1
    assert "error" in result.stderr.lower()


# ---- Error handling: output directory does not exist ----


def test_output_dir_not_found():
    """Writing to a nonexistent directory exits with code 2 and prints error."""
    result = run_cli(
        ["-o", "/nonexistent/dir/out.svg"],
        input_text="graph LR\n    A --> B",
    )
    assert result.returncode == 2
    assert "error" in result.stderr.lower()


# ---- Integration: pipe chain ----


def test_pipe_chain():
    """echo 'graph LR; A-->B' | pymermaid produces valid SVG."""
    result = subprocess.run(
        CLI,
        input="graph LR\n    A --> B",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "<svg" in result.stdout
    assert 'data-node-id="A"' in result.stdout


# ---- Additional: entry point script works ----


def test_entry_point_script():
    """The installed 'pymermaid' script entry point works."""
    result = subprocess.run(
        ["uv", "run", "pymermaid", "--version"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0
    assert "0.1.0" in result.stdout
