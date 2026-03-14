"""Fuzz tests for Mermaid parsers using hypothesis.

These tests verify that parsers handle arbitrary input gracefully:
they must either return a valid diagram object or raise ParseError.
Any other exception type (IndexError, KeyError, TypeError, etc.)
is a failure.
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from merm.parser.flowchart import ParseError, parse_flowchart
from merm.parser.sequence import parse_sequence
from merm.parser.statediag import parse_state_diagram

# ---------------------------------------------------------------------------
# Property-based fuzz tests
# ---------------------------------------------------------------------------


@pytest.mark.fuzz
@settings(max_examples=500)
@given(text=st.text())
def test_flowchart_parser_never_crashes(text: str) -> None:
    """parse_flowchart must return a Diagram or raise ParseError."""
    try:
        parse_flowchart(text)
    except ParseError:
        pass


@pytest.mark.fuzz
@settings(max_examples=500)
@given(text=st.text())
def test_sequence_parser_never_crashes(text: str) -> None:
    """parse_sequence must return a SequenceDiagram or raise ParseError."""
    try:
        parse_sequence(text)
    except ParseError:
        pass


@pytest.mark.fuzz
@settings(max_examples=500)
@given(text=st.text())
def test_state_parser_never_crashes(text: str) -> None:
    """parse_state_diagram must return a StateDiagram or raise ParseError."""
    try:
        parse_state_diagram(text)
    except ParseError:
        pass


# ---------------------------------------------------------------------------
# Targeted edge-case tests: Flowchart
# ---------------------------------------------------------------------------


@pytest.mark.fuzz
def test_flowchart_empty_string() -> None:
    with pytest.raises(ParseError):
        parse_flowchart("")


@pytest.mark.fuzz
def test_flowchart_whitespace_only() -> None:
    with pytest.raises(ParseError):
        parse_flowchart("   \n\t  ")


@pytest.mark.fuzz
def test_flowchart_null_bytes() -> None:
    """Null bytes in input must not crash the parser."""
    try:
        parse_flowchart("graph TD\n  A\x00B")
    except ParseError:
        pass


@pytest.mark.fuzz
def test_flowchart_very_long_input() -> None:
    """Very long input must not hang or OOM."""
    long_input = "graph TD\n" + "  A --> B\n" * 5000
    try:
        parse_flowchart(long_input)
    except ParseError:
        pass


@pytest.mark.fuzz
def test_flowchart_unicode_stress() -> None:
    """Unicode edge cases must not crash the parser."""
    inputs = [
        "graph TD\n  \u0410 --> \u0411",  # Cyrillic
        "graph TD\n  \u4f60\u597d --> \u4e16\u754c",  # Chinese
        "graph TD\n  \U0001f600 --> \U0001f601",  # Emoji
        "graph TD\n  A\u200b --> B\u200b",  # Zero-width space
        "graph TD\n  \u202eA --> B",  # RTL override
    ]
    for text in inputs:
        try:
            parse_flowchart(text)
        except ParseError:
            pass


@pytest.mark.fuzz
def test_flowchart_dangling_edge() -> None:
    """Dangling edge syntax must raise ParseError, not crash."""
    try:
        parse_flowchart("graph TD\n  A --> ")
    except ParseError:
        pass


# ---------------------------------------------------------------------------
# Targeted edge-case tests: Sequence
# ---------------------------------------------------------------------------


@pytest.mark.fuzz
def test_sequence_empty_string() -> None:
    with pytest.raises(ParseError):
        parse_sequence("")


@pytest.mark.fuzz
def test_sequence_whitespace_only() -> None:
    with pytest.raises(ParseError):
        parse_sequence("   \n\t  ")


@pytest.mark.fuzz
def test_sequence_null_bytes() -> None:
    try:
        parse_sequence(
            "sequenceDiagram\n  Alice\x00->>Bob: Hi"
        )
    except ParseError:
        pass


@pytest.mark.fuzz
def test_sequence_very_long_input() -> None:
    long_input = (
        "sequenceDiagram\n" + "  Alice->>Bob: msg\n" * 5000
    )
    try:
        parse_sequence(long_input)
    except ParseError:
        pass


@pytest.mark.fuzz
def test_sequence_unicode_stress() -> None:
    inputs = [
        "sequenceDiagram\n"
        "  \u0410\u043b\u0438\u0441\u0430"
        "->>\u0411\u043e\u0431: \u041f\u0440\u0438\u0432\u0435\u0442",
        "sequenceDiagram\n  A\u200b->>B\u200b: msg",
        "sequenceDiagram\n  \U0001f600->>\U0001f601: emoji",
    ]
    for text in inputs:
        try:
            parse_sequence(text)
        except ParseError:
            pass


# ---------------------------------------------------------------------------
# Targeted edge-case tests: State diagram
# ---------------------------------------------------------------------------


@pytest.mark.fuzz
def test_state_empty_string() -> None:
    with pytest.raises(ParseError):
        parse_state_diagram("")


@pytest.mark.fuzz
def test_state_whitespace_only() -> None:
    with pytest.raises(ParseError):
        parse_state_diagram("   \n\t  ")


@pytest.mark.fuzz
def test_state_null_bytes() -> None:
    try:
        parse_state_diagram(
            "stateDiagram-v2\n  A\x00 --> B"
        )
    except ParseError:
        pass


@pytest.mark.fuzz
def test_state_very_long_input() -> None:
    long_input = (
        "stateDiagram-v2\n"
        + "  StateA --> StateB\n" * 5000
    )
    try:
        parse_state_diagram(long_input)
    except ParseError:
        pass


@pytest.mark.fuzz
def test_state_unicode_stress() -> None:
    inputs = [
        "stateDiagram-v2\n  \u0410 --> \u0411",
        "stateDiagram-v2\n  A\u200b --> B\u200b",
        "stateDiagram-v2\n  \U0001f600 --> \U0001f601",
    ]
    for text in inputs:
        try:
            parse_state_diagram(text)
        except ParseError:
            pass
