"""Tests for loss functions and Gram matrix computation."""

import torch

from neural_canvas.losses import content_loss, gram_matrix, style_loss, total_variation_loss


def test_gram_matrix_shape_and_symmetry() -> None:
    # Batch=2, Channels=16, H=32, W=32
    feat = torch.randn(2, 16, 32, 32)
    gram = gram_matrix(feat)

    assert gram.shape == (2, 16, 16)
    # Check symmetry: G == G^T
    for b in range(2):
        g = gram[b]
        diff = torch.max(torch.abs(g - g.T))
        assert diff.item() < 1e-5


def test_style_loss_zero_for_identical() -> None:
    # Target and current are identical
    g1 = torch.randn(1, 8, 8)
    g2 = torch.randn(1, 16, 16)
    targets = {"layer1": g1, "layer2": g2}
    current = {"layer1": g1.clone(), "layer2": g2.clone()}

    loss = style_loss(current, targets, style_weight=1.0)
    assert torch.isclose(loss, torch.tensor(0.0), atol=1e-7)


def test_content_loss_zero_for_identical() -> None:
    c1 = torch.randn(1, 16, 28, 28)
    targets = {"block5_conv2": c1}
    current = {"block5_conv2": c1.clone()}

    loss = content_loss(current, targets, content_weight=1.0)
    assert torch.isclose(loss, torch.tensor(0.0), atol=1e-7)


def test_tv_loss_constant_and_noise() -> None:
    # Constant image has 0 TV loss
    constant_img = torch.full((1, 3, 64, 64), 0.5)
    tv_const = total_variation_loss(constant_img)
    assert torch.isclose(tv_const, torch.tensor(0.0), atol=1e-7)

    # Random noise has positive TV loss
    noise_img = torch.rand(1, 3, 64, 64)
    tv_noise = total_variation_loss(noise_img)
    assert tv_noise.item() > 0.0
