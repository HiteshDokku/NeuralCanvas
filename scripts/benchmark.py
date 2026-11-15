"""Benchmark script for Neural Canvas.

Measures seconds per 100 steps across 256, 384, 512, and 768 px resolutions
on GPU and CPU, measuring real elapsed times and formatting a markdown table.
"""

from __future__ import annotations

import argparse
import time

import torch

from neural_canvas.config import StyleTransferConfig
from neural_canvas.device import resolve_device
from neural_canvas.engine import StyleTransferEngine


def benchmark_run(
    resolution: int,
    device: torch.device,
    steps: int = 100,
    warmup_steps: int = 5,
) -> dict[str, str | float]:
    """Run benchmark at specified resolution and device."""
    # Create synthetic tensors
    content = torch.rand(1, 3, resolution, resolution, device=device)
    style = torch.rand(1, 3, resolution, resolution, device=device)

    # Warmup
    if warmup_steps > 0:
        warmup_cfg = StyleTransferConfig(
            steps=warmup_steps, max_dim=resolution, preview_every=warmup_steps
        )
        warmup_engine = StyleTransferEngine(
            config=warmup_cfg, device=device, use_pretrained_weights=False
        )
        warmup_engine.prepare(content, style)
        for _ in warmup_engine.run():
            pass
        if device.type == "cuda":
            torch.cuda.synchronize()

    # Reset peak memory tracking if CUDA
    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats(device)
        torch.cuda.synchronize()

    config = StyleTransferConfig(
        steps=steps,
        max_dim=resolution,
        style_max_dim=resolution,
        preview_every=steps,
        learning_rate=0.02,
        seed=42,
    )
    engine = StyleTransferEngine(config=config, device=device, use_pretrained_weights=False)
    engine.prepare(content, style)

    start_time = time.perf_counter()
    for _ in engine.run():
        pass

    if device.type == "cuda":
        torch.cuda.synchronize()
    elapsed = time.perf_counter() - start_time

    peak_vram_mb = 0.0
    if device.type == "cuda":
        peak_vram_mb = torch.cuda.max_memory_allocated(device) / (1024 * 1024)

    ms_per_step = (elapsed / steps) * 1000.0
    return {
        "resolution": resolution,
        "device": device.type.upper(),
        "elapsed_100_steps": elapsed * (100.0 / steps),
        "ms_per_step": ms_per_step,
        "peak_vram_mb": peak_vram_mb,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Neural Canvas Benchmark Runner")
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        choices=["auto", "cuda", "cpu", "all"],
        help="Device to benchmark (default: auto, or 'all' to test both CUDA and CPU).",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=100,
        help="Number of timed steps (default: 100).",
    )
    parser.add_argument(
        "--resolutions",
        nargs="+",
        type=int,
        default=[256, 384, 512, 768],
        help="List of resolutions to benchmark.",
    )
    args = parser.parse_args()

    devices_to_test: list[torch.device] = []
    if args.device == "all":
        if torch.cuda.is_available():
            devices_to_test.append(torch.device("cuda:0"))
        devices_to_test.append(torch.device("cpu"))
    else:
        devices_to_test.append(resolve_device(args.device))

    results = []
    for dev in devices_to_test:
        print(f"\n--- Benchmarking on {dev} ---")
        for res in args.resolutions:
            print(f"Testing {res}x{res} ({args.steps} steps)...", end=" ", flush=True)
            try:
                res_data = benchmark_run(res, dev, steps=args.steps)
                results.append(res_data)
                print(
                    f"Done: {res_data['elapsed_100_steps']:.2f}s per 100 steps "
                    f"({res_data['ms_per_step']:.1f} ms/step, "
                    f"VRAM: {res_data['peak_vram_mb']:.1f} MB)"
                )
            except torch.cuda.OutOfMemoryError:
                print("CUDA Out of Memory!")
                torch.cuda.empty_cache()
                results.append(
                    {
                        "resolution": res,
                        "device": dev.type.upper(),
                        "elapsed_100_steps": "OOM",
                        "ms_per_step": "OOM",
                        "peak_vram_mb": "OOM",
                    }
                )
            except Exception as e:
                print(f"Error: {e}")
                results.append(
                    {
                        "resolution": res,
                        "device": dev.type.upper(),
                        "elapsed_100_steps": f"Error: {e}",
                        "ms_per_step": "N/A",
                        "peak_vram_mb": "N/A",
                    }
                )

    # Print markdown table
    print("\n### Benchmark Results\n")
    print("| Resolution | Device | Seconds / 100 steps | ms / step | Peak VRAM (MB) |")
    print("| :--- | :--- | :--- | :--- | :--- |")
    for r in results:
        sec = (
            f"{r['elapsed_100_steps']:.2f}s"
            if isinstance(r["elapsed_100_steps"], float)
            else str(r["elapsed_100_steps"])
        )
        ms = (
            f"{r['ms_per_step']:.1f} ms"
            if isinstance(r["ms_per_step"], float)
            else str(r["ms_per_step"])
        )
        vram = (
            f"{r['peak_vram_mb']:.1f} MB"
            if isinstance(r["peak_vram_mb"], float)
            else str(r["peak_vram_mb"])
        )
        print(f"| {r['resolution']}x{r['resolution']} | {r['device']} | {sec} | {ms} | {vram} |")


if __name__ == "__main__":
    main()
