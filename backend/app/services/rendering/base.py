"""Render backend contract shared by all rendering strategies."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable

import numpy as np


class RenderUnavailable(RuntimeError):
    """Raised when a selected render mode cannot load (missing package/weights/GPU)."""


class RenderBackend(ABC):
    """A pluggable rendering strategy.

    Implementations composite the given material selections onto the source
    image and return the final BGR canvas.

    `selections` items: {category, render_path, color?, texture_path?,
                         material_key, name}
    `mask_loader(category) -> np.ndarray|None` returns the stored binary mask.
    """

    #: registry key, e.g. "classical"
    name: str = "base"

    @abstractmethod
    def is_available(self) -> bool:
        """Cheap check (imports/config) - does not download weights."""

    @abstractmethod
    def render(
        self,
        canvas_bgr: np.ndarray,
        selections: list[dict],
        mask_loader: Callable[[str], "np.ndarray | None"],
    ) -> np.ndarray:
        ...
