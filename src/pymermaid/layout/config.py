"""Layout configuration.

Defines LayoutConfig and the MeasureFn type alias used to configure
the layout engine.
"""

from dataclasses import dataclass
from typing import Callable

from pymermaid.ir import Direction


@dataclass
class LayoutConfig:
    """Configuration for the layout engine."""

    rank_sep: float = 40.0
    node_sep: float = 30.0
    direction: Direction = Direction.TB

# Type alias for the measure function
MeasureFn = Callable[[str, float], tuple[float, float]]
