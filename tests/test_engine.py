"""Tests for StyleTransferEngine optimization loop and generator."""

import pytest
import torch

from neural_canvas.config import StyleTransferConfig
from neural_canvas.engine import StyleTransferEngine
from neural_canvas.losses import content_loss, gram_matrix, style_loss, total_variation_loss


def test_engine_generator_and_loss_decrease() -> None:
    # Small synthetic tensors for fast CPU execution
    content = torch.rand(1, 3, 64, 64)
    style = torch.rand(1, 3, 64, 64)

    config = StyleTransferConfig(
        steps=10,
        max_dim=64,
        style_max_dim=64,
        preview_every=2,
        learning_rate=0.05,
        seed=42,
    )

    engine = StyleTransferEngine(
        config=config,
        device=torch.device("cpu"),
        use_pretrained_weights=False,
    )
    engine.prepare(content, style)

    results = list(engine.run())

    # Expected yields: 2, 4, 6, 8, 10
    assert len(results) == 5
    steps = [r.step for r in results]
    assert steps == [2, 4, 6, 8, 10]

    # Verify loss decreases from first step to final step
    first_loss = results[0].total_loss
    last_loss = results[-1].total_loss
    assert last_loss < first_loss, (
        f"Expected total loss to decrease: first={first_loss:.4f}, last={last_loss:.4f}"
    )

    # Verify image properties
    final_img = results[-1].image
    assert final_img.shape == (1, 3, 64, 64)
    assert final_img.min().item() >= 0.0
    assert final_img.max().item() <= 1.0


def test_clamped_parameterization_loss_and_bounds() -> None:
    """Verify that clamped Adam parameterization decreases loss and stays strictly in [0, 1]."""
    content = torch.rand(1, 3, 64, 64)
    style = torch.rand(1, 3, 64, 64)

    config = StyleTransferConfig(
        steps=10,
        max_dim=64,
        style_max_dim=64,
        preview_every=2,
        learning_rate=0.01,
        parameterization="clamped",
        seed=42,
    )

    engine = StyleTransferEngine(
        config=config,
        device=torch.device("cpu"),
        use_pretrained_weights=False,
    )
    engine.prepare(content, style)

    results = list(engine.run())
    assert len(results) == 5

    # Verify loss decrease
    assert results[-1].total_loss < results[0].total_loss

    # Verify bounds in [0.0, 1.0] across all yields
    for r in results:
        assert r.image.min().item() >= 0.0
        assert r.image.max().item() <= 1.0


def test_style_blending() -> None:
    content = torch.rand(1, 3, 64, 64)
    style1 = torch.rand(1, 3, 64, 64)
    style2 = torch.rand(1, 3, 64, 64)

    config = StyleTransferConfig(steps=4, max_dim=64, preview_every=4, seed=42)
    engine = StyleTransferEngine(
        config=config, device=torch.device("cpu"), use_pretrained_weights=False
    )
    engine.prepare(content, [style1, style2], style_weights=[0.7, 0.3])

    results = list(engine.run())
    assert len(results) == 1
    assert results[0].step == 4


def test_lbfgs_optimizer_option() -> None:
    content = torch.rand(1, 3, 64, 64)
    style = torch.rand(1, 3, 64, 64)

    config = StyleTransferConfig(
        steps=3,
        max_dim=64,
        preview_every=3,
        optimizer="lbfgs",
        learning_rate=0.5,
        seed=42,
    )
    engine = StyleTransferEngine(
        config=config, device=torch.device("cpu"), use_pretrained_weights=False
    )
    engine.prepare(content, style)

    results = list(engine.run())
    assert len(results) == 1
    assert results[0].step == 3


def test_loss_and_gradient_balance_regression() -> None:
    # Regression test ensuring style gradient is not overwhelmed by TV gradient
    torch.manual_seed(42)
    content = torch.rand(1, 3, 64, 64)
    style = torch.rand(1, 3, 64, 64)

    # Use calibrated weights for regression check (style_weight=1e5, content_weight=10.0, tv_weight=1e-5)
    config = StyleTransferConfig(
        steps=5,
        max_dim=64,
        preview_every=1,
        content_weight=10.0,
        tv_weight=1e-5,
        learning_rate=0.005,
        eps=1e-8,
        seed=42,
    )
    engine = StyleTransferEngine(
        config=config,
        device=torch.device("cpu"),
        use_pretrained_weights=False,
    )
    engine.prepare(content, style)

    # 1. Check gradient norms of individual loss terms on initial image
    opt_image = content.clone().detach().requires_grad_(True)
    features = engine.extractor(opt_image, engine._all_layer_indices)
    current_grams = {name: gram_matrix(features[name]) for name in engine.config.style_layers}
    loss_s = style_loss(
        current_grams, engine.target_style_grams, style_weight=engine.config.style_weight
    )
    grad_s = torch.autograd.grad(loss_s, opt_image, retain_graph=True)[0]
    norm_s = torch.linalg.vector_norm(grad_s).item()

    loss_tv = total_variation_loss(opt_image) * engine.config.tv_weight
    grad_tv = torch.autograd.grad(loss_tv, opt_image, retain_graph=True)[0]
    norm_tv = torch.linalg.vector_norm(grad_tv).item()

    # The bug was that norm_s / norm_tv was ~ 3.4e-7. It must be >= 1e-3 (in fact >> 1.0)
    ratio = norm_s / (norm_tv + 1e-12)
    assert ratio >= 1e-3, f"Style gradient too weak relative to TV gradient: ratio={ratio:.2e}"

    # 2. Check that style loss decreases over optimization steps
    results = list(engine.run())
    first_style_loss = results[0].style_loss
    last_style_loss = results[-1].style_loss
    assert last_style_loss < first_style_loss, (
        f"Expected style loss to decrease: first={first_style_loss:.4f}, last={last_style_loss:.4f}"
    )


