"""Tests for sequence diagram text rendering and box sizing (Task 54).

Verifies that <br/> tags are rendered as multi-line text, note boxes are
properly sized, and the SVG viewBox encompasses all content.
"""

import xml.etree.ElementTree as ET
from pathlib import Path

from pymermaid import render_diagram

_FIXTURES = Path(__file__).parent / "fixtures" / "corpus" / "sequence"
_SVG_NS = "http://www.w3.org/2000/svg"
_NS = {"svg": _SVG_NS}

# Font size used by the sequence renderer for notes/messages.
_NOTE_FONT_SIZE = 12
_CHAR_WIDTH_FACTOR = 0.6

def _render_fixture(name: str) -> ET.Element:
    """Render a .mmd fixture and return the parsed SVG root element."""
    path = _FIXTURES / name
    source = path.read_text()
    svg_str = render_diagram(source)
    return ET.fromstring(svg_str)

def _all_text_content(el: ET.Element) -> str:
    """Collect all text content from an element and its children."""
    parts = []
    if el.text:
        parts.append(el.text)
    for child in el:
        if child.text:
            parts.append(child.text)
        if child.tail:
            parts.append(child.tail)
    if el.tail:
        parts.append(el.tail)
    return "".join(parts)

def _find_groups(root: ET.Element, class_name: str) -> list[ET.Element]:
    """Find all <g> elements with the given class attribute."""
    groups = []
    for g in root.iter("{%s}g" % _SVG_NS):
        if g.get("class") == class_name:
            groups.append(g)
    return groups

def _parse_viewbox(root: ET.Element) -> tuple[float, float, float, float]:
    """Parse the viewBox attribute into (x, y, width, height)."""
    vb = root.get("viewBox", "0 0 0 0")
    parts = vb.split()
    return float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3])

# ---------------------------------------------------------------------------
# Unit: br tag conversion in notes
# ---------------------------------------------------------------------------

class TestBrTagConversionInNotes:
    """Verify that <br/> in note text is rendered as tspan elements."""

    def test_no_literal_br_in_flink_late_event_notes(self):
        """Notes in flink_late_event.mmd must not contain literal '<br/>' text."""
        root = _render_fixture("flink_late_event.mmd")
        note_groups = _find_groups(root, "seq-note")
        assert len(note_groups) > 0, "Expected note groups in flink_late_event.mmd"

        for g in note_groups:
            for text_el in g.iter("{%s}text" % _SVG_NS):
                full_text = _all_text_content(text_el)
                assert "<br/>" not in full_text, (
                    f"Found literal '<br/>' in note text: {full_text}"
                )

    def test_multiline_notes_have_tspan_children(self):
        """Notes with <br/> should contain multiple <tspan> children."""
        root = _render_fixture("flink_late_event.mmd")
        note_groups = _find_groups(root, "seq-note")

        # The first note on F has 3 lines (2 <br/> tags).
        found_multiline = False
        for g in note_groups:
            for text_el in g.iter("{%s}text" % _SVG_NS):
                tspans = list(text_el.iter("{%s}tspan" % _SVG_NS))
                if len(tspans) >= 2:
                    found_multiline = True
                    break
            if found_multiline:
                break

        assert found_multiline, (
            "Expected at least one note with multiple <tspan> children"
        )

    def test_flink_late_upsert_note_two_tspan_lines(self):
        """The 'upsert via PRIMARY KEY<br/>corrected from 1 to 2' note should
        render as two <tspan> lines."""
        root = _render_fixture("flink_late_upsert.mmd")
        note_groups = _find_groups(root, "seq-note")

        found = False
        for g in note_groups:
            for text_el in g.iter("{%s}text" % _SVG_NS):
                full_text = _all_text_content(text_el)
                if "upsert" in full_text and "corrected" in full_text:
                    tspans = list(text_el.iter("{%s}tspan" % _SVG_NS))
                    assert len(tspans) == 2, (
                        f"Expected 2 tspan lines, got {len(tspans)}"
                    )
                    found = True

        assert found, "Did not find the upsert note"

    def test_no_literal_br_in_flink_late_upsert_notes(self):
        """Notes in flink_late_upsert.mmd must not contain literal '<br/>'."""
        root = _render_fixture("flink_late_upsert.mmd")
        note_groups = _find_groups(root, "seq-note")
        assert len(note_groups) > 0

        for g in note_groups:
            for text_el in g.iter("{%s}text" % _SVG_NS):
                full_text = _all_text_content(text_el)
                assert "<br/>" not in full_text, (
                    f"Found literal '<br/>' in note text: {full_text}"
                )

