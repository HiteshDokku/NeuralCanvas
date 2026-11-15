"""Loss functions for Neural Canvas: Gram matrix, style loss, content loss, total variation."""

from __future__ import annotations

import torch


def gram_matrix(features: torch.Tensor) -> torch.Tensor:
    """Compute the Gram matrix of intermediate feature activations.

    Ported faithfully from the official Gatys / TensorFlow tutorial:
    G_{cd} = sum_{i,j} (F_{ijc} * F_{ijd}) / (H * W)
    representing correlations between feature channels divided by spatial locations.

    Args:
        features: Tensor of shape (B, C, H, W).

    Returns:
        Gram matrix of shape (B, C, C).
    """
    if features.ndim != 4:
        raise ValueError(f"Expected 4D feature tensor (B, C, H, W), got shape {features.shape}")

    b, c, h, w = features.shape
    num_locations = float(h * w)
    # Using einsum matching 'bijc,bijd->bcd' with NCHW layout: 'bchw,bdhw->bcd'
    gram = torch.einsum("bchw,bdhw->bcd", features, features)
    return gram / num_locations


def style_loss(
    current_grams: dict[str, torch.Tensor],
    target_grams: dict[str, torch.Tensor],
    style_weight: float = 1.0,
    layer_weights: dict[str, float] | None = None,
) -> torch.Tensor:
    """Calculate style loss as normalized sum of MSE across style layer Gram matrices.

    Args:
        current_grams: Map of layer name to Gram matrix of current image.
        target_grams: Map of layer name to Gram matrix of style image.
        style_weight: Scalar multiplier for the style loss.
        layer_weights: Optional map of layer names to relative importance weights.
            If provided, weights are normalized to sum to 1.0.

    Returns:
        Scalar tensor containing style loss.
    """
    if not target_grams:
        raise ValueError("target_grams dictionary cannot be empty")

    num_layers = len(target_grams)
    if layer_weights is not None:
        total_w = sum(layer_weights.get(name, 0.0) for name in target_grams)
        if total_w <= 0:
            raise ValueError("Sum of layer_weights for present layers must be positive")
        norm_weights = {name: layer_weights.get(name, 0.0) / total_w for name in target_grams}
    else:
        norm_weights = dict.fromkeys(target_grams, 1.0 / num_layers)

    layer_losses = []
    for name, target in target_grams.items():
        if name not in current_grams:
            raise KeyError(f"Style layer '{name}' missing from current features")
        current = current_grams[name]
        layer_losses.append(norm_weights[name] * torch.mean((current - target) ** 2))

    total_loss = torch.stack(layer_losses).sum()
    return total_loss * style_weight


def content_loss(
    current_features: dict[str, torch.Tensor],
    target_features: dict[str, torch.Tensor],
    content_weight: float = 1.0,
) -> torch.Tensor:
    """Calculate content loss as normalized sum of MSE across content layers.

    Args:
        current_features: Map of layer name to feature activations of current image.
        target_features: Map of layer name to feature activations of content image.
        content_weight: Scalar multiplier for content loss.

    Returns:
        Scalar tensor containing content loss.
    """
    if not target_features:
        raise ValueError("target_features dictionary cannot be empty")

    num_layers = len(target_features)
    layer_losses = []
    for name, target in target_features.items():
        if name not in current_features:
            raise KeyError(f"Content layer '{name}' missing from current features")
        current = current_features[name]
        layer_losses.append(torch.mean((current - target) ** 2))

    total_loss = torch.stack(layer_losses).sum()
    return total_loss * (content_weight / num_layers)


def total_variation_loss(image: torch.Tensor) -> torch.Tensor:
    """Calculate Total Variation loss (sum of absolute neighbor differences along H and W).

    Matches tf.image.total_variation:
    sum(|img[:, :, 1:, :] - img[:, :, :-1, :]|) + sum(|img[:, :, :, 1:] - img[:, :, :, :-1]|)

    Args:
        image: Tensor of shape (B, C, H, W).

    Returns:
        Scalar tensor with the total variation.
    """
    if image.ndim != 4:
        raise ValueError(f"Expected 4D image tensor (B, C, H, W), got shape {image.shape}")

    # Vertical differences (along height axis 2)
    diff_h = torch.abs(image[:, :, 1:, :] - image[:, :, :-1, :]).sum()
    # Horizontal differences (along width axis 3)
    diff_w = torch.abs(image[:, :, :, 1:] - image[:, :, :, :-1]).sum()

    return diff_h + diff_w
