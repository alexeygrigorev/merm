"""Command-line interface for merm."""

import argparse
import sys
from importlib.metadata import version

from merm import render_diagram
from merm.parser import ParseError


def _get_version() -> str:
    """Return the version string for display."""
    try:
        return f"merm {version('merm')}"
    except Exception:
        from merm.__version__ import __version__
        return f"merm {__version__}"


def _build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser."""
    parser = argparse.ArgumentParser(
        prog="merm",
        description="Render Mermaid diagrams to SVG or PNG from the command line.",
    )
    parser.add_argument(
        "input_file",
        nargs="?",
        default=None,
        help="Input .mmd file path (reads from stdin if not provided)",
    )
    parser.add_argument(
        "-i",
        "--input",
        default=None,
        help="Input .mmd file path (alternative to positional argument)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output file path (writes to stdout if not provided)",
    )
    parser.add_argument(
        "-f",
        "--format",
        default=None,
        choices=["svg", "png"],
        help="Output format: svg or png "
        "(auto-detected from -o extension, defaults to svg)",
    )
    parser.add_argument(
        "--theme",
        default=None,
        choices=["default", "dark", "forest", "neutral"],
        help="Built-in theme name (default, dark, forest, neutral)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=_get_version(),
    )
    return parser


def _resolve_input(args: argparse.Namespace) -> str | None:
    """Resolve the input file path from positional or -i arguments.

    Returns the file path, or None if stdin should be used.
    Exits with an error if both positional and -i are provided.
    """
    if args.input_file is not None and args.input is not None:
        print(
            "Error: cannot specify both positional input and -i/--input",
            file=sys.stderr,
        )
        sys.exit(2)
    return args.input_file if args.input_file is not None else args.input


def _resolve_format(args: argparse.Namespace) -> str:
    """Resolve the output format from -f or output file extension.

    Returns 'svg' or 'png'.
    """
    if args.format is not None:
        return args.format
    if args.output is not None and args.output.lower().endswith(".png"):
        return "png"
    return "svg"


def _convert_to_png(svg_str: str) -> bytes:
    """Convert SVG string to PNG bytes using cairosvg."""
    try:
        import cairosvg
    except ImportError:
        print(
            "Error: PNG output requires cairosvg. Install it with: uv add cairosvg",
            file=sys.stderr,
        )
        sys.exit(1)
    return cairosvg.svg2png(bytestring=svg_str.encode("utf-8"))


def main() -> None:
    """Entry point for the merm CLI."""
    parser = _build_parser()
    args = parser.parse_args()

    # --- Resolve input source ---
    input_path = _resolve_input(args)

    if input_path is not None:
        try:
            with open(input_path) as f:
                source = f.read()
        except FileNotFoundError:
            print(f"Error: file not found: {input_path}", file=sys.stderr)
            sys.exit(2)
        except PermissionError:
            print(
                f"Error: permission denied: {input_path}", file=sys.stderr
            )
            sys.exit(2)
        except OSError as exc:
            print(f"Error: cannot read file: {exc}", file=sys.stderr)
            sys.exit(2)
    else:
        source = sys.stdin.read()

    # --- Render SVG ---
    try:
        svg_output = render_diagram(source, theme=args.theme)
    except ParseError as exc:
        print(f"Parse error: {exc}", file=sys.stderr)
        sys.exit(1)

    # --- Resolve output format ---
    output_format = _resolve_format(args)

    # --- Convert to PNG if needed ---
    if output_format == "png":
        png_data = _convert_to_png(svg_output)

    # --- Write output ---
    if args.output is not None:
        try:
            if output_format == "png":
                with open(args.output, "wb") as f:
                    f.write(png_data)
            else:
                with open(args.output, "w") as f:
                    f.write(svg_output)
        except FileNotFoundError:
            print(
                f"Error: output directory does not exist: {args.output}",
                file=sys.stderr,
            )
            sys.exit(2)
        except PermissionError:
            print(
                f"Error: permission denied writing: {args.output}",
                file=sys.stderr,
            )
            sys.exit(2)
        except OSError as exc:
            print(f"Error: cannot write file: {exc}", file=sys.stderr)
            sys.exit(2)
    else:
        if output_format == "png":
            sys.stdout.buffer.write(png_data)
        else:
            print(svg_output)

if __name__ == "__main__":
    main()
