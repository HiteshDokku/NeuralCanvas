"""VGG19 Feature Extractor for Neural Canvas."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence

import torch
import torch.nn as nn
from torchvision.models import VGG19_Weights, vgg19

logger = logging.getLogger(__name__)

# Map common layer names to torchvision VGG19 features module indices.
# In Keras/TF, conv layers include ReLU activations (post-ReLU).
# In torchvision VGG19, ReLU is a separate module immediately following each Conv2d:
# conv1_1 (idx 0) -> relu1_1 (idx 1)
# conv1_2 (idx 2) -> relu1_2 (idx 3)
# maxpool1 (idx 4)
# conv2_1 (idx 5) -> relu2_1 (idx 6)
# conv2_2 (idx 7) -> relu2_2 (idx 8)
# maxpool2 (idx 9)
# conv3_1 (idx 10) -> relu3_1 (idx 11)
# conv3_2 (idx 12) -> relu3_2 (idx 13)
# conv3_3 (idx 14) -> relu3_3 (idx 15)
# conv3_4 (idx 16) -> relu3_4 (idx 17)
# maxpool3 (idx 18)
# conv4_1 (idx 19) -> relu4_1 (idx 20)
# conv4_2 (idx 21) -> relu4_2 (idx 22)
# conv4_3 (idx 23) -> relu4_3 (idx 24)
# conv4_4 (idx 25) -> relu4_4 (idx 26)
# maxpool4 (idx 27)
# conv5_1 (idx 28) -> relu5_1 (idx 29)
# conv5_2 (idx 30) -> relu5_2 (idx 31)
# conv5_3 (idx 32) -> relu5_3 (idx 33)
# conv5_4 (idx 34) -> relu5_4 (idx 35)
# maxpool5 (idx 36)

LAYER_NAME_TO_INDEX: dict[str, int] = {
    # Short conv / relu names (referring to post-ReLU activations)
    "conv1_1": 1,
    "relu1_1": 1,
    "conv1_2": 3,
    "relu1_2": 3,
    "conv2_1": 6,
    "relu2_1": 6,
    "conv2_2": 8,
    "relu2_2": 8,
    "conv3_1": 11,
    "relu3_1": 11,
    "conv3_2": 13,
    "relu3_2": 13,
    "conv3_3": 15,
    "relu3_3": 15,
    "conv3_4": 17,
    "relu3_4": 17,
    "conv4_1": 20,
    "relu4_1": 20,
    "conv4_2": 22,
    "relu4_2": 22,
    "conv4_3": 24,
    "relu4_3": 24,
    "conv4_4": 26,
    "relu4_4": 26,
    "conv5_1": 29,
    "relu5_1": 29,
    "conv5_2": 31,
    "relu5_2": 31,
    "conv5_3": 33,
    "relu5_3": 33,
    "conv5_4": 35,
    "relu5_4": 35,
    # Keras style names
    "block1_conv1": 1,
    "block1_conv2": 3,
    "block2_conv1": 6,
    "block2_conv2": 8,
    "block3_conv1": 11,
    "block3_conv2": 13,
    "block3_conv3": 15,
    "block3_conv4": 17,
    "block4_conv1": 20,
    "block4_conv2": 22,
    "block4_conv3": 24,
    "block4_conv4": 26,
    "block5_conv1": 29,
    "block5_conv2": 31,
    "block5_conv3": 33,
    "block5_conv4": 35,
}

# Preceding Conv2d layer index for each post-ReLU output
LAYER_INDEX_TO_CONV_INDEX: dict[int, int] = {
    1: 0,
    3: 2,
    6: 5,
    8: 7,
    11: 10,
    13: 12,
    15: 14,
    17: 16,
    20: 19,
    22: 21,
    24: 23,
    26: 25,
    29: 28,
    31: 30,
    33: 32,
    35: 34,
}


def canonicalize_layer_name(name: str) -> str:
    """Normalize user layer name and return canonical representation."""
    cleaned = name.strip().lower()
    if cleaned not in LAYER_NAME_TO_INDEX:
        supported = sorted(set(LAYER_NAME_TO_INDEX.keys()))
        raise KeyError(f"Unknown VGG layer '{name}'. Supported layers: {supported}")
    return cleaned


def resolve_layer_indices(layer_names: Sequence[str]) -> dict[str, int]:
    """Map a sequence of layer names to their torchvision features module index."""
    return {name: LAYER_NAME_TO_INDEX[canonicalize_layer_name(name)] for name in layer_names}


class ImageNetNormalize(nn.Module):
    """Normalize RGB tensor in [0, 1] using ImageNet mean and std."""

    def __init__(self) -> None:
        super().__init__()
        mean = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1)
        std = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)
        self.register_buffer("mean", mean)
        self.register_buffer("std", std)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return (x - self.mean) / self.std


class VGGFeatureExtractor(nn.Module):
    """VGG19 feature extractor truncated to maximum requested layer index.

    Guarantees:
    - In-place ReLUs replaced with out-of-place ReLUs to avoid corrupting captured activations.
    - Parameters are frozen (eval mode, requires_grad = False).
    - ImageNet normalization included as first step.
    """

    def __init__(
        self,
        features: nn.Sequential,
        max_layer_idx: int = 35,
    ) -> None:
        super().__init__()
        self.normalize = ImageNetNormalize()

        # Slice features up to max_layer_idx inclusive
        layers = []
        for i in range(max_layer_idx + 1):
            layer = features[i]
            if isinstance(layer, nn.ReLU):
                # Ensure non-in-place
                layers.append(nn.ReLU(inplace=False))
            else:
                layers.append(layer)

        self.features = nn.Sequential(*layers)
        self.features.eval()
        for param in self.features.parameters():
            param.requires_grad = False

    def forward(
        self,
        x: torch.Tensor,
        requested_layers: Mapping[str, int],
    ) -> dict[str, torch.Tensor]:
        """Forward pass extracting requested feature maps.

        Args:
            x: Input image tensor of shape (B, 3, H, W) with values in [0, 1].
            requested_layers: Mapping of layer name to features index.

        Returns:
            Dictionary mapping layer name to activation tensor.
        """
        # Group requested names by target index
        idx_to_names: dict[int, list[str]] = {}
        for name, idx in requested_layers.items():
            idx_to_names.setdefault(idx, []).append(name)

        max_idx = max(requested_layers.values()) if requested_layers else -1

        out = self.normalize(x)
        captured: dict[str, torch.Tensor] = {}

        for i, layer in enumerate(self.features):
            out = layer(out)
            if i in idx_to_names:
                for name in idx_to_names[i]:
                    captured[name] = out
            if i >= max_idx:
                break

        return captured


_EXTRACTOR_CACHE: dict[tuple[str, bool], VGGFeatureExtractor] = {}


def build_extractor(
    weights: bool = True,
    device: torch.device | None = None,
) -> VGGFeatureExtractor:
    """Construct a VGGFeatureExtractor.

    Args:
        weights: If True, load ImageNet pretrained weights. If False, initialize random weights.
        device: PyTorch device to move model to.

    Returns:
        VGGFeatureExtractor instance.
    """
    vgg_weights = VGG19_Weights.IMAGENET1K_V1 if weights else None
    model = vgg19(weights=vgg_weights)
    extractor = VGGFeatureExtractor(model.features, max_layer_idx=35)
    if device is not None:
        extractor = extractor.to(device)
    extractor.eval()
    return extractor


def get_extractor(
    device: torch.device,
    weights: bool = True,
) -> VGGFeatureExtractor:
    """Retrieve or build a cached VGGFeatureExtractor for the given device."""
    key = (str(device), weights)
    if key not in _EXTRACTOR_CACHE:
        logger.info("Initializing VGG19 feature extractor on %s (weights=%s)", device, weights)
        extractor = build_extractor(weights=weights, device=device)
        _EXTRACTOR_CACHE[key] = extractor
    return _EXTRACTOR_CACHE[key]


def clear_extractor_cache() -> None:
    """Clear cached extractors to free memory."""
    _EXTRACTOR_CACHE.clear()