# ---------------------------------------------------------------------------
# Unit: br tag conversion in message labels
# ---------------------------------------------------------------------------

class TestBrTagConversionInMessages:
    """Verify that <br/> in message labels is rendered as tspan elements."""

    def test_message_with_br_has_tspan(self):
        """A message label containing <br/> should use <tspan> children."""
        source = (
            "sequenceDiagram\n"
            "    participant A\n"
            "    participant B\n"
            "    A->>B: first line<br/>second line\n"
        )
        svg_str = render_diagram(source)
        root = ET.fromstring(svg_str)

        msg_groups = _find_groups(root, "seq-message")
        assert len(msg_groups) > 0

        found_tspan = False
        for g in msg_groups:
            for text_el in g.iter("{%s}text" % _SVG_NS):
                full_text = _all_text_content(text_el)
                assert "<br/>" not in full_text, (
                    f"Found literal '<br/>' in message label: {full_text}"
                )
                tspans = list(text_el.iter("{%s}tspan" % _SVG_NS))
                if len(tspans) >= 2:
                    found_tspan = True

        assert found_tspan, (
            "Expected message label with <br/> to have multiple <tspan> children"
        )

# ---------------------------------------------------------------------------
# Unit: note box sizing
# ---------------------------------------------------------------------------

class TestNoteBoxSizing:
    """Verify note boxes are wide enough for their text content."""

    def _check_note_widths(self, root: ET.Element):
        """For each note group, assert rect width >= estimated text width."""
        note_groups = _find_groups(root, "seq-note")
        assert len(note_groups) > 0

        for g in note_groups:
            rect = g.find("{%s}rect" % _SVG_NS)
            text_el = g.find("{%s}text" % _SVG_NS)
            assert rect is not None and text_el is not None

            rect_width = float(rect.get("width", "0"))

            # Get the longest line of text.
            tspans = list(text_el.iter("{%s}tspan" % _SVG_NS))
            if tspans:
                lines = [ts.text or "" for ts in tspans]
            else:
                lines = [text_el.text or ""]

            longest = max(len(line) for line in lines) if lines else 0
            estimated_width = longest * _NOTE_FONT_SIZE * _CHAR_WIDTH_FACTOR

            assert rect_width >= estimated_width, (
                f"Note rect width {rect_width} < estimated text width "
                f"{estimated_width} for text lines {lines}"
            )

    def test_flink_late_event_note_widths(self):
        root = _render_fixture("flink_late_event.mmd")
        self._check_note_widths(root)

    def test_flink_late_upsert_note_widths(self):
        root = _render_fixture("flink_late_upsert.mmd")
        self._check_note_widths(root)

# ---------------------------------------------------------------------------
# Unit: note box height for multi-line notes
# ---------------------------------------------------------------------------

class TestNoteBoxHeight:
    """Verify note boxes are tall enough for multi-line content."""

    def test_multiline_note_height(self):
        """Notes with <br/> should have height accommodating all lines."""
        root = _render_fixture("flink_late_event.mmd")
        note_groups = _find_groups(root, "seq-note")

        line_height = 16  # Typical line height for 12px font.
        padding = 10  # Minimum padding.

        for g in note_groups:
            rect = g.find("{%s}rect" % _SVG_NS)
            text_el = g.find("{%s}text" % _SVG_NS)
            assert rect is not None and text_el is not None

            tspans = list(text_el.iter("{%s}tspan" % _SVG_NS))
            num_lines = max(len(tspans), 1)

            if num_lines > 1:
                rect_height = float(rect.get("height", "0"))
                min_expected = num_lines * line_height + padding
                assert rect_height >= min_expected, (
                    f"Note rect height {rect_height} < expected minimum "
                    f"{min_expected} for {num_lines} lines"
                )

