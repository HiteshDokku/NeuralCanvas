"""Device selection and memory management for Neural Canvas."""

from __future__ import annotations

import logging
from collections.abc import Generator
from contextlib import contextmanager

import torch

logger = logging.getLogger(__name__)

DEFAULT_MAX_DIM_GPU = 512
HARD_CAP_MAX_DIM = 768
DEFAULT_MAX_DIM_CPU = 384


def derive_max_dim_from_memory(device: torch.device | None = None) -> int:
    """Derive recommended maximum resolution cap based on free device memory.

    Measured peak VRAM: 768px requires ~1.6 GB, 512px requires ~0.8 GB, 384px requires ~0.5 GB.
    Returns conservative maximum dimensions (768, 512, or 384 px on GPU; 384 px on CPU).
    """
    if device is None:
        device = resolve_device("auto")
    if device.type == "cuda" and torch.cuda.is_available():
        idx = device.index if device.index is not None else 0
        try:
            free_bytes, _ = torch.cuda.mem_get_info(idx)
            free_gb = free_bytes / (1024**3)
            if free_gb >= 3.0:
                return 768
            elif free_gb >= 1.5:
                return 512
            else:
                return 384
        except Exception:
            return 512
    return DEFAULT_MAX_DIM_CPU


class NeuralCanvasOOMError(RuntimeError):
    """Raised when GPU memory is exhausted during style transfer."""


def get_default_device_name() -> str:
    """Determine the best available device: cuda > mps > cpu."""
    if torch.cuda.is_available():
        return "cuda"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def resolve_device(device_str: str | None = None) -> torch.device:
    """Resolve and configure a PyTorch device.

    Args:
        device_str: "auto", "cuda", "mps", "cpu", or specific cuda device e.g. "cuda:0".

    Returns:
        Configured torch.device instance.
    """
    if device_str is None or device_str == "auto":
        target = get_default_device_name()
    else:
        target = device_str.lower()

    if target.startswith("cuda"):
        if not torch.cuda.is_available():
            logger.warning("CUDA requested but not available. Falling back to CPU.")
            target = "cpu"
        else:
            torch.backends.cudnn.benchmark = True

    device = torch.device(target)
    logger.info("Neural Canvas running on device: %s", device)
    return device


def get_device_info(device: torch.device | None = None) -> dict[str, str | bool | int]:
    """Return diagnostic info about the active device."""
    if device is None:
        device = resolve_device("auto")

    info: dict[str, str | bool | int] = {
        "type": device.type,
        "name": str(device),
        "is_cuda": device.type == "cuda",
    }

    if device.type == "cuda" and torch.cuda.is_available():
        idx = device.index if device.index is not None else 0
        info["gpu_name"] = torch.cuda.get_device_name(idx)
        vram_bytes = torch.cuda.get_device_properties(idx).total_memory
        info["vram_gb"] = round(vram_bytes / (1024**3), 2)
        info["capability"] = ".".join(str(x) for x in torch.cuda.get_device_capability(idx))
    return info


@contextmanager
def handle_cuda_oom(current_dim: int | None = None) -> Generator[None, None, None]:
    """Context manager to trap CUDA OutOfMemoryError and provide helpful guidance."""
    try:
        yield
    except (torch.cuda.OutOfMemoryError, RuntimeError) as err:
        err_msg = str(err)
        if "out of memory" in err_msg.lower() or isinstance(err, torch.cuda.OutOfMemoryError):
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            dim_str = f" at resolution {current_dim}px" if current_dim else ""
            msg = (
                f"CUDA Out of Memory{dim_str}. "
                "GPU memory was exhausted. Suggestion: reduce `--max-dim` (e.g. 384 or 256), "
                "lower `--style-max-dim`, or switch to `--device cpu`."
            )
            logger.error(msg)
            raise NeuralCanvasOOMError(msg) from err
        raise
