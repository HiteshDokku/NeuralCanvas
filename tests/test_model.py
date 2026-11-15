"""Tests for VGG model architecture, layer mapping, and feature extraction."""

import torch
import torch.nn as nn
from torchvision.models import vgg19

from neural_canvas.model import (
    LAYER_INDEX_TO_CONV_INDEX,
    LAYER_NAME_TO_INDEX,
    build_extractor,
    resolve_layer_indices,
)


def test_layer_index_mapping_against_vgg_architecture() -> None:
    """Verify that every mapped layer index corresponds to a ReLU preceded by a Conv2d."""
    raw_vgg = vgg19(weights=None)
    features = raw_vgg.features

    for layer_name, relu_idx in LAYER_NAME_TO_INDEX.items():
        assert relu_idx < len(features), f"Layer index {relu_idx} out of range for {layer_name}"

        # Target layer must be ReLU
        target_layer = features[relu_idx]
        assert isinstance(target_layer, nn.ReLU), (
            f"Expected features[{relu_idx}] to be ReLU for {layer_name}, got {type(target_layer)}"
        )

        # Preceding layer must be Conv2d
        conv_idx = LAYER_INDEX_TO_CONV_INDEX[relu_idx]
        assert conv_idx == relu_idx - 1
        conv_layer = features[conv_idx]
        assert isinstance(conv_layer, nn.Conv2d), (
            f"Expected features[{conv_idx}] to be Conv2d for {layer_name}, got {type(conv_layer)}"
        )


def test_specific_gatys_layer_indices() -> None:
    """Verify exact Gatys / TF tutorial layer indices:

    Style: conv1_1 (1), conv2_1 (6), conv3_1 (11), conv4_1 (20), conv5_1 (29)
    Content: conv5_2 (31)
    """
    mapping = resolve_layer_indices(
        ["conv1_1", "conv2_1", "conv3_1", "conv4_1", "conv5_1", "conv5_2"]
    )
    assert mapping["conv1_1"] == 1
    assert mapping["conv2_1"] == 6
    assert mapping["conv3_1"] == 11
    assert mapping["conv4_1"] == 20
    assert mapping["conv5_1"] == 29
    assert mapping["conv5_2"] == 31


def test_extractor_offline_forward_random_weights() -> None:
    """Verify feature extractor forward pass with random weights (no download required)."""
    extractor = build_extractor(weights=False)
    dummy_input = torch.rand(1, 3, 64, 64)

    requested = {"conv1_1": 1, "conv3_1": 11, "conv5_2": 31}
    outputs = extractor(dummy_input, requested)

    assert "conv1_1" in outputs
    assert "conv3_1" in outputs
    assert "conv5_2" in outputs

    assert outputs["conv1_1"].shape == (1, 64, 64, 64)
    assert outputs["conv3_1"].shape == (1, 256, 16, 16)
    assert outputs["conv5_2"].shape == (1, 512, 4, 4)