# ---------------------------------------------------------------------------
# Unit: viewBox encompasses all elements
# ---------------------------------------------------------------------------

class TestViewBoxEncompassesAll:
    """Verify the SVG viewBox is large enough for all rendered content."""

    def _check_viewbox(self, root: ET.Element):
        vb_x, vb_y, vb_w, vb_h = _parse_viewbox(root)
        vb_right = vb_x + vb_w

        # Check all rect elements.
        for rect in root.iter("{%s}rect" % _SVG_NS):
            x = float(rect.get("x", "0"))
            w = float(rect.get("width", "0"))
            assert x >= vb_x, (
                f"Rect at x={x} extends past viewBox left edge {vb_x}"
            )
            assert x + w <= vb_right, (
                f"Rect right edge {x + w} extends past viewBox right edge {vb_right}"
            )

        # Check all text elements x coordinate (approximate for centered text).
        for text_el in root.iter("{%s}text" % _SVG_NS):
            x_str = text_el.get("x")
            if x_str:
                x = float(x_str)
                # For center-anchored text, the x is the center.
                # Just check x itself is within viewBox with some tolerance.
                assert x >= vb_x, (
                    f"Text at x={x} is outside viewBox left edge {vb_x}"
                )

    def test_flink_late_event_viewbox(self):
        root = _render_fixture("flink_late_event.mmd")
        self._check_viewbox(root)

    def test_flink_late_upsert_viewbox(self):
        root = _render_fixture("flink_late_upsert.mmd")
        self._check_viewbox(root)

# ---------------------------------------------------------------------------
# Unit: notes.mmd still works (regression)
# ---------------------------------------------------------------------------

class TestNotesRegression:
    """Verify notes.mmd without <br/> still renders correctly."""

    def test_notes_renders_without_errors(self):
        root = _render_fixture("notes.mmd")
        assert root is not None

    def test_notes_contain_expected_text(self):
        root = _render_fixture("notes.mmd")
        note_groups = _find_groups(root, "seq-note")
        all_note_text = []
        for g in note_groups:
            for text_el in g.iter("{%s}text" % _SVG_NS):
                all_note_text.append(_all_text_content(text_el))

        combined = " ".join(all_note_text)
        assert "Alice starts" in combined
        assert "Shared note" in combined
        assert "Bob replies" in combined

    def test_notes_without_br_have_no_tspan(self):
        """Notes without <br/> should not have <tspan> children."""
        root = _render_fixture("notes.mmd")
        note_groups = _find_groups(root, "seq-note")
        for g in note_groups:
            for text_el in g.iter("{%s}text" % _SVG_NS):
                tspans = list(text_el.iter("{%s}tspan" % _SVG_NS))
                assert len(tspans) == 0, (
                    f"Single-line note should not have <tspan> elements, "
                    f"found {len(tspans)}"
                )

# ---------------------------------------------------------------------------
# Unit: message labels within viewBox
# ---------------------------------------------------------------------------

class TestMessageLabelsWithinViewBox:
    """Verify message labels don't extend past the viewBox."""

    def test_flink_late_event_message_labels_in_viewbox(self):
        root = _render_fixture("flink_late_event.mmd")
        vb_x, vb_y, vb_w, vb_h = _parse_viewbox(root)

        msg_groups = _find_groups(root, "seq-message")
        for g in msg_groups:
            for text_el in g.iter("{%s}text" % _SVG_NS):
                x_str = text_el.get("x")
                if x_str:
                    x = float(x_str)
                    assert x >= vb_x, (
                        f"Message label at x={x} is outside viewBox "
                        f"left edge {vb_x}"
                    )
