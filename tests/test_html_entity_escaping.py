"""Tests for HTML entity decoding in flowchart parser labels."""

import xml.etree.ElementTree as ET

import pytest

from pymermaid.parser import parse_flowchart


class TestHTMLEntityDecodingInNodeLabels:
    """Verify that standard HTML entities are decoded in node labels."""

    def test_ampersand_entity(self):
        d = parse_flowchart('graph TD\n  A["Ampersand &amp; stuff"]')
        assert d.nodes[0].label == "Ampersand & stuff"

    def test_lt_gt_entities(self):
        d = parse_flowchart('graph TD\n  A["Angle &lt; &gt; brackets"]')
        assert d.nodes[0].label == "Angle < > brackets"

    def test_quot_entity(self):
        d = parse_flowchart('graph TD\n  A["Quote &quot;here&quot;"]')
        assert d.nodes[0].label == 'Quote "here"'

    def test_quot_entity_only(self):
        d = parse_flowchart('graph TD\n  A["&quot;quoted&quot;"]')
        assert d.nodes[0].label == '"quoted"'

    def test_numeric_decimal_entity(self):
        d = parse_flowchart('graph TD\n  A["&#38; numeric"]')
        assert d.nodes[0].label == "& numeric"

    def test_numeric_hex_entity(self):
        d = parse_flowchart('graph TD\n  A["&#x26; hex"]')
        assert d.nodes[0].label == "& hex"

    def test_mermaid_entity_still_works(self):
        d = parse_flowchart('graph TD\n  A["Hash #35; mark"]')
        assert d.nodes[0].label == "Hash # mark"

    def test_mixed_mermaid_and_html_entities(self):
        d = parse_flowchart('graph TD\n  A["#35; and &amp; together"]')
        assert d.nodes[0].label == "# and & together"

    def test_multiple_html_entities(self):
        d = parse_flowchart('graph TD\n  A["&lt;b&gt;bold&lt;/b&gt;"]')
        assert d.nodes[0].label == "<b>bold</b>"


class TestHTMLEntityDecodingInEdgeLabels:
    """Verify that HTML entities are decoded in edge labels.

    Note: HTML entities with semicolons (like &amp;) in edge labels
    conflict with the semicolon statement separator in the preprocessor,
    so edge labels with entities that contain semicolons are not directly
    testable via parsing. We verify via the _decode_entities function
    and with edge labels that don't contain semicolons.
    """

    def test_decode_entities_on_edge_label_text(self):
        """Test entity decoding on edge label text via direct function call."""
        from pymermaid.parser.flowchart import _decode_entities

        assert _decode_entities("&amp; link") == "& link"
        assert _decode_entities("&lt;tag&gt;") == "<tag>"
        assert _decode_entities("#35; hash") == "# hash"

    def test_pipe_label_plain_text(self):
        """Edge labels without entities still work."""
        d = parse_flowchart('graph TD\n  A -->|plain label| B')
        assert d.edges[0].label == "plain label"

    def test_inline_label_plain_text(self):
        """Inline edge labels without entities still work."""
        d = parse_flowchart('graph TD\n  A -- plain label --> B')
        assert d.edges[0].label == "plain label"


class TestSVGOutputCorrectness:
    """Verify that decoded entities are properly XML-escaped in SVG output."""

    def test_ampersand_in_svg_output(self):
        """An & in a label should appear as &amp; in SVG source (single escape)."""
        from pymermaid.layout import layout_diagram
        from pymermaid.measure import measure_text
        from pymermaid.render import render_svg

        d = parse_flowchart('graph TD\n  A["Ampersand & stuff"]')
        measurer = measure_text
        laid = layout_diagram(d, measurer)
        svg_str = render_svg(d, laid)

        # The raw SVG should contain &amp; (single XML escape) not &amp;amp;
        assert "&amp;amp;" not in svg_str
        assert "Ampersand &amp; stuff" in svg_str

        # When parsed as XML, the text content should be the decoded value
        root = ET.fromstring(svg_str)
        ns = {"svg": "http://www.w3.org/2000/svg"}
        texts = root.findall(".//svg:text", ns)
        text_contents = []
        for t in texts:
            # Collect all text including tspan children
            full = "".join(t.itertext())
            text_contents.append(full)
        assert any("Ampersand & stuff" in tc for tc in text_contents)

    def test_angle_brackets_in_svg_output(self):
        """< and > in a label should appear as &lt; and &gt; in SVG source."""
        from pymermaid.layout import layout_diagram
        from pymermaid.measure import measure_text
        from pymermaid.render import render_svg

        d = parse_flowchart('graph TD\n  A["Angle < > brackets"]')
        measurer = measure_text
        laid = layout_diagram(d, measurer)
        svg_str = render_svg(d, laid)

        # Should NOT contain double-escaped entities
        assert "&amp;lt;" not in svg_str
        assert "&amp;gt;" not in svg_str
        # Should contain proper XML escapes
        assert "&lt;" in svg_str
        assert "&gt;" in svg_str


class TestPNGRendering:
    """Integration test: render special_chars.mmd to SVG and PNG."""

    def test_special_chars_renders_without_error(self):
        from pymermaid.layout import layout_diagram
        from pymermaid.measure import measure_text
        from pymermaid.render import render_svg

        mmd_path = "tests/fixtures/corpus/text/special_chars.mmd"
        with open(mmd_path) as f:
            source = f.read()

        d = parse_flowchart(source)
        # Verify decoded labels
        labels = {n.label for n in d.nodes}
        assert "Ampersand & stuff" in labels
        assert "Angle < > brackets" in labels

        laid = layout_diagram(d, measure_text)
        svg_str = render_svg(d, laid)

        # SVG should be valid XML
        ET.fromstring(svg_str)

        # No double-escaped entities
        assert "&amp;amp;" not in svg_str
        assert "&amp;lt;" not in svg_str
        assert "&amp;gt;" not in svg_str

    def test_special_chars_png_rendering(self):
        """Render to PNG via cairosvg -- confirms SVG is valid for rasterization."""
        cairosvg = pytest.importorskip("cairosvg")
        from pymermaid.layout import layout_diagram
        from pymermaid.measure import measure_text
        from pymermaid.render import render_svg

        mmd_path = "tests/fixtures/corpus/text/special_chars.mmd"
        with open(mmd_path) as f:
            source = f.read()

        d = parse_flowchart(source)
        laid = layout_diagram(d, measure_text)
        svg_str = render_svg(d, laid)

        # Convert to PNG -- should not raise
        png_data = cairosvg.svg2png(bytestring=svg_str.encode("utf-8"))
        assert len(png_data) > 0
