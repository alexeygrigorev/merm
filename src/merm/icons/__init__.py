"""Font Awesome icon registry for inline SVG icon rendering.

Icons are stored as individual SVG files in this package directory.
They are lazy-loaded and cached on first access.

Font Awesome Free is MIT licensed (https://fontawesome.com/license/free).
Icon paths extracted from @fortawesome/fontawesome-free SVG files.
"""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

_ICONS_DIR = Path(__file__).parent

# Lazy-loaded cache: icon name -> (path_d, viewbox_width, viewbox_height)
_icon_cache: dict[str, tuple[str, int, int]] = {}
_all_loaded = False

# Aliases: old FA name -> new FA6 name
_ALIASES: dict[str, str] = {
    "check-circle": "circle-check",
    "cog": "gear",
    "exclamation-triangle": "triangle-exclamation",
    "home": "house",
    "info-circle": "circle-info",
    "mobile-alt": "mobile",
    "question": "circle-question",
    "search": "magnifying-glass",
    "shopping-cart": "cart-shopping",
    "times": "xmark",
    "times-circle": "circle-xmark",
}


_FA_TOKEN_RE = re.compile(r"fa:fa-([\w-]+)")


def _load_icon(name: str) -> tuple[str, int, int] | None:
    """Load a single icon SVG file and parse its path data and viewBox."""
    svg_path = _ICONS_DIR / f"{name}.svg"
    if not svg_path.exists():
        return None
    tree = ET.parse(svg_path)
    root = tree.getroot()
    ns = "{http://www.w3.org/2000/svg}"
    viewbox = root.get("viewBox", "0 0 512 512")
    parts = viewbox.split()
    w = int(float(parts[2]))
    h = int(float(parts[3]))
    path_el = root.find(f"{ns}path")
    if path_el is None:
        path_el = root.find("path")
    if path_el is None:
        return None
    path_d = path_el.get("d", "")
    return (path_d, w, h)


def _load_all() -> None:
    """Load all icon SVG files into the cache."""
    global _all_loaded
    if _all_loaded:
        return
    for svg_file in _ICONS_DIR.glob("*.svg"):
        name = svg_file.stem
        if name not in _icon_cache:
            result = _load_icon(name)
            if result is not None:
                _icon_cache[name] = result
    _all_loaded = True


@dataclass
class LabelSegment:
    """A segment of a parsed label -- either text or an icon reference."""

    kind: str  # "text" or "icon"
    value: str  # text content or icon name (without fa:fa- prefix)


def get_icon_path(name: str) -> tuple[str, int, int] | None:
    """Look up an icon by name.

    Args:
        name: The icon name without the ``fa-`` prefix (e.g. ``"car"``).

    Returns:
        A tuple of ``(path_d, viewbox_width, viewbox_height)`` or ``None``
        if the icon is not found.
    """
    # Check cache first
    result = _icon_cache.get(name)
    if result is not None:
        return result

    # Resolve aliases
    canonical = _ALIASES.get(name, name)

    # Check cache for canonical name
    result = _icon_cache.get(canonical)
    if result is not None:
        _icon_cache[name] = result
        return result

    # Load from disk
    result = _load_icon(canonical)
    if result is not None:
        _icon_cache[canonical] = result
        if name != canonical:
            _icon_cache[name] = result
        return result

    return None


def parse_label(label: str) -> list[LabelSegment]:
    """Parse a label string into segments of text and icon references.

    Tokens matching ``fa:fa-<name>`` are extracted as icon segments.
    Surrounding text becomes text segments. Leading/trailing whitespace
    in text segments is preserved, but empty text segments are dropped.

    Args:
        label: The raw label string, e.g. ``"fa:fa-car Car"``.

    Returns:
        A list of :class:`LabelSegment` instances.
    """
    segments: list[LabelSegment] = []
    last_end = 0

    for m in _FA_TOKEN_RE.finditer(label):
        # Text before this icon token
        before = label[last_end : m.start()]
        if before:
            segments.append(LabelSegment(kind="text", value=before))
        segments.append(LabelSegment(kind="icon", value=m.group(1)))
        last_end = m.end()

    # Trailing text after last icon
    after = label[last_end:]
    if after:
        segments.append(LabelSegment(kind="text", value=after))

    # If no icons found, return single text segment
    if not segments:
        segments.append(LabelSegment(kind="text", value=label))

    return segments


def has_icons(label: str) -> bool:
    """Return True if the label contains any ``fa:fa-*`` tokens."""
    return bool(_FA_TOKEN_RE.search(label))


def icon_count() -> int:
    """Return the number of icons in the registry."""
    return len(list(_ICONS_DIR.glob("*.svg")))
