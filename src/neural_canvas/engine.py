"""Core style transfer execution engine."""

from __future__ import annotations

import logging
import random
from collections.abc import Generator, Sequence
from dataclasses import dataclass

import numpy as np
import torch

from .config import StyleTransferConfig
from .device import handle_cuda_oom, resolve_device
from .image_io import ImageSource, load_image, transfer_color
from .losses import content_loss, gram_matrix, style_loss, total_variation_loss
from .model import get_extractor, resolve_layer_indices

logger = logging.getLogger(__name__)


@dataclass
class StepResult:
    """Result yielded at intermediate and final optimization steps."""

    step: int
    image: torch.Tensor
    total_loss: float
    style_loss: float
    content_loss: float
    tv_loss: float


class StyleTransferEngine:
    """Encapsulates the neural style transfer optimization loop."""

    def __init__(
        self,
        config: StyleTransferConfig | None = None,
        device: torch.device | str | None = None,
        use_pretrained_weights: bool = True,
    ) -> None:
        self.config = config or StyleTransferConfig()
        if isinstance(device, str) or device is None:
            self.device = resolve_device(device)
        else:
            self.device = device

        self.use_pretrained_weights = use_pretrained_weights
        self.extractor = get_extractor(self.device, weights=self.use_pretrained_weights)

        # Precomputed targets
        self.content_tensor: torch.Tensor | None = None
        self.style_tensor: torch.Tensor | None = None
        self.target_content_features: dict[str, torch.Tensor] = {}
        self.target_style_grams: dict[str, torch.Tensor] = {}

        # Layer index mappings
        self._content_layer_indices = resolve_layer_indices(self.config.content_layers)
        self._style_layer_indices = resolve_layer_indices(self.config.style_layers)
        self._all_layer_indices = {
            **self._content_layer_indices,
            **self._style_layer_indices,
        }

    def prepare(
        self,
        content: torch.Tensor | ImageSource,
        style: torch.Tensor | ImageSource | Sequence[torch.Tensor | ImageSource],
        style_weights: Sequence[float] | None = None,
    ) -> None:
        """Precompute target content features and target style Gram matrices."""
        with handle_cuda_oom(self.config.max_dim):
            # Load and transfer content image
            if isinstance(content, torch.Tensor):
                self.content_tensor = content.to(self.device)
            else:
                self.content_tensor = load_image(
                    content, max_dim=self.config.max_dim, device=self.device
                )

            with torch.no_grad():
                # Handle single or multiple style blending
                if isinstance(style, (list, tuple)):
                    all_grams_list = []
                    for s in style:
                        st = (
                            s.to(self.device)
                            if isinstance(s, torch.Tensor)
                            else load_image(
                                s,
                                max_dim=self.config.effective_style_max_dim,
                                device=self.device,
                            )
                        )
                        feat = self.extractor(st, self._style_layer_indices)
                        all_grams_list.append({name: gram_matrix(f) for name, f in feat.items()})

                    weights = style_weights or [1.0 / len(all_grams_list)] * len(all_grams_list)
                    w_sum = sum(weights)
                    weights = [w / w_sum for w in weights]
                    self.target_style_grams = {}
                    for name in self.config.style_layers:
                        self.target_style_grams[name] = sum(
                            w * g[name] for w, g in zip(weights, all_grams_list, strict=False)
                        )
                else:
                    if isinstance(style, torch.Tensor):
                        self.style_tensor = style.to(self.device)
                    else:
                        self.style_tensor = load_image(
                            style,
                            max_dim=self.config.effective_style_max_dim,
                            device=self.device,
                        )

                    if self.config.multi_crop_style:
                        # Multi-crop style Gram averaging (averages num_style_crops random crops)
                        _, _, sh, sw = self.style_tensor.shape
                        accum_grams: dict[str, torch.Tensor] = {
                            name: torch.tensor(0.0, device=self.device)
                            for name in self.config.style_layers
                        }
                        if self.config.seed is not None:
                            torch.manual_seed(self.config.seed)

                        exclude = self.config.style_crop_exclude
                        if exclude is not None:
                            # Standard [x_min, y_min, x_max, y_max] format
                            ex1, ey1, ex2, ey2 = exclude
                            # Define partition zones strictly disjoint from the exclusion rectangle
                            candidate_zones = [
                                (0.0, 0.0, 1.0, float(ex1)),  # Left: X in [0, ex1]
                                (0.0, float(ex2), 1.0, 1.0),  # Right: X in [ex2, 1]
                                (0.0, 0.0, float(ey1), 1.0),  # Top: Y in [0, ey1]
                                (float(ey2), 0.0, 1.0, 1.0),  # Bottom: Y in [ey2, 1]
                            ]
                            # Filter zones with adequate dimensions to hold crops
                            valid_zones = [
                                z
                                for z in candidate_zones
                                if (z[2] - z[0]) >= 0.08 and (z[3] - z[1]) >= 0.08
                            ]
                            if not valid_zones:
                                valid_zones = candidate_zones
                            zone_areas = [(z[2] - z[0]) * (z[3] - z[1]) for z in valid_zones]
                            zone_weights = torch.tensor(zone_areas, dtype=torch.float32)

                            for _ in range(self.config.num_style_crops):
                                z_idx = int(torch.multinomial(zone_weights, 1).item())
                                zy1, zx1, zy2, zx2 = valid_zones[z_idx]
                                z_h = zy2 - zy1
                                z_w = zx2 - zx1

                                scale_h = float(torch.empty(1).uniform_(0.35, 0.85).item())
                                scale_w = float(torch.empty(1).uniform_(0.35, 0.85).item())
                                ch = max(
                                    32, min(int(round(z_h * sh)), int(round(z_h * sh * scale_h)))
                                )
                                cw = max(
                                    32, min(int(round(z_w * sw)), int(round(z_w * sw * scale_w)))
                                )

                                zone_top = int(round(zy1 * sh))
                                zone_left = int(round(zx1 * sw))
                                max_top_offset = max(0, int(round(z_h * sh)) - ch)
                                max_left_offset = max(0, int(round(z_w * sw)) - cw)

                                off_top = (
                                    int(torch.randint(0, max_top_offset + 1, (1,)).item())
                                    if max_top_offset > 0
                                    else 0
                                )
                                off_left = (
                                    int(torch.randint(0, max_left_offset + 1, (1,)).item())
                                    if max_left_offset > 0
                                    else 0
                                )

                                top = min(sh - ch, zone_top + off_top)
                                left = min(sw - cw, zone_left + off_left)
                                crop = self.style_tensor[:, :, top : top + ch, left : left + cw]
                                feat = self.extractor(crop, self._style_layer_indices)
                                for name in self.config.style_layers:
                                    accum_grams[name] = accum_grams[name] + gram_matrix(feat[name])
                        else:
                            for _ in range(self.config.num_style_crops):
                                scale = float(torch.empty(1).uniform_(0.50, 0.85).item())
                                ch = max(32, int(round(sh * scale)))
                                cw = max(32, int(round(sw * scale)))
                                top = (
                                    int(torch.randint(0, sh - ch + 1, (1,)).item())
                                    if sh > ch
                                    else 0
                                )
                                left = (
                                    int(torch.randint(0, sw - cw + 1, (1,)).item())
                                    if sw > cw
                                    else 0
                                )
                                crop = self.style_tensor[:, :, top : top + ch, left : left + cw]
                                feat = self.extractor(crop, self._style_layer_indices)
                                for name in self.config.style_layers:
                                    accum_grams[name] = accum_grams[name] + gram_matrix(feat[name])

                        self.target_style_grams = {
                            name: accum_grams[name] / float(self.config.num_style_crops)
                            for name in self.config.style_layers
                        }
                    else:
                        style_features = self.extractor(
                            self.style_tensor, self._style_layer_indices
                        )
                        self.target_style_grams = {
                            name: gram_matrix(feat) for name, feat in style_features.items()
                        }

                # Extract content targets
                self.target_content_features = self.extractor(
                    self.content_tensor, self._content_layer_indices
                )

    def run(self) -> Generator[StepResult, None, None]:
        """Execute the optimization loop, yielding StepResult periodically.

        Yields:
            StepResult every preview_every steps and on the final step.
        """
        if self.content_tensor is None or not self.target_content_features:
            raise RuntimeError(
                "Engine has not been prepared. Call `prepare(content, style)` first."
            )

        # Seed per-run reproducibility if configured
        if self.config.seed is not None:
            random.seed(self.config.seed)
            np.random.seed(self.config.seed)
            torch.manual_seed(self.config.seed)
            if self.device.type == "cuda":
                torch.cuda.manual_seed_all(self.config.seed)

        with handle_cuda_oom(self.config.max_dim):
            # Initialize image/logits to optimize
            if self.config.init == "content":
                init_base = self.content_tensor.clone()
            elif self.config.init == "noise":
                init_base = torch.rand_like(self.content_tensor)
            else:
                raise ValueError(f"Unknown init mode: {self.config.init}")

            if self.config.parameterization == "sigmoid":
                c_min, c_max = getattr(self.config, "sigmoid_init_clamp", (1e-4, 1.0 - 1e-4))
                base_safe = init_base.clamp(c_min, c_max)
                opt_var = (
                    torch.log(base_safe / (1.0 - base_safe)).detach().clone().requires_grad_(True)
                )
            else:
                opt_var = init_base.detach().clone().requires_grad_(True)

            if self.config.optimizer == "lbfgs":
                optimizer: torch.optim.Optimizer = torch.optim.LBFGS(
                    [opt_var],
                    lr=self.config.learning_rate,
                    max_iter=1,
                    history_size=20,
                )
                scheduler = None
            else:
                optimizer = torch.optim.Adam(
                    [opt_var],
                    lr=self.config.learning_rate,
                    betas=self.config.betas,
                    eps=self.config.eps,
                )
                if self.config.lr_schedule == "cosine":
                    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
                        optimizer,
                        T_max=self.config.steps,
                        eta_min=self.config.learning_rate * self.config.lr_min_ratio,
                    )
                else:
                    scheduler = None

            try:
                for step in range(1, self.config.steps + 1):
                    loss_metrics: dict[str, float] = {}

                    def closure(metrics_dict: dict[str, float] = loss_metrics) -> torch.Tensor:
                        optimizer.zero_grad(set_to_none=True)
                        if self.config.parameterization == "sigmoid":
                            opt_image = torch.sigmoid(opt_var)
                        else:
                            opt_image = opt_var

                        current_features = self.extractor(opt_image, self._all_layer_indices)

                        current_grams = {
                            name: gram_matrix(current_features[name])
                            for name in self.config.style_layers
                        }

                        curr_area = float(opt_image.shape[2] * opt_image.shape[3])
                        ref_area = 384.0 * 384.0

                        # Content scaling to preserve content/style balance across resolutions:
                        # In multi-layer VGG19, ||g_c|| / ||g_s|| scales as ~ Area^0.73
                        content_area_factor = (ref_area / curr_area) ** 0.75
                        eff_content_weight = self.config.content_weight * content_area_factor

                        loss_s = style_loss(
                            current_grams,
                            self.target_style_grams,
                            style_weight=self.config.style_weight,
                            layer_weights=self.config.style_layer_weights,
                        )
                        loss_c = content_loss(
                            current_features,
                            self.target_content_features,
                            content_weight=eff_content_weight,
                        )

                        # Resolution-invariant TV regularization:
                        # Bounded at min area 30,000 to safely accommodate wide 256x144 canvases (area=36,864)
                        # without artificial clipping, while preventing synthetic unit-test tensors (< 256px) from exploding
                        tv_area_factor = (ref_area / max(curr_area, 30000.0)) ** 1.0
                        loss_tv = (
                            total_variation_loss(opt_image)
                            * (self.config.tv_weight * tv_area_factor)
                            if self.config.tv_weight > 0
                            else torch.tensor(0.0, device=self.device)
                        )

                        total = loss_s + loss_c + loss_tv
                        total.backward()

                        metrics_dict["total"] = float(total.item())
                        metrics_dict["style"] = float(loss_s.item())
                        metrics_dict["content"] = float(loss_c.item())
                        metrics_dict["tv"] = float(loss_tv.item())
                        return total

                    optimizer.step(closure)
                    if scheduler is not None:
                        scheduler.step()

                    if self.config.parameterization == "clamped":
                        # Clamp to [0, 1] range after each step under torch.no_grad()
                        with torch.no_grad():
                            opt_var.clamp_(0.0, 1.0)

                    # Check yield conditions: every preview_every steps or final step
                    is_preview = step % self.config.preview_every == 0
                    is_final = step == self.config.steps

                    if is_preview or is_final:
                        if self.config.parameterization == "sigmoid":
                            with torch.no_grad():
                                out_tensor = torch.sigmoid(opt_var).detach().clone().clamp(0.0, 1.0)
                        else:
                            out_tensor = opt_var.detach().clone()

                        if self.config.color_preserve and self.content_tensor is not None:
                            out_tensor = transfer_color(self.content_tensor, out_tensor)

                        result = StepResult(
                            step=step,
                            image=out_tensor,
                            total_loss=loss_metrics.get("total", 0.0),
                            style_loss=loss_metrics.get("style", 0.0),
                            content_loss=loss_metrics.get("content", 0.0),
                            tv_loss=loss_metrics.get("tv", 0.0),
                        )
                        yield result

            finally:
                # Cleanup if early stopped
                if self.device.type == "cuda":
                    torch.cuda.empty_cache()