def test_content_gradient_not_negligible_regression() -> None:
    # Regression test ensuring content gradient is within a healthy ratio of style gradient
    torch.manual_seed(42)
    content = torch.rand(1, 3, 64, 64)
    style = torch.rand(1, 3, 64, 64)

    config = StyleTransferConfig(
        steps=5,
        max_dim=64,
        preview_every=1,
        learning_rate=0.005,
        eps=1e-8,
        seed=42,
    )
    engine = StyleTransferEngine(
        config=config,
        device=torch.device("cpu"),
        use_pretrained_weights=False,
    )
    engine.prepare(content, style)

    # After optimization steps, opt_image has moved, activating both content and style gradients
    results = list(engine.run())
    final_image = results[-1].image.clone().detach().requires_grad_(True)

    features = engine.extractor(final_image, engine._all_layer_indices)
    current_grams = {name: gram_matrix(features[name]) for name in engine.config.style_layers}

    loss_s = style_loss(
        current_grams, engine.target_style_grams, style_weight=engine.config.style_weight
    )
    grad_s = torch.autograd.grad(loss_s, final_image, retain_graph=True)[0]
    norm_s = torch.linalg.vector_norm(grad_s).item()

    loss_c = content_loss(
        features, engine.target_content_features, content_weight=engine.config.content_weight
    )
    grad_c = torch.autograd.grad(loss_c, final_image, retain_graph=True)[0]
    norm_c = torch.linalg.vector_norm(grad_c).item()

    # Content gradient must not be negligible relative to style gradient (uncalibrated was ~1e-6)
    ratio_cs = norm_c / (norm_s + 1e-12)
    assert ratio_cs >= 0.001, (
        f"Content gradient too weak relative to style gradient: ratio={ratio_cs:.4f}"
    )


def test_sigmoid_parameterization_range() -> None:
    """Verify that Sigmoid parameterization maps unconstrained logits to (0, 1) strictly."""
    torch.manual_seed(42)
    # Logits spanning extreme negative to extreme positive
    w = torch.tensor([-100.0, -10.0, -1.0, 0.0, 1.0, 10.0, 100.0], requires_grad=True)
    x = torch.sigmoid(w)

    assert torch.all(x >= 0.0)
    assert torch.all(x <= 1.0)

    # Verify derivative approaches 0 at bounds (saturation damping)
    loss = x.sum()
    loss.backward()
    grad = w.grad

    # Derivative of sigmoid is sigma * (1 - sigma)
    assert grad[0].item() < 1e-10  # at -100
    assert grad[-1].item() < 1e-10  # at +100
    assert pytest.approx(grad[3].item(), rel=1e-4) == 0.25  # at 0.0


def test_sigmoid_output_range_and_loss_decrease() -> None:
    """Verify that sigmoid parameterization stays strictly in [0, 1] and loss decreases."""
    device = torch.device("cpu")
    cfg = StyleTransferConfig(
        max_dim=64,
        steps=10,
        preview_every=1,
        learning_rate=0.05,
        parameterization="sigmoid",
        seed=42,
    )
    engine = StyleTransferEngine(config=cfg, device=device, use_pretrained_weights=False)

    # Synthetic dummy images for fast test
    dummy_content = torch.rand((1, 3, 64, 64), device=device)
    dummy_style = torch.rand((1, 3, 64, 64), device=device)

    engine.prepare(dummy_content, dummy_style)

    results = list(engine.run())
    assert len(results) > 0

    first_res = results[0]
    final_res = results[-1]

    # Output strictly within [0, 1]
    assert final_res.image.min().item() >= 0.0
    assert final_res.image.max().item() <= 1.0

    # Loss decreases
    assert final_res.total_loss < first_res.total_loss
