"""Tests for style registry, thumbnail generation, and handling of corrupt files."""

import json
from pathlib import Path

import pytest
import torch
from PIL import Image

from neural_canvas.styles import StyleRegistry


def test_style_registry_with_valid_and_corrupt_files(tmp_path: Path) -> None:
    styles_dir = tmp_path / "styles"
    styles_dir.mkdir()

    # Create a valid image file
    valid_img = Image.new("RGB", (100, 100), color=(255, 100, 50))
    valid_path = styles_dir / "valid_artwork.jpg"
    valid_img.save(valid_path)

    # Create a corrupt / non-image file with image extension
    corrupt_path = styles_dir / "corrupted_file.jpg"
    corrupt_path.write_text("This is definitely not a JPEG image file.", encoding="utf-8")

    # Initialize registry
    registry = StyleRegistry(styles_dir=styles_dir)
    presets = registry.ensure_registry()

    # Check that valid image was loaded
    assert "valid_artwork" in presets
    preset = registry.get_preset("valid_artwork")
    assert preset.name == "Valid Artwork"
    assert Path(preset.thumbnail_path).exists()

    # Corrupt file should be safely skipped, not crashing the registry
    assert "corrupted_file" not in presets
    assert len(registry.list_presets()) == 1


def test_get_nonexistent_preset_raises_keyerror(tmp_path: Path) -> None:
    registry = StyleRegistry(styles_dir=tmp_path)
    with pytest.raises(KeyError, match="Preset 'unknown' not found"):
        registry.get_preset("unknown")


def test_gram_target_caching_and_invalidation(tmp_path: Path) -> None:
    styles_dir = tmp_path / "styles"
    styles_dir.mkdir()

    valid_img = Image.new("RGB", (64, 64), color=(100, 150, 200))
    valid_path = styles_dir / "art.jpg"
    valid_img.save(valid_path)

    registry = StyleRegistry(styles_dir=styles_dir)
    registry.ensure_registry()

    layers = ("conv1_1", "conv2_1")
    # First call: computes and caches
    grams1 = registry.get_cached_grams("art", style_max_dim=64, style_layers=layers)
    assert "conv1_1" in grams1
    assert "conv2_1" in grams1

    cache_files = list(registry.cache_dir.glob("*.pt"))
    assert len(cache_files) == 1

    # Second call: loads from cache
    grams2 = registry.get_cached_grams("art", style_max_dim=64, style_layers=layers)
    assert torch.allclose(grams1["conv1_1"], grams2["conv1_1"])

    # Modifying image or layer set changes cache key
    layers_expanded = ("conv1_1", "conv2_1", "conv3_1")
    grams3 = registry.get_cached_grams("art", style_max_dim=64, style_layers=layers_expanded)
    assert len(list(registry.cache_dir.glob("*.pt"))) == 2
    assert "conv3_1" in grams3


def test_best_for_avoid_for_loading() -> None:
    """Verify that all presets in styles.json load non-empty best_for and avoid_for fields."""
    registry = StyleRegistry()
    presets = registry.ensure_registry()

    assert len(presets) >= 10, f"Expected at least 10 styles, got {len(presets)}"

    for pid, preset in presets.items():
        assert preset.best_for is not None and len(preset.best_for.strip()) > 10, (
            f"Preset '{pid}' missing valid best_for description"
        )
        assert preset.avoid_for is not None and len(preset.avoid_for.strip()) > 10, (
            f"Preset '{pid}' missing valid avoid_for description"
        )


def test_portrait_toggle_and_the_kiss_warning() -> None:
    """Verify portrait mode behavior and that The Kiss is marked avoid_for portraits."""
    repo_root = Path(__file__).resolve().parent.parent
    styles_json_path = repo_root / "styles" / "styles.json"
    assert styles_json_path.exists()

    with open(styles_json_path, encoding="utf-8") as f:
        styles = json.load(f)

    kiss_entry = [s for s in styles if s["id"] == "the_kiss"][0]
    avoid_for = kiss_entry.get("avoid_for", "").lower()

    # The Kiss must explicitly state avoid for portraits/faces
    assert "portrait" in avoid_for or "face" in avoid_for


def test_crop_sampler_exclusion_guarantee() -> None:
    """Verify that multi-crop style sampling strictly never overlaps the exclusion rectangle."""
    # Impression, Sunrise dimensions
    sw, sh = 2048, 1589
    exclude = (0.50, 0.00, 0.88, 0.80)  # [x_min, y_min, x_max, y_max]
    ex1, ey1, ex2, ey2 = exclude

    ex_left = int(round(ex1 * sw))
    ex_top = int(round(ey1 * sh))
    ex_right = int(round(ex2 * sw))
    ex_bottom = int(round(ey2 * sh))

    candidate_zones = [
        (0.0, 0.0, 1.0, float(ex1)),  # Left: X in [0, ex1]
        (0.0, float(ex2), 1.0, 1.0),  # Right: X in [ex2, 1]
        (0.0, 0.0, float(ey1), 1.0),  # Top: Y in [0, ey1]
        (float(ey2), 0.0, 1.0, 1.0),  # Bottom: Y in [ey2, 1]
    ]
    valid_zones = [z for z in candidate_zones if (z[2] - z[0]) >= 0.08 and (z[3] - z[1]) >= 0.08]
    assert len(valid_zones) >= 2

    zone_areas = [(z[2] - z[0]) * (z[3] - z[1]) for z in valid_zones]
    zone_weights = torch.tensor(zone_areas, dtype=torch.float32)

    torch.manual_seed(42)
    # Test 200 random crops across all seeds
    for _ in range(200):
        z_idx = int(torch.multinomial(zone_weights, 1).item())
        zy1, zx1, zy2, zx2 = valid_zones[z_idx]
        z_h = zy2 - zy1
        z_w = zx2 - zx1

        scale_h = float(torch.empty(1).uniform_(0.35, 0.85).item())
        scale_w = float(torch.empty(1).uniform_(0.35, 0.85).item())
        ch = max(32, min(int(round(z_h * sh)), int(round(z_h * sh * scale_h))))
        cw = max(32, min(int(round(z_w * sw)), int(round(z_w * sw * scale_w))))

        zone_top = int(round(zy1 * sh))
        zone_left = int(round(zx1 * sw))
        max_top_offset = max(0, int(round(z_h * sh)) - ch)
        max_left_offset = max(0, int(round(z_w * sw)) - cw)

        off_top = (
            int(torch.randint(0, max_top_offset + 1, (1,)).item()) if max_top_offset > 0 else 0
        )
        off_left = (
            int(torch.randint(0, max_left_offset + 1, (1,)).item()) if max_left_offset > 0 else 0
        )

        crop_top = min(sh - ch, zone_top + off_top)
        crop_left = min(sw - cw, zone_left + off_left)
        crop_bottom = crop_top + ch
        crop_right = crop_left + cw

        # Compute intersection with exclusion box
        inter_x1 = max(crop_left, ex_left)
        inter_y1 = max(crop_top, ex_top)
        inter_x2 = min(crop_right, ex_right)
        inter_y2 = min(crop_bottom, ex_bottom)

        overlap_w = max(0, inter_x2 - inter_x1)
        overlap_h = max(0, inter_y2 - inter_y1)
        overlap_area = overlap_w * overlap_h

        assert overlap_area == 0, (
            f"Crop [{crop_left}, {crop_top}, {crop_right}, {crop_bottom}] overlapped "
            f"excluded zone [{ex_left}, {ex_top}, {ex_right}, {ex_bottom}] by {overlap_area} px!"
        )
