"""Image loading, preprocessing, validation, and serialization for Neural Canvas."""

from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageOps

ImageSource = str | Path | bytes | Image.Image


def calculate_dimensions(width: int, height: int, max_dim: int | None = None) -> tuple[int, int]:
    """Calculate target dimensions preserving aspect ratio, rounded to multiples of 8.

    Args:
        width: Original image width.
        height: Original image height.
        max_dim: Maximum allowed long-edge dimension (between 64 and 768).

    Returns:
        tuple of (new_width, new_height), both multiples of 8 and at least 64.
    """
    if width <= 0 or height <= 0:
        raise ValueError(f"Image dimensions must be positive, got width={width}, height={height}")

    long_edge = max(width, height)
    if max_dim is not None and long_edge > max_dim:
        scale = max_dim / long_edge
        w = width * scale
        h = height * scale
    else:
        w = float(width)
        h = float(height)

    # Round to nearest multiple of 8, with a hard minimum of 64
    new_w = max(64, round(w / 8.0) * 8)
    new_h = max(64, round(h / 8.0) * 8)

    # If rounding caused long edge to exceed max_dim when max_dim is provided, adjust down
    if max_dim is not None:
        if new_w > max_dim:
            new_w = (max_dim // 8) * 8
        if new_h > max_dim:
            new_h = (max_dim // 8) * 8

    return int(new_w), int(new_h)


def load_image(
    source: ImageSource,
    max_dim: int | None = None,
    device: torch.device | None = None,
) -> torch.Tensor:
    """Load an image, apply EXIF orientation, convert to RGB, resize, and convert to Tensor.

    Args:
        source: File path, bytes, or PIL Image.
        max_dim: Maximum long edge size in pixels.
        device: PyTorch device to place tensor on.

    Returns:
        Tensor of shape (1, 3, H, W) with float32 values in [0.0, 1.0].
    """
    if isinstance(source, Image.Image):
        pil_img = source
    elif isinstance(source, (str, Path)):
        path = Path(source)
        if not path.is_file():
            raise FileNotFoundError(f"Image file not found: {path}")
        try:
            pil_img = Image.open(path)
        except Exception as e:
            raise ValueError(f"Failed to open image file {path}: {e}") from e
    elif isinstance(source, (bytes, bytearray)):
        try:
            pil_img = Image.open(io.BytesIO(source))
        except Exception as e:
            raise ValueError(f"Failed to parse image from byte buffer: {e}") from e
    else:
        raise TypeError(f"Unsupported image source type: {type(source)}")

    # Apply EXIF rotation if present
    try:
        pil_img = ImageOps.exif_transpose(pil_img)
    except Exception:
        pass

    # Ensure RGB
    if pil_img.mode != "RGB":
        pil_img = pil_img.convert("RGB")

    orig_w, orig_h = pil_img.size
    target_w, target_h = calculate_dimensions(orig_w, orig_h, max_dim=max_dim)

    if (orig_w, orig_h) != (target_w, target_h):
        pil_img = pil_img.resize((target_w, target_h), resample=Image.Resampling.LANCZOS)

    # Convert to Tensor [1, 3, H, W] in [0, 1]
    arr = np.array(pil_img, dtype=np.float32) / 255.0
    tensor = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0)

    if device is not None:
        tensor = tensor.to(device)

    return tensor


def tensor_to_pil(tensor: torch.Tensor) -> Image.Image:
    """Convert a float32 PyTorch tensor in [0, 1] to a PIL RGB Image.

    Args:
        tensor: Tensor of shape (1, 3, H, W) or (3, H, W).

    Returns:
        PIL Image in RGB mode.
    """
    t = tensor.detach().cpu()
    if t.ndim == 4:
        if t.shape[0] != 1:
            raise ValueError(f"Expected batch size 1, got shape {t.shape}")
        t = t.squeeze(0)

    if t.ndim != 3 or t.shape[0] != 3:
        raise ValueError(f"Expected tensor of shape (3, H, W), got {t.shape}")

    t = torch.clamp(t, 0.0, 1.0)
    arr = (t.permute(1, 2, 0).numpy() * 255.0).round().astype(np.uint8)
    return Image.fromarray(arr, mode="RGB")


def save_png(image: torch.Tensor | Image.Image, output_path: str | Path) -> Path:
    """Save an image (Tensor or PIL Image) as a PNG file.

    Args:
        image: Tensor in [0, 1] or PIL Image.
        output_path: Destination file path.

    Returns:
        Resolved Path to the saved file.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(image, torch.Tensor):
        pil_img = tensor_to_pil(image)
    elif isinstance(image, Image.Image):
        pil_img = image
    else:
        raise TypeError(f"Expected torch.Tensor or PIL.Image, got {type(image)}")

    pil_img.save(path, format="PNG")
    return path


def rgb_to_ycbcr(rgb: torch.Tensor) -> torch.Tensor:
    """Convert RGB tensor (B, 3, H, W) in [0, 1] to YCbCr."""
    r = rgb[:, 0:1, :, :]
    g = rgb[:, 1:2, :, :]
    b = rgb[:, 2:3, :, :]
    y = 0.299 * r + 0.587 * g + 0.114 * b
    cb = -0.168736 * r - 0.331264 * g + 0.5 * b + 0.5
    cr = 0.5 * r - 0.418688 * g - 0.081312 * b + 0.5
    return torch.cat([y, cb, cr], dim=1)


def ycbcr_to_rgb(ycbcr: torch.Tensor) -> torch.Tensor:
    """Convert YCbCr tensor (B, 3, H, W) to RGB in [0, 1]."""
    y = ycbcr[:, 0:1, :, :]
    cb = ycbcr[:, 1:2, :, :] - 0.5
    cr = ycbcr[:, 2:3, :, :] - 0.5
    r = y + 1.402 * cr
    g = y - 0.344136 * cb - 0.714136 * cr
    b = y + 1.772 * cb
    return torch.clamp(torch.cat([r, g, b], dim=1), 0.0, 1.0)


def transfer_color(content_rgb: torch.Tensor, stylized_rgb: torch.Tensor) -> torch.Tensor:
    """Preserve color from original content image while retaining stylized texture.

    Combines stylized luminance (Y) with content chrominance (Cb, Cr).
    """
    if content_rgb.shape != stylized_rgb.shape:
        # Resize content to match stylized shape if needed
        h, w = stylized_rgb.shape[2], stylized_rgb.shape[3]
        content_rgb = torch.nn.functional.interpolate(
            content_rgb, size=(h, w), mode="bilinear", align_corners=False
        )

    content_ycbcr = rgb_to_ycbcr(content_rgb)
    stylized_ycbcr = rgb_to_ycbcr(stylized_rgb)
    blended = torch.cat([stylized_ycbcr[:, 0:1, :, :], content_ycbcr[:, 1:3, :, :]], dim=1)
    return ycbcr_to_rgb(blended)


def is_grayscale_image(img: Image.Image | torch.Tensor, threshold: float = 3.0) -> bool:
    """Detect whether an image is grayscale by checking channel differences.

    Args:
        img: PIL Image or torch.Tensor in (1, 3, H, W) or (3, H, W).
        threshold: Max average channel difference threshold (0-255 scale).

    Returns:
        True if the image is grayscale or near-grayscale with negligible color variance.
    """
    if isinstance(img, Image.Image):
        if img.mode in ("L", "1"):
            return True
        rgb = np.array(img.convert("RGB"), dtype=np.float32)
        diff_rg = np.abs(rgb[:, :, 0] - rgb[:, :, 1]).mean()
        diff_gb = np.abs(rgb[:, :, 1] - rgb[:, :, 2]).mean()
        diff_br = np.abs(rgb[:, :, 2] - rgb[:, :, 0]).mean()
        return float(max(diff_rg, diff_gb, diff_br)) < threshold

    if isinstance(img, torch.Tensor):
        t = img.detach()
        if t.ndim == 4:
            t = t.squeeze(0)
        diff_rg = float(torch.abs(t[0] - t[1]).mean().item() * 255.0)
        diff_gb = float(torch.abs(t[1] - t[2]).mean().item() * 255.0)
        diff_br = float(torch.abs(t[2] - t[0]).mean().item() * 255.0)
        return max(diff_rg, diff_gb, diff_br) < threshold

    raise TypeError(f"Expected PIL Image or torch.Tensor, got {type(img)}")
