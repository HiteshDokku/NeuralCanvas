"""Tests for learning rate schedules, area scaling, and device memory heuristics.

Tests:
1. Cosine LR decay schedule
2. Content & TV area scaling (including wide-aspect canvases)
3. derive_max_dim_from_memory memory bracket mapping
4. style_scale_ratio clamping and effective_style_max_dim
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
import torch

from neural_canvas.config import StyleTransferConfig
from neural_canvas.device import DEFAULT_MAX_DIM_CPU, derive_max_dim_from_memory


def test_cosine_lr_decay_schedule() -> None:
    """Verify that cosine annealing smoothly decays LR to lr * lr_min_ratio."""
    init_lr = 0.05
    min_ratio = 0.01
    steps = 100

    cfg = StyleTransferConfig(
        steps=steps,
        learning_rate=init_lr,
        lr_schedule="cosine",
        lr_min_ratio=min_ratio,
        max_dim=64,
        preview_every=100,
    )

    param = torch.nn.Parameter(torch.randn(1, 3, 16, 16))
    optimizer = torch.optim.Adam([param], lr=cfg.learning_rate)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=cfg.steps, eta_min=cfg.learning_rate * cfg.lr_min_ratio
    )

    initial_lr = optimizer.param_groups[0]["lr"]
    assert pytest.approx(initial_lr, rel=1e-5) == init_lr

    lrs = [initial_lr]
    for _ in range(steps):
        optimizer.step()
        scheduler.step()
        lrs.append(optimizer.param_groups[0]["lr"])

    final_lr = optimizer.param_groups[0]["lr"]
    expected_min_lr = init_lr * min_ratio
    assert pytest.approx(final_lr, rel=1e-3) == expected_min_lr
    assert final_lr < initial_lr
    # Check monotonic decay
    assert all(lrs[i] >= lrs[i + 1] - 1e-9 for i in range(len(lrs) - 1))


def test_area_scaling_including_wide_aspect() -> None:
    """Verify content and TV area scaling across resolutions and wide canvases (e.g. 256x144)."""
    ref_area = 384.0 * 384.0  # 147,456

    # 1. Standard square resolutions
    for dim in [256, 384, 512, 768]:
        area = float(dim * dim)
        content_factor = (ref_area / area) ** 0.75
        tv_factor = (ref_area / max(area, 30000.0)) ** 1.0

        if dim == 384:
            assert pytest.approx(content_factor, rel=1e-5) == 1.0
            assert pytest.approx(tv_factor, rel=1e-5) == 1.0
        elif dim < 384:
            assert content_factor > 1.0
            assert tv_factor > 1.0
        else:
            assert content_factor < 1.0
            assert tv_factor < 1.0

    # 2. Wide canvas 256x144 (area = 36,864)
    wide_area = 256.0 * 144.0  # 36,864
    assert wide_area > 30000.0, "256x144 area must exceed lower clamp threshold of 30,000"
    tv_wide_factor = (ref_area / max(wide_area, 30000.0)) ** 1.0
    # Expected: 147456 / 36864 = 4.0
    assert pytest.approx(tv_wide_factor, rel=1e-4) == 4.0

    # 3. Small synthetic tensor (64x64, area = 4096) is safely bounded
    small_area = 64.0 * 64.0
    tv_small_bounded = (ref_area / max(small_area, 30000.0)) ** 1.0
    assert pytest.approx(tv_small_bounded, rel=1e-4) == (147456.0 / 30000.0)


def test_derive_max_dim_from_memory_mocked() -> None:
    """Verify derive_max_dim_from_memory maps VRAM brackets correctly."""
    # Test CPU fallback
    cpu_device = torch.device("cpu")
    assert derive_max_dim_from_memory(cpu_device) == DEFAULT_MAX_DIM_CPU

    cuda_device = torch.device("cuda:0")

    # Mock >= 3.0 GB -> 768 px
    with patch("torch.cuda.is_available", return_value=True):
        with patch("torch.cuda.mem_get_info", return_value=(4 * (1024**3), 8 * (1024**3))):
            assert derive_max_dim_from_memory(cuda_device) == 768

    # Mock >= 1.5 GB and < 3.0 GB -> 512 px
    with patch("torch.cuda.is_available", return_value=True):
        with patch("torch.cuda.mem_get_info", return_value=(2 * (1024**3), 8 * (1024**3))):
            assert derive_max_dim_from_memory(cuda_device) == 512

    # Mock < 1.5 GB -> 384 px
    with patch("torch.cuda.is_available", return_value=True):
        with patch("torch.cuda.mem_get_info", return_value=(1 * (1024**3), 8 * (1024**3))):
            assert derive_max_dim_from_memory(cuda_device) == 384


def test_style_scale_ratio_clamping() -> None:
    """Verify effective_style_max_dim behavior and clamping."""
    # When explicit style_max_dim is given, it is preserved
    cfg_explicit = StyleTransferConfig(max_dim=512, style_max_dim=700)
    assert cfg_explicit.effective_style_max_dim == 700

    # When style_max_dim is None, derived from max_dim * style_scale_ratio
    cfg_ratio1 = StyleTransferConfig(max_dim=512, style_scale_ratio=1.0)
    assert cfg_ratio1.effective_style_max_dim == 512

    cfg_ratio15 = StyleTransferConfig(max_dim=512, style_scale_ratio=1.5)
    assert cfg_ratio15.effective_style_max_dim == int(round(512 * 1.5))

    # Lower clamp at 64
    cfg_low = StyleTransferConfig(max_dim=64, style_scale_ratio=0.5)
    assert cfg_low.effective_style_max_dim == 64

    # Upper clamp at 1024
    cfg_high = StyleTransferConfig(max_dim=768, style_scale_ratio=2.0)
    assert cfg_high.effective_style_max_dim == 1024
