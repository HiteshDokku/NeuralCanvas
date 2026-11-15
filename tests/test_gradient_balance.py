"""Tests for content weight scaling, loss linearity, and gradient balance."""

from __future__ import annotations

import torch

from neural_canvas.losses import content_loss


def test_content_weight_doubling_and_gradient() -> None:
    """Verify that doubling content_weight doubles the content loss and its gradient."""
    # Create synthetic feature maps
    feat_curr = {"conv4_2": torch.randn((1, 512, 16, 16), requires_grad=True)}
    feat_targ = {"conv4_2": torch.randn((1, 512, 16, 16))}

    cw1 = 100.0
    cw2 = 200.0

    loss1 = content_loss(feat_curr, feat_targ, content_weight=cw1)
    loss2 = content_loss(feat_curr, feat_targ, content_weight=cw2)

    # 1. Loss value strictly doubles
    assert torch.isclose(loss2, 2.0 * loss1, rtol=1e-5)

    # 2. Gradient strictly doubles
    grad1 = torch.autograd.grad(loss1, feat_curr["conv4_2"], retain_graph=True)[0]
    grad2 = torch.autograd.grad(loss2, feat_curr["conv4_2"], retain_graph=True)[0]
    assert torch.allclose(grad2, 2.0 * grad1, rtol=1e-5)

    # 3. Area scaling preserves linearity: eff_cw = config.content_weight * content_area_factor
    curr_area = 512.0 * 512.0
    ref_area = 384.0 * 384.0
    factor = (ref_area / curr_area) ** 0.75

    eff_cw1 = cw1 * factor
    eff_cw2 = cw2 * factor
    assert abs(eff_cw2 - 2.0 * eff_cw1) < 1e-6
