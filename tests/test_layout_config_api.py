"""Tests for per-layout text sizing configuration."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

import merm.layout.sugiyama as sugiyama
from merm.ir import Diagram, DiagramType, Node, Subgraph
from merm.layout import LayoutConfig, layout_diagram


def _diagram(label: str) -> Diagram:
    return Diagram(
        type=DiagramType.flowchart,
        nodes=(Node(id="node", label=label),),
    )


def test_config_controls_font_measurement_and_padding():
    measure_calls: list[tuple[str, float]] = []
    width_calls: list[tuple[str, float]] = []

    def measure(text: str, font_size: float) -> tuple[float, float]:
        measure_calls.append((text, font_size))
        return (10.0, 5.0)

    def line_width(text: str, font_size: float) -> float:
        width_calls.append((text, font_size))
        return 10.0

    result = layout_diagram(
        _diagram("configured"),
        measure_fn=measure,
        config=LayoutConfig(
            font_size=13.0,
            line_width_fn=line_width,
            node_padding_h=8.0,
            node_padding_v=6.0,
            node_min_width=0.0,
            node_min_height=0.0,
        ),
    )

    node = result.nodes["node"]
    assert measure_calls == [("configured", 13.0)]
    assert width_calls == [("configured", 13.0)]
    assert node.width == pytest.approx(18.0)
    assert node.height == pytest.approx(11.0)


def test_config_controls_wrapping_and_minimum_size():
    wrap_calls: list[tuple[str, float, float]] = []

    def line_width(text: str, font_size: float) -> float:
        return 100.0 if text == "wrap this label" else 12.0

    def wrap_line(text: str, font_size: float, max_width: float) -> list[str]:
        wrap_calls.append((text, font_size, max_width))
        return ["wrap this", "label"]

    result = layout_diagram(
        _diagram("wrap this label"),
        measure_fn=lambda text, font_size: (1.0, 1.0),
        config=LayoutConfig(
            font_size=17.0,
            max_text_width=40.0,
            line_width_fn=line_width,
            wrap_line_fn=wrap_line,
            node_padding_h=0.0,
            node_padding_v=0.0,
            node_min_width=90.0,
            node_min_height=50.0,
        ),
    )

    assert wrap_calls == [("wrap this label", 17.0, 40.0)]
    assert result.nodes["node"].width == pytest.approx(90.0)
    assert result.nodes["node"].height == pytest.approx(50.0)


def test_configured_measurement_sizes_subgraph_titles():
    calls: list[tuple[str, float]] = []

    def line_width(text: str, font_size: float) -> float:
        calls.append((text, font_size))
        return 500.0 if text == "wide title" else 1.0

    diagram = Diagram(
        type=DiagramType.flowchart,
        nodes=(Node(id="node", label="node"),),
        subgraphs=(
            Subgraph(
                id="group",
                title="wide title",
                node_ids=("node",),
            ),
        ),
    )
    result = layout_diagram(
        diagram,
        measure_fn=lambda text, font_size: (1.0, 1.0),
        config=LayoutConfig(line_width_fn=line_width),
    )

    assert ("wide title", 12.0) in calls
    assert result.subgraphs["group"].width == pytest.approx(524.0)


def test_concurrent_layouts_keep_text_configuration_isolated():
    label = "a label that must wrap"
    barrier = Barrier(2)
    global_names = (
        "_DEFAULT_FONT_SIZE",
        "_NODE_PADDING_H",
        "_NODE_PADDING_V",
        "_NODE_MIN_WIDTH",
        "_NODE_MIN_HEIGHT",
        "_line_width",
        "_wrap_line",
    )
    original_globals = {
        name: getattr(sugiyama, name)
        for name in global_names
    }

    def assert_globals_unchanged() -> None:
        assert {
            name: getattr(sugiyama, name)
            for name in global_names
        } == original_globals

    def run_layout(
        *,
        font_size: float,
        wrapped_width: float,
        padding_h: float,
    ) -> tuple[float, float]:
        def line_width(text: str, current_font_size: float) -> float:
            assert_globals_unchanged()
            assert current_font_size == font_size
            if text == label:
                barrier.wait(timeout=5.0)
                return 100.0
            return wrapped_width

        def wrap_line(
            text: str,
            current_font_size: float,
            max_width: float,
        ) -> list[str]:
            assert_globals_unchanged()
            assert (text, current_font_size, max_width) == (
                label,
                font_size,
                50.0,
            )
            return ["a label", "that wraps"]

        result = layout_diagram(
            _diagram(label),
            measure_fn=lambda text, size: (1.0, 1.0),
            config=LayoutConfig(
                font_size=font_size,
                max_text_width=50.0,
                line_width_fn=line_width,
                wrap_line_fn=wrap_line,
                node_padding_h=padding_h,
                node_padding_v=0.0,
                node_min_width=0.0,
                node_min_height=0.0,
            ),
        )
        node = result.nodes["node"]
        return node.width, node.height

    with ThreadPoolExecutor(max_workers=2) as executor:
        small = executor.submit(
            run_layout,
            font_size=10.0,
            wrapped_width=8.0,
            padding_h=2.0,
        )
        large = executor.submit(
            run_layout,
            font_size=20.0,
            wrapped_width=30.0,
            padding_h=4.0,
        )

    assert small.result() == pytest.approx((10.0, 28.0))
    assert large.result() == pytest.approx((34.0, 56.0))
    assert_globals_unchanged()
