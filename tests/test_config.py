"""Tests for configuration dataclass, validation, and JSON serialization."""

import json
from pathlib import Path

import pytest

from neural_canvas.config import (
    DEFAULT_SLIDER_POSITION,
    PRESETS,
    StyleTransferConfig,
    calculate_slider_content_weight,
)


def test_default_config_valid() -> None:
    cfg = StyleTransferConfig()
    assert cfg.steps == 1000
    assert cfg.max_dim == 512
    assert cfg.effective_style_max_dim == 512
    assert cfg.style_weight == 1e5
    assert cfg.content_weight == 100.0
    assert cfg.tv_weight == 0.05
    assert cfg.content_layers == ("conv4_2",)


def test_config_validation_errors() -> None:
    with pytest.raises(ValueError, match="style_weight must be non-negative"):
        StyleTransferConfig(style_weight=-1.0)

    with pytest.raises(ValueError, match="content_weight must be non-negative"):
        StyleTransferConfig(content_weight=-1.0)

    with pytest.raises(ValueError, match="tv_weight must be non-negative"):
        StyleTransferConfig(tv_weight=-5.0)

    with pytest.raises(ValueError, match="steps must be positive"):
        StyleTransferConfig(steps=0)

    with pytest.raises(ValueError, match="max_dim must be between"):
        StyleTransferConfig(max_dim=32)

    with pytest.raises(ValueError, match="max_dim must be between"):
        StyleTransferConfig(max_dim=1024)

    with pytest.raises(ValueError, match="learning_rate must be positive"):
        StyleTransferConfig(learning_rate=0.0)

    with pytest.raises(ValueError, match="init mode must be"):
        StyleTransferConfig(init="invalid")  # type: ignore[arg-type]


def test_config_json_roundtrip() -> None:
    cfg = StyleTransferConfig(
        steps=250,
        max_dim=384,
        style_max_dim=256,
        style_weight=0.05,
        content_weight=5000.0,
        tv_weight=15.0,
        learning_rate=0.015,
        betas=(0.95, 0.99),
        eps=0.01,
        content_layers=("conv4_2",),
        style_layers=("conv1_1", "conv2_1"),
        init="noise",
        seed=123,
        preview_every=25,
    )
    json_str = cfg.to_json()
    loaded = StyleTransferConfig.from_json(json_str)
    assert loaded == cfg
    assert loaded.effective_style_max_dim == 256


def test_quality_presets() -> None:
    for preset in PRESETS.values():
        assert preset.steps > 0
        assert 64 <= preset.max_dim <= 768
        assert preset.style_weight >= 0


def test_per_tier_preset_defaults() -> None:
    """Verify exact shipped per-tier parameterization and learning rate defaults."""
    # Draft tier
    assert PRESETS["draft"].parameterization == "sigmoid"
    assert PRESETS["draft"].learning_rate == 0.02
    assert PRESETS["draft"].steps == 150
    assert PRESETS["draft"].max_dim == 256

    # Balanced tier
    assert PRESETS["balanced"].parameterization == "sigmoid"
    assert PRESETS["balanced"].learning_rate == 0.03
    assert PRESETS["balanced"].steps == 400
    assert PRESETS["balanced"].max_dim == 384

    # High tier: clamped Adam at 1/4 preset LR (0.0075, cosine decay to 1%)
    assert PRESETS["high"].parameterization == "clamped"
    assert PRESETS["high"].learning_rate == 0.0075
    assert PRESETS["high"].lr_schedule == "cosine"
    assert PRESETS["high"].lr_min_ratio == 0.01
    assert PRESETS["high"].steps == 1000
    assert PRESETS["high"].max_dim == 512


def test_style_strength_slider_mapping() -> None:
    """Verify style strength slider mapping endpoints, default preservation, and portrait mode."""
    # 1. Position 1 gives 5000.0 (weakest style / maximum photo structure preservation)
    assert calculate_slider_content_weight(1, base_cw=120.0) == 5000.0

    # 2. Position 10 gives 90.0 (strongest style / intense painterly dominance)
    assert calculate_slider_content_weight(10, base_cw=120.0) == 90.0

    # 3. Default position gives exact preset recommended weight (unrounded)
    assert calculate_slider_content_weight(DEFAULT_SLIDER_POSITION, base_cw=120.0) == 120.0
    assert calculate_slider_content_weight(DEFAULT_SLIDER_POSITION, base_cw=90.0) == 90.0
    assert calculate_slider_content_weight(DEFAULT_SLIDER_POSITION, base_cw=80.0) == 80.0
    assert calculate_slider_content_weight(None, base_cw=140.0) == 140.0

    # 4. Portrait mode always gives 10000.0
    assert calculate_slider_content_weight(1, base_cw=120.0, portrait_mode=True) == 10000.0
    assert calculate_slider_content_weight(5, base_cw=120.0, portrait_mode=True) == 10000.0
    assert calculate_slider_content_weight(10, base_cw=120.0, portrait_mode=True) == 10000.0
    assert (
        calculate_slider_content_weight(DEFAULT_SLIDER_POSITION, base_cw=120.0, portrait_mode=True)
        == 10000.0
    )


def test_slider_content_weight_decreases_with_position() -> None:
    """Verify that content weight decreases (style strength increases) as slider moves 1 -> 10."""
    # Test monotonic decrease across non-default positions
    weights_left = [calculate_slider_content_weight(p, base_cw=120.0) for p in range(1, 6)]
    for i in range(len(weights_left) - 1):
        assert weights_left[i] > weights_left[i + 1]

    weights_right = [calculate_slider_content_weight(p, base_cw=120.0) for p in range(6, 11)]
    for i in range(len(weights_right) - 1):
        assert weights_right[i] > weights_right[i + 1]

    # Verify overall endpoints
    assert (
        calculate_slider_content_weight(1, base_cw=120.0)
        > calculate_slider_content_weight(DEFAULT_SLIDER_POSITION, base_cw=120.0)
        > calculate_slider_content_weight(10, base_cw=120.0)
    )


def test_tv_default_is_0_05() -> None:
    """Verify that TV default is 0.05 across config, presets, and styles.json."""
    # 1. Config dataclass default
    cfg = StyleTransferConfig()
    assert cfg.tv_weight == 0.05

    # 2. Quality presets in config.py
    for preset_name, preset_cfg in PRESETS.items():
        assert preset_cfg.tv_weight == 0.05, (
            f"Preset {preset_name} tv_weight is {preset_cfg.tv_weight}, expected 0.05"
        )

    # 3. styles.json catalog
    styles_json_path = Path("styles/styles.json")
    assert styles_json_path.exists()
    with open(styles_json_path, encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, list)
    for style_entry in data:
        rec = style_entry.get("recommended_weights", {})
        assert rec.get("tv_weight") == 0.05, (
            f"Style {style_entry['id']} recommended tv_weight is {rec.get('tv_weight')}, expected 0.05"
        )


def test_color_preserve_default_off() -> None:
    """Verify that color_preserve defaults to False across config and all presets."""
    cfg = StyleTransferConfig()
    assert cfg.color_preserve is False

    for name, p_cfg in PRESETS.items():
        assert p_cfg.color_preserve is False, f"Preset {name} has color_preserve=True"
