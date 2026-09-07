"""Layout configuration.

Defines LayoutConfig and the callable types used to configure the layout
engine.
"""

from dataclasses import dataclass
from typing import Callable

from merm.ir import Direction

# Public callable types for text measurement and wrapping.
MeasureFn = Callable[[str, float], tuple[float, float]]
LineWidthFn = Callable[[str, float], float]
WrapLineFn = Callable[[str, float, float], list[str]]


@dataclass
class LayoutConfig:
    """Per-layout spacing and text sizing configuration."""

    rank_sep: float = 40.0
    node_sep: float = 30.0
    direction: Direction = Direction.TB
    font_size: float = 16.0
    max_text_width: float = 200.0
    line_width_fn: LineWidthFn | None = None
    wrap_line_fn: WrapLineFn | None = None
    node_padding_h: float = 32.0
    node_padding_v: float = 16.0
    node_min_width: float = 70.0
    node_min_height: float = 42.0
