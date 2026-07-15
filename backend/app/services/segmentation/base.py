"""Segmentation backend contract shared by all model strategies."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
from PIL import Image


@dataclass
class CategoryMask:
    mask: np.ndarray  # uint8 {0,1}, shape (H, W)
    confidence: float
    instance_count: int


class BackendUnavailable(RuntimeError):
    """Raised when a selected backend cannot load (missing package/weights/GPU)."""


class SegBackend(ABC):
    """A pluggable segmentation strategy.

    Implementations turn an image + list of category keys into a mapping of
    category -> CategoryMask at the working-image resolution.
    """

    #: registry key, e.g. "grounded_sam"
    name: str = "base"

    @abstractmethod
    def is_available(self) -> bool:
        """Cheap check (imports/config) - does not download weights."""

    def warmup(self) -> None:
        """Load weights into memory. Override in model-backed engines."""

    def unload(self) -> None:
        """Release weights to free RAM. Override in model-backed engines."""

    def is_loaded(self) -> bool:
        """True when weights are resident in memory (OpenCV always True)."""
        return True

    @abstractmethod
    def segment(self, image: Image.Image, categories: list[str]) -> dict[str, CategoryMask]:
        ...
