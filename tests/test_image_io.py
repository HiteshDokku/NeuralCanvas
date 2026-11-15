"""Tests for image loading, resizing, dimension calculations, and format conversions."""

from pathlib import Path

import numpy as np
import torch
from PIL import Image

from neural_canvas.image_io import (
    calculate_dimensions,
    load_image,
    save_png,
    tensor_to_pil,
)


def test_calculate_dimensions_aspect_ratio_and_multiple_of_8() -> None:
    # 800 x 600 image with max_dim 512
    w, h = calculate_dimensions(800, 600, max_dim=512)
    assert w <= 512
    assert h <= 512
    assert w % 8 == 0
    assert h % 8 == 0
    assert w >= 64
    assert h >= 64

    # Aspect ratio should be close to 800/600 = 1.333
    ratio_orig = 800 / 600
    ratio_new = w / h
    assert abs(ratio_orig - ratio_new) < 0.05


def test_calculate_dimensions_minimum_64() -> None:
    w, h = calculate_dimensions(30, 20, max_dim=512)
    assert w >= 64
    assert h >= 64
    assert w % 8 == 0
    assert h % 8 == 0


def test_image_load_and_save_roundtrip(tmp_path: Path) -> None:
    # Create a synthetic PIL image
    img = Image.new("RGB", (200, 150), color=(120, 180, 240))
    test_file = tmp_path / "test.png"
    img.save(test_file)

    tensor = load_image(test_file, max_dim=128)
    assert isinstance(tensor, torch.Tensor)
    assert tensor.ndim == 4
    assert tensor.shape[0] == 1
    assert tensor.shape[1] == 3
    assert tensor.shape[2] % 8 == 0
    assert tensor.shape[3] % 8 == 0
    assert tensor.min() >= 0.0
    assert tensor.max() <= 1.0

    pil_out = tensor_to_pil(tensor)
    assert pil_out.size == (tensor.shape[3], tensor.shape[2])

    save_path = tmp_path / "out.png"
    save_png(tensor, save_path)
    assert save_path.exists()


def test_color_transfer_preserves_content_chrominance() -> None:
    from neural_canvas.image_io import transfer_color

    content = torch.full((1, 3, 64, 64), 0.8)  # Bright content
    content[:, 0, :, :] = 0.9  # Red tint
    stylized = torch.full((1, 3, 64, 64), 0.2)  # Dark blue stylized
    stylized[:, 2, :, :] = 0.8

    result = transfer_color(content, stylized)
    assert result.shape == (1, 3, 64, 64)
    assert result.min() >= 0.0
    assert result.max() <= 1.0


def test_is_grayscale_image_detection() -> None:
    from neural_canvas.image_io import is_grayscale_image

    # Grayscale PIL image
    gray_pil = Image.new("L", (100, 100), color=128)
    assert is_grayscale_image(gray_pil) is True

    # Grayscale photo saved in RGB format (R == G == B)
    rgb_gray_pil = Image.new("RGB", (100, 100), color=(140, 140, 140))
    assert is_grayscale_image(rgb_gray_pil) is True

    # Color photo (vibrant saturated red)
    color_pil = Image.new("RGB", (100, 100), color=(240, 60, 40))
    assert is_grayscale_image(color_pil) is False

    # Grayscale Tensor
    gray_tensor = torch.full((1, 3, 64, 64), 0.5)
    assert is_grayscale_image(gray_tensor) is True

    # Color Tensor
    color_tensor = torch.full((1, 3, 64, 64), 0.5)
    color_tensor[:, 0, :, :] = 0.9  # Red channel boosted
    assert is_grayscale_image(color_tensor) is False


def test_grayscale_detection() -> None:
    """Verify grayscale detection on synthetic images and sample assets."""
    from neural_canvas.image_io import is_grayscale_image

    # Synthetic 3-channel RGB image with identical channels (pure grayscale)
    gray_arr = np.full((100, 100, 3), 128, dtype=np.uint8)
    gray_pil = Image.fromarray(gray_arr, mode="RGB")
    assert is_grayscale_image(gray_pil) is True

    # Synthetic 3-channel RGB image with color tint (R != G)
    color_arr = np.copy(gray_arr)
    color_arr[:, :, 0] = 200  # Add red
    color_pil = Image.fromarray(color_arr, mode="RGB")
    assert is_grayscale_image(color_pil) is False

    # PIL Image mode 'L' (single-channel)
    mode_l_img = Image.new("L", (50, 50), color=100)
    assert is_grayscale_image(mode_l_img) is True

    # Real assets test
    samples_dir = Path("assets/samples")
    if (samples_dir / "portrait_migrant_mother.jpg").exists():
        with Image.open(samples_dir / "portrait_migrant_mother.jpg") as im:
            assert is_grayscale_image(im) is True

    if (samples_dir / "landscape_tetons.jpg").exists():
        with Image.open(samples_dir / "landscape_tetons.jpg") as im:
            assert is_grayscale_image(im) is True

    if (samples_dir / "dog.jpg").exists():
        with Image.open(samples_dir / "dog.jpg") as im:
            assert is_grayscale_image(im) is False
