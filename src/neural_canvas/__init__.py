"""Neural Canvas: A portfolio-quality neural style transfer project in PyTorch."""

from __future__ import annotations

from .config import PRESET_BALANCED, PRESET_DRAFT, PRESET_HIGH, PRESETS, StyleTransferConfig
from .device import get_device_info, resolve_device
from .engine import StepResult, StyleTransferEngine
from .image_io import (
    calculate_dimensions,
    is_grayscale_image,
    load_image,
    save_png,
    tensor_to_pil,
    transfer_color,
)
from .losses import content_loss, gram_matrix, style_loss, total_variation_loss
from .model import build_extractor, get_extractor
from .styles import StylePreset, StyleRegistry, get_preset, list_presets, resolve_style

__version__ = "0.1.0"

__all__ = [
    "PRESETS",
    "PRESET_BALANCED",
    "PRESET_DRAFT",
    "PRESET_HIGH",
    "StepResult",
    "StylePreset",
    "StyleRegistry",
    "StyleTransferConfig",
    "StyleTransferEngine",
    "build_extractor",
    "calculate_dimensions",
    "content_loss",
    "get_device_info",
    "get_extractor",
    "get_preset",
    "gram_matrix",
    "is_grayscale_image",
    "list_presets",
    "load_image",
    "resolve_device",
    "resolve_style",
    "save_png",
    "style_loss",
    "tensor_to_pil",
    "total_variation_loss",
    "transfer_color",
]
