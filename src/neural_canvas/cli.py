"""Command-line interface for Neural Canvas."""

from __future__ import annotations

import argparse
import sys
import time

from .config import PRESETS, StyleTransferConfig
from .device import resolve_device
from .engine import StyleTransferEngine
from .image_io import save_png
from .styles import list_presets, resolve_style


def build_parser() -> argparse.ArgumentParser:
    """Construct argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="neural-canvas",
        description="Neural Canvas: Neural style transfer in PyTorch.",
    )
    parser.add_argument(
        "content",
        type=str,
        help="Path to content image.",
    )
    parser.add_argument(
        "--style",
        type=str,
        default=None,
        help="Style preset ID (e.g. 'the_starry_night', 'the_great_wave_off_kanagawa').",
    )
    parser.add_argument(
        "--style-image",
        type=str,
        default=None,
        help="Path to custom style image file.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="stylized.png",
        help="Path to save output image (default: stylized.png).",
    )
    parser.add_argument(
        "--preset",
        type=str,
        choices=["draft", "balanced", "high"],
        default=None,
        help="Quality preset: draft (150 steps, 256px), balanced (400, 384px), high (1000, 512px).",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        choices=["auto", "cuda", "cpu", "mps"],
        help="Device to use for computation (default: auto).",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=None,
        help="Total optimization steps.",
    )
    parser.add_argument(
        "--max-dim",
        type=int,
        default=None,
        help="Max long-edge dimension for content image (64 to 768).",
    )
    parser.add_argument(
        "--style-max-dim",
        type=int,
        default=None,
        help="Max long-edge dimension for style image (defaults to max-dim).",
    )
    parser.add_argument(
        "--style-weight",
        type=float,
        default=None,
        help="Weight multiplier for style loss (default: 1e5).",
    )
    parser.add_argument(
        "--content-weight",
        type=float,
        default=None,
        help="Weight multiplier for content loss (calibrated range: 90.0 to 5000.0; weights below ~500 look visually similar, visible change starts above ~1000).",
    )
    parser.add_argument(
        "--tv-weight",
        type=float,
        default=None,
        help="Weight multiplier for total variation loss (default: 0.05).",
    )
    parser.add_argument(
        "--content-layer",
        type=str,
        default=None,
        help="Content representation layer (default: conv4_2; alternative: conv5_2).",
    )
    parser.add_argument(
        "--lr",
        "--learning-rate",
        type=float,
        default=None,
        dest="learning_rate",
        help="Optimizer learning rate (default: 0.03).",
    )
    parser.add_argument(
        "--init",
        type=str,
        choices=["content", "noise"],
        default=None,
        help="Initial image canvas: 'content' or 'noise' (default: content).",
    )
    parser.add_argument(
        "--parameterization",
        type=str,
        choices=["sigmoid", "clamped"],
        default=None,
        help="Image parameterization: 'sigmoid' (smoother at low resolution, updates very dark and very bright pixels more slowly) or 'clamped' (clamped Adam in [0, 1]).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility.",
    )
    parser.add_argument(
        "--preview-every",
        type=int,
        default=None,
        help="Step interval for progress logs.",
    )
    parser.add_argument(
        "--portrait",
        action="store_true",
        help="Enable portrait mode to preserve human facial features (uses content weight 10000 on ornamental styles).",
    )
    parser.add_argument(
        "--color-preserve",
        "--preserve-colors",
        action="store_true",
        dest="color_preserve",
        help="Preserve content photo colors and transfer style luminance and texture only.",
    )
    parser.add_argument(
        "--list-styles",
        action="store_true",
        help="List available preset styles and exit.",
    )
    return parser


def print_progress_bar(
    iteration: int,
    total: int,
    total_loss: float,
    elapsed: float,
    length: int = 30,
) -> None:
    """Print ASCII progress bar in console."""
    percent = f"{100 * (iteration / float(total)):.1f}"
    filled_len = int(length * iteration // total)
    bar = "█" * filled_len + "-" * (length - filled_len)
    rate = iteration / elapsed if elapsed > 0 else 0
    msg = (
        f"\rProgress: |{bar}| {iteration}/{total} ({percent}%) "
        f"Loss: {total_loss:.2e} [{rate:.1f} it/s]"
    )
    sys.stdout.write(msg)
    sys.stdout.flush()
    if iteration == total:
        sys.stdout.write("\n")


def main(args: list[str] | None = None) -> int:
    """Main CLI entrypoint."""
    parser = build_parser()
    parsed = parser.parse_args(args)

    if parsed.list_styles:
        presets = list_presets()
        print(f"\nAvailable style presets ({len(presets)}):")
        for p in presets:
            print(f"  - {p.id:35} : {p.name} ({p.artist}, {p.year})")
        return 0

    if not parsed.style and not parsed.style_image:
        print(
            "Error: either --style <preset_id> or --style-image <path> is required.",
            file=sys.stderr,
        )
        return 1

    # Base configuration from preset or defaults
    if parsed.preset:
        base_cfg = PRESETS[parsed.preset]
    else:
        base_cfg = StyleTransferConfig()

    # Override with explicit CLI flags
    cfg_kwargs = {}
    for attr in [
        "steps",
        "max_dim",
        "style_max_dim",
        "style_weight",
        "content_weight",
        "tv_weight",
        "learning_rate",
        "init",
        "parameterization",
        "seed",
        "preview_every",
    ]:
        val = getattr(parsed, attr)
        if val is not None:
            cfg_kwargs[attr] = val

    if parsed.content_layer:
        cfg_kwargs["content_layers"] = (parsed.content_layer,)

    # Portrait mode handling: ornamental styles get content_weight = 10000 unless user explicitly overrode
    if parsed.portrait and parsed.content_weight is None:
        p_id = parsed.style.lower().strip() if parsed.style else ""
        if p_id == "the_kiss":
            print(
                "Warning: The Kiss ornamental gold foil patterns can cover facial features and hands even in Portrait mode. Composition VII, The Starry Night, or The Great Wave are recommended for portraits.",
                file=sys.stderr,
            )
        elif p_id == "composition_vii_1913":
            cfg_kwargs["content_weight"] = 10000.0

    if parsed.color_preserve:
        cfg_kwargs["color_preserve"] = True

    # Check preset recommended weights
    if parsed.style:
        try:
            from .styles import StyleRegistry

            reg = StyleRegistry()
            p_obj = reg.get_preset(parsed.style.lower().strip())
            rec_settings = p_obj.recommended_weights or {}
            if "multi_crop_style" in rec_settings:
                cfg_kwargs.setdefault("multi_crop_style", bool(rec_settings["multi_crop_style"]))
            if "style_crop_exclude" in rec_settings:
                cfg_kwargs.setdefault("style_crop_exclude", rec_settings["style_crop_exclude"])
            if "style_layer_weights" in rec_settings:
                cfg_kwargs.setdefault("style_layer_weights", rec_settings["style_layer_weights"])
        except Exception:
            pass

    config = StyleTransferConfig(
        steps=cfg_kwargs.get("steps", base_cfg.steps),
        max_dim=cfg_kwargs.get("max_dim", base_cfg.max_dim),
        style_max_dim=cfg_kwargs.get("style_max_dim", base_cfg.style_max_dim),
        style_weight=cfg_kwargs.get("style_weight", base_cfg.style_weight),
        content_weight=cfg_kwargs.get("content_weight", base_cfg.content_weight),
        tv_weight=cfg_kwargs.get("tv_weight", base_cfg.tv_weight),
        content_layers=cfg_kwargs.get("content_layers", base_cfg.content_layers),
        learning_rate=cfg_kwargs.get("learning_rate", base_cfg.learning_rate),
        parameterization=cfg_kwargs.get("parameterization", base_cfg.parameterization),
        multi_crop_style=cfg_kwargs.get("multi_crop_style", base_cfg.multi_crop_style),
        style_crop_exclude=cfg_kwargs.get("style_crop_exclude", base_cfg.style_crop_exclude),
        style_layer_weights=cfg_kwargs.get("style_layer_weights", base_cfg.style_layer_weights),
        init=cfg_kwargs.get("init", base_cfg.init),
        color_preserve=cfg_kwargs.get("color_preserve", base_cfg.color_preserve),
        seed=cfg_kwargs.get("seed", base_cfg.seed),
        preview_every=cfg_kwargs.get("preview_every", base_cfg.preview_every),
    )

    device = resolve_device(parsed.device)
    print(f"Neural Canvas starting on {device}...")
    print(
        f"Resolution: {config.max_dim}px, Steps: {config.steps}, "
        f"Style weight: {config.style_weight:.1e}, Content weight: {config.content_weight:.1e}"
    )

    # Resolve style image
    style_source = parsed.style_image if parsed.style_image else parsed.style
    try:
        style_tensor = resolve_style(
            style_source, max_dim=config.effective_style_max_dim, device=device
        )
    except Exception as e:
        print(f"Error resolving style: {e}", file=sys.stderr)
        return 1

    engine = StyleTransferEngine(config=config, device=device)
    print("Preparing style and content targets...")
    engine.prepare(parsed.content, style_tensor)

    print("Running style transfer optimization...")
    start_time = time.time()
    last_result = None

    try:
        for result in engine.run():
            last_result = result
            elapsed = time.time() - start_time
            print_progress_bar(
                result.step,
                config.steps,
                result.total_loss,
                elapsed,
            )
    except Exception as err:
        print(f"\nExecution failed: {err}", file=sys.stderr)
        return 1

    if last_result is not None:
        out_path = save_png(last_result.image, parsed.output)
        total_time = time.time() - start_time
        print(f"Done in {total_time:.2f}s! Saved output to: {out_path}")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
