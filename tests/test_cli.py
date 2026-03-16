"""Tests for the merm CLI."""

import subprocess
import sys
import tempfile
from pathlib import Path

# Helper to invoke the CLI as a subprocess.
CLI = [sys.executable, "-m", "merm.cli"]

FLOWCHART = "graph LR\n    A --> B"
SEQUENCE = "sequenceDiagram\n    Alice->>Bob: Hello"
CLASS = "classDiagram\n    class Animal"
STATE = "stateDiagram-v2\n    [*] --> Active"


def run_cli(
    args: list[str] | None = None,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run the merm CLI and return the CompletedProcess."""
    cmd = CLI + (args or [])
    return subprocess.run(
        cmd,
        input=input_text,
        capture_output=True,
        text=True,
        timeout=30,
    )


def run_cli_binary(
    args: list[str] | None = None,
    input_bytes: bytes | None = None,
) -> subprocess.CompletedProcess[bytes]:
    """Run the merm CLI in binary mode (for PNG stdout tests)."""
    cmd = CLI + (args or [])
    return subprocess.run(
        cmd,
        input=input_bytes,
        capture_output=True,
        timeout=30,
    )


# ---- Argument parsing tests ----

def test_version():
    """--version prints version string and exits 0."""
    from merm.__version__ import __version__
    result = run_cli(["--version"])
    assert result.returncode == 0
    assert __version__ in result.stdout


def test_help():
    """--help exits 0 and output contains -i, -o, -f, and --version."""
    result = run_cli(["--help"])
    assert result.returncode == 0
    assert "-i" in result.stdout
    assert "-o" in result.stdout
    assert "-f" in result.stdout
    assert "--format" in result.stdout
    assert "--version" in result.stdout
    # Positional argument should be shown
    assert "input_file" in result.stdout


# ---- Positional input argument ----

def test_positional_input_file_output():
    """merm input.mmd -o output.svg reads file and writes SVG."""
    with tempfile.TemporaryDirectory() as tmpdir:
        infile = Path(tmpdir) / "test.mmd"
        outfile = Path(tmpdir) / "test.svg"
        infile.write_text(FLOWCHART)

        result = run_cli([str(infile), "-o", str(outfile)])
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert outfile.exists()

        svg = outfile.read_text()
        assert "<svg" in svg
        assert 'data-node-id="A"' in svg
        assert 'data-node-id="B"' in svg


def test_positional_input_stdout():
    """merm input.mmd outputs SVG to stdout."""
    with tempfile.TemporaryDirectory() as tmpdir:
        infile = Path(tmpdir) / "test.mmd"
        infile.write_text(FLOWCHART)

        result = run_cli([str(infile)])
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "<svg" in result.stdout
        assert 'data-node-id="A"' in result.stdout


def test_positional_nonexistent_file():
    """Positional arg with nonexistent file exits 2."""
    result = run_cli(["/nonexistent/path.mmd"])
    assert result.returncode == 2
    assert "error" in result.stderr.lower()


# ---- PNG output ----

def test_png_output_file():
    """merm input.mmd -o output.png writes valid PNG file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        infile = Path(tmpdir) / "test.mmd"
        outfile = Path(tmpdir) / "test.png"
        infile.write_text(FLOWCHART)

        result = run_cli([str(infile), "-o", str(outfile)])
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert outfile.exists()

        png_data = outfile.read_bytes()
        assert png_data[:4] == b"\x89PNG", (
            "Output file should start with PNG magic bytes"
        )


def test_png_format_flag_to_stdout():
    """merm input.mmd -f png writes PNG bytes to stdout."""
    with tempfile.TemporaryDirectory() as tmpdir:
        infile = Path(tmpdir) / "test.mmd"
        infile.write_text(FLOWCHART)

        result = run_cli_binary([str(infile), "-f", "png"])
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert result.stdout[:4] == b"\x89PNG", "Stdout should contain PNG data"


def test_png_format_flag_to_file():
    """merm input.mmd -f png -o output.png writes PNG file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        infile = Path(tmpdir) / "test.mmd"
        outfile = Path(tmpdir) / "test.png"
        infile.write_text(FLOWCHART)

        result = run_cli([str(infile), "-f", "png", "-o", str(outfile)])
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert outfile.exists()

        png_data = outfile.read_bytes()
        assert png_data[:4] == b"\x89PNG"


# ---- Format auto-detection ----

def test_format_autodetect_png_extension():
    """-o foo.png without -f produces PNG."""
    with tempfile.TemporaryDirectory() as tmpdir:
        infile = Path(tmpdir) / "test.mmd"
        outfile = Path(tmpdir) / "foo.png"
        infile.write_text(FLOWCHART)

        result = run_cli([str(infile), "-o", str(outfile)])
        assert result.returncode == 0, f"stderr: {result.stderr}"
        png_data = outfile.read_bytes()
        assert png_data[:4] == b"\x89PNG"


def test_format_autodetect_svg_extension():
    """-o foo.svg without -f produces SVG."""
    with tempfile.TemporaryDirectory() as tmpdir:
        infile = Path(tmpdir) / "test.mmd"
        outfile = Path(tmpdir) / "foo.svg"
        infile.write_text(FLOWCHART)

        result = run_cli([str(infile), "-o", str(outfile)])
        assert result.returncode == 0, f"stderr: {result.stderr}"
        svg = outfile.read_text()
        assert "<svg" in svg


def test_format_autodetect_txt_defaults_svg():
    """-o foo.txt without -f defaults to SVG."""
    with tempfile.TemporaryDirectory() as tmpdir:
        infile = Path(tmpdir) / "test.mmd"
        outfile = Path(tmpdir) / "foo.txt"
        infile.write_text(FLOWCHART)

        result = run_cli([str(infile), "-o", str(outfile)])
        assert result.returncode == 0, f"stderr: {result.stderr}"
        content = outfile.read_text()
        assert "<svg" in content


def test_format_explicit_overrides_extension():
    """-f png -o foo.svg uses explicit format (PNG), not extension."""
    with tempfile.TemporaryDirectory() as tmpdir:
        infile = Path(tmpdir) / "test.mmd"
        outfile = Path(tmpdir) / "foo.svg"
        infile.write_text(FLOWCHART)

        result = run_cli([str(infile), "-f", "png", "-o", str(outfile)])
        assert result.returncode == 0, f"stderr: {result.stderr}"
        png_data = outfile.read_bytes()
        assert png_data[:4] == b"\x89PNG"


# ---- Backward compatibility ----

def test_file_input_file_output():
    """CLI reads .mmd file with -i, renders SVG to output file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        infile = Path(tmpdir) / "test.mmd"
        outfile = Path(tmpdir) / "test.svg"
        infile.write_text(FLOWCHART)

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
        infile.write_text(FLOWCHART)

        result = run_cli(["-i", str(infile)])
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "<svg" in result.stdout
        assert 'data-node-id="A"' in result.stdout
        assert 'data-node-id="B"' in result.stdout


def test_both_positional_and_flag_input_error():
    """Both positional and -i provided -> error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        infile = Path(tmpdir) / "test.mmd"
        infile.write_text(FLOWCHART)

        result = run_cli([str(infile), "-i", str(infile)])
        assert result.returncode == 2
        assert "cannot specify both" in result.stderr.lower()


# ---- Stdin to stdout ----

def test_stdin_to_stdout():
    """Piping mermaid text on stdin produces SVG on stdout."""
    result = run_cli(input_text=FLOWCHART)
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


# ---- Stdin piping with PNG ----

def test_stdin_to_png_file():
    """Pipe flowchart text via stdin with -o output.png, get PNG file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        outfile = Path(tmpdir) / "out.png"
        result = run_cli(
            ["-o", str(outfile)],
            input_text=FLOWCHART,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert outfile.exists()
        png_data = outfile.read_bytes()
        assert png_data[:4] == b"\x89PNG"


# ---- Error handling ----

def test_file_not_found():
    """Missing input file exits with code 2 and prints error to stderr."""
    result = run_cli(["-i", "/nonexistent/path.mmd"])
    assert result.returncode == 2
    assert "error" in result.stderr.lower()


def test_parse_error():
    """Invalid mermaid syntax exits with code 1 and prints parse error to stderr."""
    result = run_cli(input_text="this is not mermaid")
    assert result.returncode == 1
    assert "error" in result.stderr.lower()


def test_output_dir_not_found():
    """Writing to a nonexistent directory exits with code 2 and prints error."""
    result = run_cli(
        ["-o", "/nonexistent/dir/out.svg"],
        input_text=FLOWCHART,
    )
    assert result.returncode == 2
    assert "error" in result.stderr.lower()


def test_invalid_format():
    """Invalid format value (-f pdf) exits with error."""
    result = run_cli(["-f", "pdf"], input_text=FLOWCHART)
    assert result.returncode == 2  # argparse exits with 2 for invalid choices
    assert "invalid choice" in result.stderr.lower()


def test_missing_cairosvg_for_png():
    """When cairosvg is not available and PNG is requested, exit with helpful error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        infile = Path(tmpdir) / "test.mmd"
        infile.write_text(FLOWCHART)

        # Create a script that blocks cairosvg import
        script = Path(tmpdir) / "test_no_cairo.py"
        script.write_text(
            "import sys\n"
            "import builtins\n"
            "original_import = builtins.__import__\n"
            "def mock_import(name, *args, **kwargs):\n"
            "    if name == 'cairosvg':\n"
            "        raise ImportError('No module named cairosvg')\n"
            "    return original_import(name, *args, **kwargs)\n"
            "builtins.__import__ = mock_import\n"
            f"sys.argv = ['merm', '{infile}', '-f', 'png']\n"
            "from merm.cli import main\n"
            "main()\n"
        )
        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 1
        assert "cairosvg" in result.stderr.lower()


# ---- Refactored internals: all diagram types work ----

def test_flowchart_via_cli():
    """Flowchart renders through CLI."""
    result = run_cli(input_text=FLOWCHART)
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "<svg" in result.stdout


def test_sequence_via_cli():
    """Sequence diagram renders through CLI."""
    result = run_cli(input_text=SEQUENCE)
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "<svg" in result.stdout


def test_class_via_cli():
    """Class diagram renders through CLI."""
    result = run_cli(input_text=CLASS)
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "<svg" in result.stdout


def test_state_via_cli():
    """State diagram renders through CLI."""
    result = run_cli(input_text=STATE)
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "<svg" in result.stdout


# ---- Integration: pipe chain ----

def test_pipe_chain():
    """echo 'graph LR; A-->B' | merm produces valid SVG."""
    result = subprocess.run(
        CLI,
        input=FLOWCHART,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "<svg" in result.stdout
    assert 'data-node-id="A"' in result.stdout


# ---- Integration: entry point script works ----

def test_entry_point_script():
    """The installed 'merm' script entry point works."""
    result = subprocess.run(
        ["uv", "run", "merm", "--version"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0
    from merm.__version__ import __version__
    assert __version__ in result.stdout


def test_entry_point_help_shows_format():
    """uv run merm --help shows format option."""
    result = subprocess.run(
        ["uv", "run", "merm", "--help"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0
    assert "--format" in result.stdout
    assert "png" in result.stdout
