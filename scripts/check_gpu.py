"""GPU verification script for Neural Canvas.

Checks CUDA availability, GPU device specifications, architecture support,
and executes test conv2d and matmul operations on the GPU.
"""

from __future__ import annotations

import sys

import torch


def main() -> None:
    print(f"PyTorch version: {torch.__version__}")
    print(f"PyTorch CUDA version: {torch.version.cuda}")
    cuda_available = torch.cuda.is_available()
    print(f"CUDA available: {cuda_available}")

    if not cuda_available:
        print("ERROR: CUDA is not available to PyTorch.", file=sys.stderr)
        sys.exit(1)

    device_count = torch.cuda.device_count()
    device_name = torch.cuda.get_device_name(0)
    device_capability = torch.cuda.get_device_capability(0)
    arch_list = torch.cuda.get_arch_list()

    print(f"Device count: {device_count}")
    print(f"Device name: {device_name}")
    print(f"Device capability: {device_capability}")
    print(f"CUDA arch list: {', '.join(arch_list)}")

    # Check for Blackwell (sm_120 or compute_120) or capability >= (12, 0)
    is_sm120 = any("120" in arch for arch in arch_list)
    if is_sm120:
        print("Architecture check: sm_120 / compute_120 detected in arch list.")
    else:
        print(f"Note: sm_120 not in arch_list ({arch_list}), capability: {device_capability}")

    # Run small test tensors on GPU
    device = torch.device("cuda:0")
    print("Testing tensor allocation on GPU...")
    x = torch.randn(1, 3, 64, 64, device=device)
    conv = torch.nn.Conv2d(3, 16, kernel_size=3, padding=1).to(device)
    y = conv(x)
    print(f"Conv2d test passed: output shape {tuple(y.shape)}")

    a = torch.randn(64, 64, device=device)
    b = torch.randn(64, 64, device=device)
    c = torch.matmul(a, b)
    print(f"Matmul test passed: output shape {tuple(c.shape)}")

    # Verify synchronization
    torch.cuda.synchronize()
    print("GPU OK")


if __name__ == "__main__":
    main()
