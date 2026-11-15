"""Tests for portrait mode content weighting and style group behavior."""

from __future__ import annotations

from neural_canvas.cli import build_parser
from neural_canvas.styles import get_default_registry


def test_portrait_toggle_weights_per_style_group() -> None:
    """Verify portrait toggle sets cw=10000 on ornamental styles and preserves other styles."""
    parser = build_parser()
    registry = get_default_registry()

    # 1. The Kiss with --portrait -> cw=10000
    args = parser.parse_args(["assets/samples/dog.jpg", "--portrait", "--style", "the_kiss"])
    assert args.portrait is True
    preset = registry.get_preset(args.style)
    assert preset.style_group == "ornamental"
    # CLI resolution logic
    rec_cw = preset.recommended_weights.get("content_weight", 100.0)
    active_cw = (
        10000.0
        if (args.portrait and preset.style_group == "ornamental" and args.content_weight is None)
        else rec_cw
    )
    assert active_cw == 10000.0

    # 2. Composition VII with --portrait -> cw=10000
    args_comp = parser.parse_args(
        ["assets/samples/dog.jpg", "--portrait", "--style", "composition_vii_1913"]
    )
    preset_comp = registry.get_preset(args_comp.style)
    assert preset_comp.style_group == "ornamental"
    active_cw_comp = (
        10000.0
        if (
            args_comp.portrait
            and preset_comp.style_group == "ornamental"
            and args_comp.content_weight is None
        )
        else preset_comp.recommended_weights["content_weight"]
    )
    assert active_cw_comp == 10000.0

    # 3. The Starry Night with --portrait -> keeps its recommended content weight (90.0)
    args_starry = parser.parse_args(
        ["assets/samples/dog.jpg", "--portrait", "--style", "the_starry_night"]
    )
    preset_starry = registry.get_preset(args_starry.style)
    assert preset_starry.style_group != "ornamental"
    active_cw_starry = (
        10000.0
        if (
            args_starry.portrait
            and preset_starry.style_group == "ornamental"
            and args_starry.content_weight is None
        )
        else preset_starry.recommended_weights["content_weight"]
    )
    assert active_cw_starry == 90.0

    # 4. The Kiss without --portrait -> keeps default recommended weight 140.0
    args_kiss_no_port = parser.parse_args(["assets/samples/dog.jpg", "--style", "the_kiss"])
    assert args_kiss_no_port.portrait is False
    active_cw_kiss_no_port = (
        10000.0
        if (
            args_kiss_no_port.portrait
            and preset.style_group == "ornamental"
            and args_kiss_no_port.content_weight is None
        )
        else rec_cw
    )
    assert active_cw_kiss_no_port == 140.0

    # 5. User explicit override --content-weight 500 with --portrait takes precedence
    args_override = parser.parse_args(
        ["assets/samples/dog.jpg", "--portrait", "--style", "the_kiss", "--content-weight", "500"]
    )
    assert args_override.content_weight == 500.0
    active_cw_override = (
        10000.0
        if (
            args_override.portrait
            and preset.style_group == "ornamental"
            and args_override.content_weight is None
        )
        else args_override.content_weight
    )
    assert active_cw_override == 500.0
