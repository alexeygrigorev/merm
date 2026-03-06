"""Tests for task 57: icon SVG extraction to separate files."""

from merm.icons import (
    _ICONS_DIR,
    _icon_cache,
    _load_icon,
    get_icon_path,
    icon_count,
)


class TestIconSVGFiles:
    """Verify that icons are stored as individual SVG files."""

    def test_icons_directory_exists(self):
        assert _ICONS_DIR.is_dir()

    def test_svg_files_exist(self):
        svg_files = list(_ICONS_DIR.glob("*.svg"))
        assert len(svg_files) >= 60

    def test_each_svg_file_has_valid_content(self):
        """Each SVG file should have a <path> element with a d attribute."""
        import xml.etree.ElementTree as ET

        for svg_file in _ICONS_DIR.glob("*.svg"):
            tree = ET.parse(svg_file)
            root = tree.getroot()
            ns = "{http://www.w3.org/2000/svg}"
            path_el = root.find(f"{ns}path")
            if path_el is None:
                path_el = root.find("path")
            assert path_el is not None, f"{svg_file.name} has no <path> element"
            d = path_el.get("d", "")
            assert len(d) > 10, f"{svg_file.name} has trivial path data"

    def test_each_svg_file_has_viewbox(self):
        import xml.etree.ElementTree as ET

        for svg_file in _ICONS_DIR.glob("*.svg"):
            tree = ET.parse(svg_file)
            root = tree.getroot()
            viewbox = root.get("viewBox")
            assert viewbox is not None, f"{svg_file.name} missing viewBox"
            parts = viewbox.split()
            assert len(parts) == 4, f"{svg_file.name} invalid viewBox: {viewbox}"

class TestLazyLoading:
    """Verify icons are lazy-loaded from disk."""

    def test_load_icon_reads_from_disk(self):
        result = _load_icon("car")
        assert result is not None
        path_d, w, h = result
        assert isinstance(path_d, str)
        assert len(path_d) > 10
        assert w > 0
        assert h > 0

    def test_load_icon_nonexistent_returns_none(self):
        result = _load_icon("this-icon-does-not-exist-xyz")
        assert result is None

    def test_get_icon_path_caches_result(self):
        # Clear cache for this icon if present
        _icon_cache.pop("star", None)
        # First call loads from disk
        result1 = get_icon_path("star")
        assert result1 is not None
        # Should now be in cache
        assert "star" in _icon_cache
        # Second call should return same object from cache
        result2 = get_icon_path("star")
        assert result1 is result2

    def test_alias_resolves_and_caches(self):
        _icon_cache.pop("cog", None)
        _icon_cache.pop("gear", None)
        result = get_icon_path("cog")
        assert result is not None
        # Both alias and canonical should be cached
        assert "cog" in _icon_cache
        assert "gear" in _icon_cache

class TestNoHardcodedPaths:
    """Verify that __init__.py does not contain hardcoded SVG path data."""

    def test_init_file_is_small(self):
        init_file = _ICONS_DIR / "__init__.py"
        content = init_file.read_text()
        # The old file was 353 lines. The new one should be much smaller
        # since all SVG data is in separate files.
        line_count = len(content.splitlines())
        assert line_count < 200, (
            f"__init__.py has {line_count} lines, expected < 200 "
            f"(SVG data should be in separate files)"
        )

    def test_no_svg_path_data_in_init(self):
        """The __init__.py should not contain long SVG path strings."""
        init_file = _ICONS_DIR / "__init__.py"
        content = init_file.read_text()
        # SVG path data lines are typically very long (>100 chars of path commands)
        # Check that no line looks like an SVG path data string
        for line in content.splitlines():
            # SVG paths contain sequences like "M123 456c..." or "L123 456"
            if line.strip().startswith('"M') and len(line) > 200:
                raise AssertionError(
                    "Found what looks like hardcoded SVG path data "
                    f"in __init__.py: {line[:80]}..."
                )

class TestIconDataIntegrity:
    """Verify the extracted data matches expectations."""

    def test_known_icon_data_matches(self):
        """Spot-check a few icons to verify path data was extracted correctly."""
        result = get_icon_path("car")
        assert result is not None
        path_d, w, h = result
        assert w == 512
        assert h == 512
        # Path should start with the expected prefix
        assert path_d.startswith("M135.2")

    def test_icon_count_unchanged(self):
        """Should have exactly 61 icons (same as original registry)."""
        assert icon_count() == 61

    def test_all_svg_files_loadable(self):
        """Every SVG file should be loadable through _load_icon."""
        for svg_file in _ICONS_DIR.glob("*.svg"):
            name = svg_file.stem
            result = _load_icon(name)
            assert result is not None, f"Failed to load {name}.svg"
