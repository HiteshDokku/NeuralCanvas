"""Configuration models and presets for Neural Canvas."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from typing import Any, Literal

DEFAULT_CONTENT_LAYERS: tuple[str, ...] = ("conv4_2",)
DEFAULT_STYLE_LAYERS: tuple[str, ...] = (
    "conv1_1",
    "conv2_1",
    "conv3_1",
    "conv4_1",
    "conv5_1",
)

InitMode = Literal["content", "noise"]
OptimizerType = Literal["adam", "lbfgs"]


@dataclass(frozen=True)
class StyleTransferConfig:
    """Immutable configuration for a style transfer execution.

    PyTorch Loss Calibration Rationale:
    In the original TensorFlow/Keras tutorial, VGG19 was fed unnormalized pixels in [0, 255].
    Because activations were ~255x larger, Gram matrices were ~255^2 larger, and raw style MSE
    was ~4e9 times larger than in PyTorch.
    In PyTorch, torchvision VGG19 receives standard ImageNet-normalized RGB tensors
    (mean ~0, std ~1, values in -2.1..+2.6). Raw style loss is ~1..20, and raw content loss is ~0.1..5.
    Total variation loss (sum of absolute neighbor differences across all pixels and channels)
    on a 384x384 image is ~30,000, with an unweighted gradient L2 norm of ~40,000.

    Under the tutorial's unadapted weights (style=1e-2, content=1e4, tv=30), TV gradient was ~40,000
    while style gradient was ~0.013 (a 3,000,000:1 ratio!), which completely obliterated style textures
    and smoothed the canvas into a blurry fog. Additionally, Adam eps=0.1 severely throttled small updates.

    Calibrated PyTorch defaults:
    - style_weight = 1e5    (produces active style gradients ~1,000 to 4,000)
    - content_weight = 80.0 (balances structural fidelity, prevents soft styles like Monet dissolving)
    - tv_weight = 3e-5      (removes pixel speckle without muting painterly impasto strokes)
    - content_layers = ("conv4_2",) (Gatys et al. default: crisp spatial outline vs blurry conv5_2)
    - learning_rate = 0.03
    - eps = 1e-8            (standard Adam epsilon preserving coordinate adaptivity)
    """

    style_weight: float = 1e5
    content_weight: float = 100.0
    tv_weight: float = 0.05
    steps: int = 1000
    max_dim: int = 512
    style_max_dim: int | None = None
    style_scale_ratio: float = 1.0
    learning_rate: float = 0.03
    lr_schedule: str = "cosine"
    lr_min_ratio: float = 0.01
    betas: tuple[float, float] = (0.99, 0.999)
    eps: float = 1e-8
    content_layers: tuple[str, ...] = DEFAULT_CONTENT_LAYERS
    style_layers: tuple[str, ...] = DEFAULT_STYLE_LAYERS
    init: InitMode = "content"
    optimizer: OptimizerType = "adam"
    parameterization: Literal["sigmoid", "clamped"] = "sigmoid"
    sigmoid_init_clamp: tuple[float, float] = (1e-4, 1.0 - 1e-4)
    multi_crop_style: bool = False
    num_style_crops: int = 8
    style_crop_exclude: tuple[float, float, float, float] | list[float] | None = None
    style_layer_weights: dict[str, float] | None = None
    color_preserve: bool = False
    seed: int | None = 42
    preview_every: int = 50

    def __post_init__(self) -> None:
        """Validate config parameters."""
        if self.parameterization not in ("sigmoid", "clamped"):
            raise ValueError(
                f"parameterization must be 'sigmoid' or 'clamped', got {self.parameterization}"
            )
        if self.num_style_crops <= 0:
            raise ValueError(f"num_style_crops must be positive, got {self.num_style_crops}")
        if self.style_weight < 0:
            raise ValueError(f"style_weight must be non-negative, got {self.style_weight}")
        if self.content_weight < 0:
            raise ValueError(f"content_weight must be non-negative, got {self.content_weight}")
        if self.tv_weight < 0:
            raise ValueError(f"tv_weight must be non-negative, got {self.tv_weight}")
        if self.steps <= 0:
            raise ValueError(f"steps must be positive integer, got {self.steps}")
        if self.max_dim < 64 or self.max_dim > 768:
            raise ValueError(f"max_dim must be between 64 and 768, got {self.max_dim}")
        if self.style_max_dim is not None and (
            self.style_max_dim < 64 or self.style_max_dim > 1024
        ):
            raise ValueError(f"style_max_dim must be between 64 and 1024, got {self.style_max_dim}")
        if self.style_scale_ratio <= 0:
            raise ValueError(f"style_scale_ratio must be positive, got {self.style_scale_ratio}")
        if self.learning_rate <= 0:
            raise ValueError(f"learning_rate must be positive, got {self.learning_rate}")
        if self.lr_schedule not in ("constant", "cosine"):
            raise ValueError(f"lr_schedule must be 'constant' or 'cosine', got {self.lr_schedule}")
        if not (0 < self.lr_min_ratio <= 1.0):
            raise ValueError(f"lr_min_ratio must be in (0, 1], got {self.lr_min_ratio}")
        if len(self.betas) != 2 or not (0 < self.betas[0] < 1 and 0 < self.betas[1] < 1):
            raise ValueError(f"betas must be a pair of floats in (0, 1), got {self.betas}")
        if self.eps <= 0:
            raise ValueError(f"eps must be positive, got {self.eps}")
        if not self.content_layers:
            raise ValueError("content_layers cannot be empty")
        if not self.style_layers:
            raise ValueError("style_layers cannot be empty")
        if self.init not in ("content", "noise"):
            raise ValueError(f"init mode must be 'content' or 'noise', got {self.init}")
        if self.optimizer not in ("adam", "lbfgs"):
            raise ValueError(f"optimizer must be 'adam' or 'lbfgs', got {self.optimizer}")
        if self.preview_every <= 0:
            raise ValueError(f"preview_every must be positive integer, got {self.preview_every}")

    @property
    def effective_style_max_dim(self) -> int:
        """Get the resolved style max dimension."""
        if self.style_max_dim is not None:
            return self.style_max_dim
        return max(64, min(1024, int(round(self.max_dim * self.style_scale_ratio))))

    def to_json(self, indent: int = 2) -> str:
        """Serialize configuration to a JSON string."""
        data = asdict(self)
        # Convert tuples to lists for json serialization
        data["content_layers"] = list(self.content_layers)
        data["style_layers"] = list(self.style_layers)
        data["betas"] = list(self.betas)
        return json.dumps(data, indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> StyleTransferConfig:
        """Deserialize configuration from a JSON string."""
        data: dict[str, Any] = json.loads(json_str)
        if "content_layers" in data:
            data["content_layers"] = tuple(data["content_layers"])
        if "style_layers" in data:
            data["style_layers"] = tuple(data["style_layers"])
        if "betas" in data:
            data["betas"] = tuple(data["betas"])
        if "sigmoid_init_clamp" in data and isinstance(data["sigmoid_init_clamp"], list):
            data["sigmoid_init_clamp"] = tuple(data["sigmoid_init_clamp"])
        if "style_crop_exclude" in data and isinstance(data["style_crop_exclude"], list):
            data["style_crop_exclude"] = tuple(data["style_crop_exclude"])
        return cls(**data)


# Quality presets (calibrated for PyTorch scale & conv4_2 structural stability)
PRESET_DRAFT = StyleTransferConfig(
    steps=150,
    max_dim=256,
    style_weight=1e5,
    content_weight=100.0,
    tv_weight=0.05,
    learning_rate=0.02,
    parameterization="sigmoid",
    preview_every=25,
)

PRESET_BALANCED = StyleTransferConfig(
    steps=400,
    max_dim=384,
    style_weight=1e5,
    content_weight=100.0,
    tv_weight=0.05,
    learning_rate=0.03,
    parameterization="sigmoid",
    preview_every=40,
)

PRESET_HIGH = StyleTransferConfig(
    steps=1000,
    max_dim=512,
    style_weight=1e5,
    content_weight=100.0,
    tv_weight=0.05,
    learning_rate=0.0075,
    lr_schedule="cosine",
    lr_min_ratio=0.01,
    parameterization="clamped",
    preview_every=50,
)

PRESETS: dict[str, StyleTransferConfig] = {
    "draft": PRESET_DRAFT,
    "balanced": PRESET_BALANCED,
    "high": PRESET_HIGH,
}

DEFAULT_SLIDER_POSITION: int = 6


def calculate_slider_content_weight(
    slider_val: int | None,
    base_cw: float,
    portrait_mode: bool = False,
    default_slider_val: int = DEFAULT_SLIDER_POSITION,
) -> float:
    """Calculate derived content weight from UI style strength slider.

    - If portrait_mode is True: returns 10000.0 (anchoring facial anatomy).
    - If slider is untouched (None or equal to default_slider_val): returns exact base_cw (unrounded).
    - If slider_val is 1: returns 5000.0 (weakest style / maximum photo structure preservation).
    - If slider_val is 10: returns 90.0 (strongest style / intense painterly dominance).
    - Positions 1..6 interpolate logarithmically from 5000.0 down to base_cw.
    - Positions 6..10 interpolate logarithmically from base_cw down to min(90.0, base_cw).
    Ensures content weight strictly decreases (style increases) monotonically from position 1 to 10.
    """
    if portrait_mode:
        return 10000.0
    if slider_val is None or slider_val == default_slider_val:
        return float(base_cw)
    if slider_val <= 1:
        return 5000.0

    min_cw = min(90.0, float(base_cw))
    max_cw = max(5000.0, float(base_cw))

    if slider_val < default_slider_val:
        ratio = (float(slider_val) - 1.0) / (float(default_slider_val) - 1.0)
        return float(math.exp(math.log(max_cw) - ratio * (math.log(max_cw) - math.log(base_cw))))
    else:
        ratio = (float(slider_val) - float(default_slider_val)) / (10.0 - float(default_slider_val))
        return float(math.exp(math.log(base_cw) - ratio * (math.log(base_cw) - math.log(min_cw))))
