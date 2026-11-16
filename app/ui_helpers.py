"""Neural Canvas UI Helper Functions and Utilities."""

from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Any

from PIL import Image

from neural_canvas.config import PRESETS, StyleTransferConfig


def load_theme_css(css_path: Path) -> str:
    """Read theme stylesheet content safely."""
    if css_path.exists():
        return css_path.read_text(encoding="utf-8")
    return ""


def pil_to_base64_data_uri(img: Image.Image, format: str = "JPEG") -> str:
    """Encode PIL Image to a base64 data URI string."""
    buf = io.BytesIO()
    if format == "JPEG" and img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img.save(buf, format=format, quality=85 if format == "JPEG" else None)
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    mime = "image/jpeg" if format == "JPEG" else "image/png"
    return f"data:{mime};base64,{encoded}"


def get_available_samples(samples_dir: Path) -> list[str]:
    """Return sorted filenames of valid sample content images."""
    if not samples_dir.exists():
        return []
    valid_files: list[str] = []
    for f in sorted(samples_dir.iterdir()):
        if f.is_file() and f.suffix.lower() in [".jpg", ".png", ".jpeg", ".webp"]:
            try:
                with Image.open(f) as img:
                    w, h = img.size
                    if w >= 64 and h >= 64:
                        valid_files.append(f.name)
            except Exception:
                continue
    return valid_files


def count_parameter_overrides(
    config: StyleTransferConfig,
    base_config: StyleTransferConfig,
    rec_settings: dict[str, Any] | None = None,
) -> int:
    """Count how many active parameters deviate from current preset defaults."""
    diff_count = 0
    if config.steps != base_config.steps:
        diff_count += 1
    if config.max_dim != base_config.max_dim:
        diff_count += 1
    if abs(config.learning_rate - base_config.learning_rate) > 1e-6:
        diff_count += 1
    if config.parameterization != base_config.parameterization:
        diff_count += 1
    if config.init != "content":
        diff_count += 1
    if config.seed is not None and config.seed != 42:
        diff_count += 1
    if config.preview_every != base_config.preview_every:
        diff_count += 1

    expected_layer = rec_settings.get("content_layer", "conv4_2") if rec_settings else "conv4_2"
    if config.content_layers != (expected_layer,):
        diff_count += 1

    expected_scale = float(rec_settings.get("style_scale_ratio", 1.0)) if rec_settings else 1.0
    if (
        config.style_scale_ratio is not None
        and abs(config.style_scale_ratio - expected_scale) > 1e-4
    ):
        diff_count += 1

    return diff_count


def build_config_from_ui_state(
    quality_preset: str = "balanced",
    rec_settings: dict[str, Any] | None = None,
    derived_cw: float | None = None,
    color_preserve: bool = False,
    overrides: dict[str, Any] | None = None,
) -> StyleTransferConfig:
    """Build a StyleTransferConfig from UI preset and user or style state."""
    base_config = PRESETS.get(quality_preset, PRESETS["balanced"])
    overrides = overrides or {}

    if derived_cw is not None:
        default_cw = derived_cw
    elif rec_settings and "content_weight" in rec_settings:
        default_cw = float(rec_settings["content_weight"])
    else:
        default_cw = float(base_config.content_weight)

    default_sw = (
        float(rec_settings["style_weight"])
        if rec_settings and "style_weight" in rec_settings
        else float(base_config.style_weight)
    )
    default_tv = (
        float(rec_settings["tv_weight"])
        if rec_settings and "tv_weight" in rec_settings
        else float(base_config.tv_weight)
    )
    default_scale = (
        float(rec_settings["style_scale_ratio"])
        if rec_settings and "style_scale_ratio" in rec_settings
        else float(base_config.style_scale_ratio)
    )
    default_content_layer = (
        (rec_settings["content_layer"],)
        if rec_settings and "content_layer" in rec_settings
        else base_config.content_layers
    )
    default_multi_crop = (
        bool(rec_settings["multi_crop_style"])
        if rec_settings and "multi_crop_style" in rec_settings
        else base_config.multi_crop_style
    )
    default_num_crops = (
        int(rec_settings["num_style_crops"])
        if rec_settings and "num_style_crops" in rec_settings
        else base_config.num_style_crops
    )
    default_crop_exclude = (
        rec_settings.get("style_crop_exclude") if rec_settings else base_config.style_crop_exclude
    )
    default_layer_weights = (
        rec_settings.get("style_layer_weights") if rec_settings else base_config.style_layer_weights
    )

    return StyleTransferConfig(
        style_weight=overrides.get("style_weight", default_sw),
        content_weight=overrides.get("content_weight", default_cw),
        tv_weight=overrides.get("tv_weight", default_tv),
        steps=overrides.get("steps", base_config.steps),
        max_dim=overrides.get("max_dim", base_config.max_dim),
        style_max_dim=overrides.get("style_max_dim", base_config.style_max_dim),
        style_scale_ratio=overrides.get("style_scale_ratio", default_scale),
        learning_rate=overrides.get("learning_rate", base_config.learning_rate),
        lr_schedule=overrides.get("lr_schedule", base_config.lr_schedule),
        lr_min_ratio=overrides.get("lr_min_ratio", base_config.lr_min_ratio),
        betas=overrides.get("betas", base_config.betas),
        eps=overrides.get("eps", base_config.eps),
        content_layers=overrides.get("content_layers", default_content_layer),
        style_layers=overrides.get("style_layers", base_config.style_layers),
        init=overrides.get("init", "content"),
        optimizer=overrides.get("optimizer", base_config.optimizer),
        parameterization=overrides.get("parameterization", base_config.parameterization),
        sigmoid_init_clamp=overrides.get("sigmoid_init_clamp", base_config.sigmoid_init_clamp),
        multi_crop_style=overrides.get("multi_crop_style", default_multi_crop),
        num_style_crops=overrides.get("num_style_crops", default_num_crops),
        style_crop_exclude=overrides.get("style_crop_exclude", default_crop_exclude),
        style_layer_weights=overrides.get("style_layer_weights", default_layer_weights),
        color_preserve=overrides.get("color_preserve", color_preserve),
        seed=overrides.get("seed", 42),
        preview_every=overrides.get("preview_every", base_config.preview_every),
    )
