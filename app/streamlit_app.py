"""Neural Canvas: Streamlit Web Application."""

from __future__ import annotations

import io
import math
import time
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image

from neural_canvas.config import (
    DEFAULT_SLIDER_POSITION,
    PRESETS,
    StyleTransferConfig,
    calculate_slider_content_weight,
)
from neural_canvas.device import (
    HARD_CAP_MAX_DIM,
    NeuralCanvasOOMError,
    get_device_info,
    resolve_device,
)
from neural_canvas.engine import StyleTransferEngine
from neural_canvas.image_io import is_grayscale_image, tensor_to_pil
from neural_canvas.model import get_extractor
from neural_canvas.styles import StyleRegistry, get_default_registry

# Configure page
st.set_page_config(
    page_title="Neural Canvas | Neural Style Transfer",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown(
    """
    <style>
    .main-title {
        font-size: 2.4rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        margin-bottom: 0.2rem;
    }
    .subtitle {
        color: #94A3B8;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #1E293B;
        border-radius: 8px;
        padding: 12px;
        border: 1px solid #334155;
    }
    .history-card {
        border-radius: 6px;
        overflow: hidden;
        border: 1px solid #334155;
        margin-bottom: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner=False)
def load_vgg_extractor(device_str: str):
    """Cache the VGG feature extractor across runs to avoid redundant reloads."""
    dev = resolve_device(device_str)
    return get_extractor(dev, weights=True)


def init_session_state() -> None:
    """Initialize persistent session variables."""
    defaults = {
        "latest_result_image": None,
        "latest_config_json": None,
        "loss_history": [],
        "run_history": [],
        "is_running": False,
        "cancel_requested": False,
        "content_source": None,
        "style_source": None,
        "style_name": "Custom Style",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_session_state()

# Device diagnostics
device = resolve_device("auto")
dev_info = get_device_info(device)
extractor = load_vgg_extractor(device.type)

# App Header
st.markdown('<div class="main-title">🎨 Neural Canvas</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Artistic neural style transfer powered by PyTorch, VGG19, and hardware-accelerated Gram matrix optimization.</div>',
    unsafe_allow_html=True,
)

# Hardware status banner
if dev_info.get("is_cuda"):
    st.success(
        f"🚀 **GPU Hardware Acceleration Active:** {dev_info['gpu_name']} "
        f"({dev_info.get('vram_gb')} GB VRAM, sm_{dev_info.get('capability')})"
    )
else:
    st.warning(
        "⚠️ **Running on CPU:** Optimization on CPU is fully functional but significantly slower than GPU. "
        "We strongly recommend the **Draft preset** (256px, 150 steps) for responsive results."
    )

# ----------------- SIDEBAR ----------------- #
with st.sidebar:
    st.header("⚙️ Configuration")

    # Content Image Section
    st.subheader("1. Content Image")
    sample_content_dir = Path("assets/samples")
    sample_options = ["Upload Custom..."]
    sample_files = []
    if sample_content_dir.exists():
        valid_sample_files = []
        for f in sorted(sample_content_dir.iterdir()):
            if f.is_file() and f.suffix.lower() in [".jpg", ".png", ".jpeg", ".webp"]:
                try:
                    with Image.open(f) as img:
                        w, h = img.size
                        if w >= 64 and h >= 64:
                            valid_sample_files.append(f)
                except Exception:
                    continue
        sample_options.extend([f.name for f in valid_sample_files])

    content_choice = st.selectbox("Content Source", sample_options)
    content_img_pil = None

    if content_choice == "Upload Custom...":
        uploaded_content = st.file_uploader(
            "Upload content photo", type=["jpg", "jpeg", "png", "webp"], key="content_upload"
        )
        if uploaded_content is not None:
            try:
                content_img_pil = Image.open(uploaded_content).convert("RGB")
            except Exception as e:
                st.error(f"Error opening image: {e}")
    else:
        chosen_file = sample_content_dir / content_choice
        try:
            content_img_pil = Image.open(chosen_file).convert("RGB")
        except Exception as e:
            st.error(f"Error loading sample: {e}")

    if content_img_pil is not None and is_grayscale_image(content_img_pil):
        st.info(
            "ℹ️ **Grayscale Photo Detected:** With **Preserve Original Colors** ON, the output retains monochrome tones while transferring brushwork texture. Turn it OFF to colorize your photo with the artwork's color palette."
        )

    # Style Image Section
    st.subheader("2. Style Reference")
    style_mode = st.radio("Style Selection", ["Preset Artworks", "Upload Custom"], horizontal=True)

    style_img_pil = None
    style_label = "Custom Style"
    registry: StyleRegistry = get_default_registry()
    presets = registry.list_presets()

    if style_mode == "Preset Artworks" and presets:
        preset_options = {f"{p.name} ({p.artist})": p.id for p in presets}
        selected_label = st.selectbox("Choose Masterwork", list(preset_options.keys()))
        selected_id = preset_options[selected_label]
        selected_preset = registry.get_preset(selected_id)
        style_img_pil = Image.open(selected_preset.image_path).convert("RGB")
        style_label = selected_preset.name
        if Path(selected_preset.thumbnail_path).exists():
            st.image(
                selected_preset.thumbnail_path,
                caption=f"{selected_preset.name} ({selected_preset.year})",
                use_container_width=True,
            )
    else:
        uploaded_style = st.file_uploader(
            "Upload style reference artwork",
            type=["jpg", "jpeg", "png", "webp"],
            key="style_upload",
        )
        if uploaded_style is not None:
            try:
                style_img_pil = Image.open(uploaded_style).convert("RGB")
                style_label = uploaded_style.name
            except Exception as e:
                st.error(f"Error opening style image: {e}")

    # Quality Presets & Style Tuning
    st.subheader("3. Optimization & Style Tuning")

    # Check for per-preset recommended settings
    rec_settings = (
        getattr(selected_preset, "recommended_weights", None)
        if "selected_preset" in locals() and selected_preset
        else None
    )
    if "selected_preset" in locals() and selected_preset:
        best_for = getattr(selected_preset, "best_for", None)
        avoid_for = getattr(selected_preset, "avoid_for", None)
        if best_for or avoid_for:
            with st.expander(f"ℹ️ Style Guidance: {selected_preset.name}", expanded=True):
                if best_for:
                    st.markdown(f"**Best for:** {best_for}")
                if avoid_for:
                    st.markdown(f"**Avoid / Caution:** {avoid_for}")
                    if "portrait" in avoid_for.lower() or "face" in avoid_for.lower():
                        st.info(
                            "💡 **Portrait Guidance:** If your photo has faces, enable **Portrait / faces**."
                        )
    if rec_settings:
        st.info(
            f"✨ Preset tuning loaded for **{selected_preset.name}**: Content Weight `{rec_settings.get('content_weight', 80.0):.0f}`, Layer `{rec_settings.get('content_layer', 'conv4_2')}`"
        )

    quality_preset = st.select_slider(
        "Quality Preset",
        options=["draft", "balanced", "high", "custom"],
        value="balanced" if dev_info.get("is_cuda") else "draft",
        format_func=lambda x: {
            "draft": "Draft (256px, 150 steps - quick preview)",
            "balanced": "Balanced (384px, 400 steps)",
            "high": "High (512px, 1000 steps)",
            "custom": "Custom Tuning...",
        }[x],
    )

    base_config = PRESETS.get(quality_preset, PRESETS["balanced"])

    base_cw = (
        rec_settings.get("content_weight", base_config.content_weight)
        if rec_settings
        else base_config.content_weight
    )

    # Intuitive primary control: Style Strength (maps to content/style balance)
    style_strength = st.slider(
        "🎨 Style Strength",
        min_value=1,
        max_value=10,
        value=DEFAULT_SLIDER_POSITION,
        step=1,
        help="Controls artistic intensity on a log scale. Position 1 (Subtle) sets content weight to 5000 for high photo detail; Position 10 (Intense) sets content weight to 90 for strong painterly texture. The default position preserves the selected style's exact calibrated recommendation.",
    )

    # Primary Control: Portrait / faces checkbox
    portrait_mode = st.checkbox(
        "👤 Portrait / faces",
        value=False,
        help="Prioritizes facial feature recognizability on portraits (applies high content weighting for styles like Composition VII).",
    )

    derived_cw = calculate_slider_content_weight(
        slider_val=style_strength,
        base_cw=base_cw,
        portrait_mode=portrait_mode,
        default_slider_val=DEFAULT_SLIDER_POSITION,
    )

    if portrait_mode:
        selected_id = (
            getattr(selected_preset, "id", "")
            if "selected_preset" in locals() and selected_preset
            else ""
        )
        if selected_id == "the_kiss":
            st.warning(
                "⚠️ **The Kiss & Portraits:** Gustav Klimt's ornamental gold foil patterns can cover facial features, mouths, and hands with dense decorative blocks even at high content weights. For portrait photos, we recommend **Composition VII**, **The Starry Night**, or **The Great Wave** instead."
            )

    # Style scale slider relative to canvas dimensions (resolution-invariant pattern scale)
    style_native_dim = max(style_img_pil.size) if style_img_pil else HARD_CAP_MAX_DIM
    if style_img_pil is not None and style_native_dim < 512:
        st.warning(
            f"⚠️ This style image is only {style_native_dim}px; larger source images (≥ 512px) give better results."
        )

    rec_scale_ratio = float(rec_settings.get("style_scale_ratio", 1.0)) if rec_settings else 1.0
    style_scale_ratio = st.select_slider(
        "🖌️ Style Pattern Scale",
        options=[0.5, 0.75, 1.0, 1.5, 2.0],
        value=rec_scale_ratio if rec_scale_ratio in [0.5, 0.75, 1.0, 1.5, 2.0] else 1.0,
        format_func=lambda x: (
            f"{x}x ({'Micro' if x <= 0.5 else ('Fine' if x <= 0.75 else ('Standard' if x == 1.0 else ('Broad' if x == 1.5 else 'Macro')))})"
        ),
        help="Scale of style brushstrokes and textures relative to canvas dimensions (1.0x matches canvas; 0.5x yields fine micro-textures; 2.0x yields broad macro-strokes). Clamped to native image resolution.",
    )

    # Primary Control: Preserve Original Colors
    color_preserve = st.checkbox(
        "🎨 Preserve Original Colors",
        value=False,
        help="The photo's original colors are kept; the style changes only brightness and texture. Grayscale inputs give grayscale output.",
    )

    # Advanced Settings Expander
    with st.expander("🛠️ Advanced Hyperparameters", expanded=(quality_preset == "custom")):
        use_raw_weights = st.checkbox(
            "Override with Raw Loss Weights", value=(quality_preset == "custom")
        )

        content_layer_choice = st.selectbox(
            "Content Representation Layer",
            options=[
                "conv4_2 (Crisp Structure, Gatys et al. default)",
                "conv5_2 (Abstract Silhouette, TF Tutorial)",
            ],
            index=0 if (not rec_settings or rec_settings.get("content_layer") == "conv4_2") else 1,
            help="conv4_2 preserves sharp contours; conv5_2 yields abstract silhouettes.",
        )
        if "conv5_2" in content_layer_choice:
            selected_content_layer = ("conv5_2",)
        else:
            selected_content_layer = ("conv4_2",)

        steps = st.slider(
            "Optimization Steps", min_value=20, max_value=2000, value=base_config.steps, step=20
        )
        max_dim = st.slider(
            "Max Resolution (px)",
            min_value=128,
            max_value=HARD_CAP_MAX_DIM,
            value=base_config.max_dim,
            step=32,
        )

        if use_raw_weights:
            style_weight_log = st.slider(
                "Style Weight (log10)", min_value=3.0, max_value=7.0, value=5.0, step=0.2
            )
            style_weight = 10**style_weight_log

            content_weight_log = st.slider(
                "Content Weight (log10)",
                min_value=-1.0,
                max_value=4.0,
                value=float(f"{math.log10(derived_cw):.1f}") if derived_cw > 0 else 2.0,
                step=0.1,
            )
            content_weight = 10**content_weight_log

            tv_weight_log = st.slider(
                "Total Variation Weight (log10)",
                min_value=-4.0,
                max_value=0.0,
                value=-1.3,
                step=0.1,
            )
            tv_weight = 10**tv_weight_log
        else:
            style_weight = rec_settings.get("style_weight", 1e5) if rec_settings else 1e5
            content_weight = derived_cw
            tv_weight = rec_settings.get("tv_weight", 0.05) if rec_settings else 0.05

        st.caption(
            f"Active Weights: Style=`{style_weight:.1e}` | Content=`{content_weight:.1f}` | TV=`{tv_weight:.3f}` | Layers=`{'+'.join(selected_content_layer)}`"
        )

        lr = st.number_input(
            "Learning Rate",
            min_value=0.001,
            max_value=0.1,
            value=base_config.learning_rate,
            step=0.005,
        )
        init_mode = st.selectbox("Canvas Initialization", ["content", "noise"], index=0)
        param_choice = st.selectbox(
            "Image Parameterization",
            options=["sigmoid", "clamped"],
            index=0 if base_config.parameterization == "sigmoid" else 1,
            help="Sigmoid is smoother at low resolution and updates very dark and very bright pixels more slowly. High uses clamped Adam to stylize dark and bright regions faster.",
        )
        seed_val = st.number_input(
            "Random Seed (0 for random)", min_value=0, max_value=999999, value=42
        )
        preview_interval = st.slider(
            "Preview Interval (steps)", min_value=10, max_value=100, value=25, step=5
        )

    st.caption(
        f"⚙️ Active Mode: **{param_choice}** (Preset Default: `{base_config.parameterization}`)"
    )

    if st.button("🔄 Reset to Preset Defaults"):
        st.rerun()

    active_config = StyleTransferConfig(
        style_weight=style_weight,
        content_weight=content_weight,
        tv_weight=tv_weight,
        steps=steps,
        max_dim=max_dim,
        style_max_dim=None,
        style_scale_ratio=style_scale_ratio,
        content_layers=selected_content_layer,
        color_preserve=color_preserve,
        learning_rate=lr,
        parameterization=param_choice,
        multi_crop_style=bool(rec_settings.get("multi_crop_style", False))
        if rec_settings
        else False,
        style_crop_exclude=rec_settings.get("style_crop_exclude") if rec_settings else None,
        style_layer_weights=rec_settings.get("style_layer_weights") if rec_settings else None,
        init=init_mode,
        seed=int(seed_val) if seed_val > 0 else None,
        preview_every=preview_interval,
    )


# ----------------- MAIN PANEL ----------------- #
col_content, col_style, col_result = st.columns([1, 1, 1.2])

with col_content:
    st.markdown("### 📷 Content Image")
    if content_img_pil is not None:
        st.image(
            content_img_pil,
            use_container_width=True,
            caption=f"Original: {content_img_pil.size[0]}x{content_img_pil.size[1]}px",
        )
    else:
        st.info("Select or upload a content image in the sidebar.")

with col_style:
    st.markdown("### 🎨 Style Reference")
    if style_img_pil is not None:
        st.image(
            style_img_pil,
            use_container_width=True,
            caption=f"{style_label}: {style_img_pil.size[0]}x{style_img_pil.size[1]}px",
        )
    else:
        st.info("Select or upload a style artwork in the sidebar.")

with col_result:
    st.markdown("### ✨ Stylized Output")
    result_display_slot = st.empty()
    progress_bar = st.empty()
    status_text = st.empty()

    if st.session_state["latest_result_image"] is not None:
        result_display_slot.image(st.session_state["latest_result_image"], use_container_width=True)
    else:
        result_display_slot.markdown(
            """
            <div style="border: 2px dashed #334155; border-radius: 8px; padding: 60px 20px; text-align: center; color: #64748B;">
                Click <b>Run Style Transfer</b> below to generate the output canvas.
            </div>
            """,
            unsafe_allow_html=True,
        )

# Execution Controls
st.markdown("---")
btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 4])
start_run = btn_col1.button("🚀 Run Style Transfer", type="primary", use_container_width=True)
cancel_run = btn_col2.button("⏹️ Cancel Run", use_container_width=True)

if cancel_run:
    st.session_state["cancel_requested"] = True

# Main Execution Loop
if start_run:
    if content_img_pil is None or style_img_pil is None:
        st.error("Please supply both a content image and a style reference before running.")
    else:
        st.session_state["cancel_requested"] = False
        st.session_state["loss_history"] = []

        try:
            engine = StyleTransferEngine(config=active_config, device=device)
            status_text.text("Preparing feature representations and Gram targets...")

            # Prepare inputs
            engine.prepare(content_img_pil, style_img_pil)

            start_time = time.time()
            total_steps = active_config.steps

            for step_res in engine.run():
                # Check cancellation
                if st.session_state.get("cancel_requested"):
                    status_text.warning("Optimization cancelled by user. Partial result preserved.")
                    break

                elapsed = time.time() - start_time
                steps_done = step_res.step
                rate = steps_done / elapsed if elapsed > 0 else 0
                eta = (total_steps - steps_done) / rate if rate > 0 else 0

                # Convert current tensor to PIL and update session state
                curr_pil = tensor_to_pil(step_res.image)
                st.session_state["latest_result_image"] = curr_pil
                st.session_state["latest_config_json"] = active_config.to_json()
                st.session_state["loss_history"].append(
                    {
                        "step": step_res.step,
                        "total_loss": step_res.total_loss,
                        "style_loss": step_res.style_loss,
                        "content_loss": step_res.content_loss,
                        "tv_loss": step_res.tv_loss,
                    }
                )

                # Live updates in UI
                result_display_slot.image(curr_pil, use_container_width=True)
                progress_bar.progress(steps_done / total_steps)
                status_text.markdown(
                    f"**Step {steps_done}/{total_steps}** ({100 * steps_done / total_steps:.0f}%) | "
                    f"**Style:** `{step_res.style_loss:.2e}` | "
                    f"**Content:** `{step_res.content_loss:.2e}` | "
                    f"**TV:** `{step_res.tv_loss:.2e}` | "
                    f"**Total:** `{step_res.total_loss:.2e}` | "
                    f"`{rate:.1f} it/s` (ETA {eta:.1f}s)"
                )

            total_elapsed = time.time() - start_time
            if not st.session_state.get("cancel_requested"):
                status_text.success(f"✅ Stylization complete in {total_elapsed:.1f} seconds!")
                progress_bar.empty()

                # Add to history
                if st.session_state["latest_result_image"] is not None:
                    st.session_state["run_history"].insert(
                        0,
                        {
                            "image": st.session_state["latest_result_image"],
                            "style": style_label,
                            "time": time.strftime("%H:%M:%S"),
                            "steps": active_config.steps,
                            "config": active_config.to_json(),
                        },
                    )
                    # Keep last 5
                    st.session_state["run_history"] = st.session_state["run_history"][:5]

        except NeuralCanvasOOMError as oom:
            st.error(f"❌ {oom}")
        except Exception as err:
            st.error(f"❌ Unexpected Error: {err}")

# Post-Run Analysis & Downloads
if st.session_state["latest_result_image"] is not None:
    st.markdown("### 📊 Run Analysis & Downloads")
    tab_inspect, tab_loss, tab_history = st.tabs(
        ["🖼️ Compare & Export", "📈 Loss Progression", "🕒 History Strip"]
    )

    with tab_inspect:
        d_col1, d_col2 = st.columns([1, 1])

        with d_col1:
            # Download Image
            buf = io.BytesIO()
            st.session_state["latest_result_image"].save(buf, format="PNG")
            st.download_button(
                label="💾 Download Stylized Image (PNG)",
                data=buf.getvalue(),
                file_name=f"neural_canvas_{int(time.time())}.png",
                mime="image/png",
                use_container_width=True,
            )

        with d_col2:
            # Download Params
            st.download_button(
                label="📄 Download Hyperparameters (JSON)",
                data=st.session_state.get("latest_config_json", "{}"),
                file_name="neural_canvas_config.json",
                mime="application/json",
                use_container_width=True,
            )

    with tab_loss:
        if st.session_state["loss_history"]:
            df_loss = pd.DataFrame(st.session_state["loss_history"])
            st.line_chart(df_loss.set_index("step")[["total_loss", "style_loss", "content_loss"]])
        else:
            st.info("Loss metrics will plot during and after an active run.")

    with tab_history:
        if st.session_state["run_history"]:
            h_cols = st.columns(min(len(st.session_state["run_history"]), 5))
            for i, hist in enumerate(st.session_state["run_history"]):
                with h_cols[i]:
                    st.image(
                        hist["image"],
                        caption=f"{hist['style']} ({hist['time']})",
                        use_container_width=True,
                    )
        else:
            st.info("Previous creations will appear here.")

# How it Works Section
st.markdown("---")
with st.expander("📖 How Neural Canvas Works (Gatys Algorithm Deep Dive)"):
    st.markdown(
        r"""
        Neural Canvas implements the neural style transfer algorithm formulated by Gatys, Ecker, and Bethge (2015).

        ### 1. Feature Representation with Pretrained VGG19
        Rather than optimizing network weights, the network weights are frozen and the pixel values of the output image $\vec{x}$ are directly optimized via gradient descent.

        - **Content Representation:** Activations of deeper layers capture semantic structures while discarding high-frequency textures:
          $$\mathcal{L}_{\text{content}}(\vec{p}, \vec{x}, l) = \frac{1}{2} \sum_{i,j} (F^l_{ij} - P^l_{ij})^2$$

        - **Style Representation:** Texture and color correlations across channels are captured by the **Gram matrix** $G^l$:
          $$G^l_{cd} = \frac{1}{H \times W} \sum_{i,j} F^l_{ijc} F^l_{ijd}$$
          Style loss computes MSE between target Gram matrices $A^l$ and generated Gram matrices $G^l$:
          $$\mathcal{L}_{\text{style}}(\vec{a}, \vec{x}) = \sum_{l} w_l \frac{1}{N_l} \sum_{c,d} (G^l_{cd} - A^l_{cd})^2$$

        - **Total Variation Regularization:** Suppresses high-frequency pixel noise to ensure smooth, natural brushwork:
          $$\mathcal{L}_{\text{TV}}(\vec{x}) = \sum_{i,j} |x_{i+1,j} - x_{i,j}| + |x_{i,j+1} - x_{i,j}|$$

        - **Total Objective:**
          $$\mathcal{L}_{\text{total}} = \alpha \mathcal{L}_{\text{content}} + \beta \mathcal{L}_{\text{style}} + \gamma \mathcal{L}_{\text{TV}}$$
        """
    )
