"""Neural Canvas: Streamlit Web Application."""

from __future__ import annotations

import html
import io
import math
import re
import time
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
from PIL import Image

try:
    from app.ui_helpers import (
        build_config_from_ui_state,
        count_parameter_overrides,
        get_available_samples,
        load_theme_css,
        pil_to_base64_data_uri,
    )
except ModuleNotFoundError:
    from ui_helpers import (  # type: ignore
        build_config_from_ui_state,
        count_parameter_overrides,
        get_available_samples,
        load_theme_css,
        pil_to_base64_data_uri,
    )
from neural_canvas.config import (
    DEFAULT_SLIDER_POSITION,
    PRESETS,
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

# Configure page layout and metadata
st.set_page_config(
    page_title="Neural Canvas",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject custom scoped stylesheet
css_path = Path(__file__).resolve().parent / "static" / "theme.css"
theme_css = load_theme_css(css_path)
if theme_css:
    st.markdown(f"<style>{theme_css}</style>", unsafe_allow_html=True)

# Inject scoped panel resize script
js_path = Path(__file__).resolve().parent / "static" / "resize_panel.js"
if js_path.exists():
    components.html(f"<script>{js_path.read_text(encoding='utf-8')}</script>", height=1)


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
        "show_settings": False,
        "show_original": False,
        "run_status_msg": "Ready",
        "active_cw": None,
        "active_style_weight": 1e5,
        "active_tv_weight": 0.05,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_session_state()

# Device diagnostics
device = resolve_device("auto")
dev_info = get_device_info(device)
extractor = load_vgg_extractor(device.type)

if dev_info.get("is_cuda"):
    raw_name = dev_info.get("gpu_name", "")
    short_name = re.sub(r"^NVIDIA\s+(?:GeForce\s+)?", "", raw_name).strip()
    vram_val = dev_info.get("vram_gb")
    vram_str = f"{round(vram_val)} GB" if vram_val is not None else ""
    device_note = f"{short_name}, {vram_str}".strip(", ")
else:
    device_note = "Running on CPU (slower than GPU; draft recommended)"

# ----------------- LEFT RAIL (SIDEBAR) ----------------- #
with st.sidebar:
    with st.container(key="nc-rail-content"):
        # 1. Title & 1-line tagline with 16px bottom spacing
        st.markdown(
            '<div class="rail-title-block">'
            '<div class="font-title">Neural Canvas</div>'
            '<div class="font-tagline">Artistic neural style transfer</div>'
            "</div>",
            unsafe_allow_html=True,
        )

        # 2. Photo Selection
        st.markdown('<div class="sidebar-section-label">Photo</div>', unsafe_allow_html=True)
        sample_content_dir = Path("assets/samples")
        sample_options = ["Upload custom photo"]
        valid_samples = get_available_samples(sample_content_dir)
        sample_options.extend(valid_samples)

        content_choice = st.selectbox(
            "Content source",
            sample_options,
            key="select_content_source",
            label_visibility="collapsed",
        )
        content_img_pil = None
        uploaded_content = None

        if content_choice == "Upload custom photo":
            uploaded_content = st.file_uploader(
                "Upload content photo",
                type=["jpg", "jpeg", "png", "webp"],
                key="content_upload",
                label_visibility="collapsed",
            )
            if uploaded_content is not None:
                try:
                    content_img_pil = Image.open(uploaded_content).convert("RGB")
                except Exception as e:
                    st.markdown(
                        f'<div class="font-muted">Photo not readable. {e}</div>',
                        unsafe_allow_html=True,
                    )
        else:
            chosen_file = sample_content_dir / content_choice
            try:
                content_img_pil = Image.open(chosen_file).convert("RGB")
            except Exception as e:
                st.markdown(
                    f'<div class="font-muted">Error loading sample. {e}</div>',
                    unsafe_allow_html=True,
                )

        if content_img_pil is not None and is_grayscale_image(content_img_pil):
            st.markdown(
                '<div class="font-muted">Grayscale photo detected. Turn on Keep photo colors to retain monochrome tones.</div>',
                unsafe_allow_html=True,
            )

        # 3. Style Selection
        st.markdown('<div class="sidebar-section-label">Style</div>', unsafe_allow_html=True)
        registry: StyleRegistry = get_default_registry()
        presets = registry.list_presets()

        style_options = [p.name for p in presets] + ["Upload custom style"]
        selected_style_name = st.radio(
            "Style selection",
            style_options,
            index=0,
            label_visibility="collapsed",
        )

        style_img_pil = None
        selected_preset = None
        style_label = "Custom Style"
        uploaded_style = None

        if selected_style_name != "Upload custom style":
            for p in presets:
                if p.name == selected_style_name:
                    selected_preset = p
                    break

        if selected_preset is not None:
            style_img_pil = Image.open(selected_preset.image_path).convert("RGB")
            style_label = selected_preset.name
            rec_settings = getattr(selected_preset, "recommended_weights", {}) or {}
            best_for = getattr(selected_preset, "best_for", None)
            avoid_for = getattr(selected_preset, "avoid_for", None)
            guidance_notes = []
            if best_for:
                bf = best_for.strip().rstrip(".")
                guidance_notes.append(f"Best for: {bf}.")
            if avoid_for:
                af = avoid_for.strip().rstrip(".")
                guidance_notes.append(f"Avoid: {af}.")
        else:
            rec_settings = {}
            guidance_notes = []
            uploaded_style = st.file_uploader(
                "Upload style reference artwork",
                type=["jpg", "jpeg", "png", "webp"],
                key="style_upload",
                label_visibility="collapsed",
            )
            if uploaded_style is not None:
                try:
                    style_img_pil = Image.open(uploaded_style).convert("RGB")
                    style_label = uploaded_style.name
                except Exception as e:
                    st.markdown(
                        f'<div class="font-muted">Error opening style image. {e}</div>',
                        unsafe_allow_html=True,
                    )

        style_native_dim = max(style_img_pil.size) if style_img_pil else HARD_CAP_MAX_DIM
        if style_img_pil is not None and style_native_dim < 512:
            st.markdown(
                f'<div class="font-muted">Style image is {style_native_dim}px. Larger images give better results.</div>',
                unsafe_allow_html=True,
            )

        # 4. Quality (Draft/Balanced/High)
        st.markdown('<div class="sidebar-section-label">Quality</div>', unsafe_allow_html=True)
        quality_choice = st.segmented_control(
            "Quality preset",
            options=["Draft", "Balanced", "High"],
            default="Balanced" if dev_info.get("is_cuda") else "Draft",
            label_visibility="collapsed",
        )
        quality_preset = (quality_choice or "Balanced").lower()
        base_config = PRESETS.get(quality_preset, PRESETS["balanced"])

        base_cw = (
            rec_settings.get("content_weight", base_config.content_weight)
            if rec_settings
            else base_config.content_weight
        )

        # 5. Style Strength
        style_strength = st.slider(
            "Style strength",
            min_value=1,
            max_value=10,
            value=DEFAULT_SLIDER_POSITION,
            step=1,
            help="Controls artistic intensity. Position 1 retains high photo detail; position 10 produces strong painterly texture.",
        )

        # 6. Portrait Mode
        portrait_mode = st.checkbox(
            "Portrait mode",
            value=False,
            help="Prioritizes facial feature recognizability on portraits.",
        )

        if portrait_mode and selected_preset is not None and selected_preset.id == "the_kiss":
            st.markdown(
                '<div class="font-muted">The Kiss ornamental gold patterns can cover facial features. Composition VII or The Starry Night is recommended for portraits.</div>',
                unsafe_allow_html=True,
            )

        # 7. Keep Photo Colors
        color_preserve = st.checkbox(
            "Keep photo colors",
            value=False,
            help="The photo original colors are kept; the style changes only brightness and texture.",
        )

        derived_cw = calculate_slider_content_weight(
            slider_val=style_strength,
            base_cw=base_cw,
            portrait_mode=portrait_mode,
            default_slider_val=DEFAULT_SLIDER_POSITION,
        )

    # 8. Device Line above button & Pinned Stylize / Cancel Button
    with st.container(key="nc-rail-dock"):
        st.markdown(
            f'<div class="sidebar-device-line" title="{html.escape(device_note)}">{html.escape(device_note)}</div>',
            unsafe_allow_html=True,
        )
        action_btn_slot = st.empty()
        if st.session_state.get("is_running", False) or st.session_state.get("btn_cancel"):
            if action_btn_slot.button("Cancel", key="btn_cancel", use_container_width=True):
                st.session_state["cancel_requested"] = True
                st.session_state["is_running"] = False
                if st.session_state.get("latest_result_image") is not None:
                    st.session_state["run_status_msg"] = (
                        "Cancelled at step 50/150. Partial result kept."
                    )
                else:
                    st.session_state["run_status_msg"] = "Cancelled."
        else:
            start_run = action_btn_slot.button(
                "Stylize",
                type="primary",
                key="btn_stylize",
                use_container_width=True,
            )


# ----------------- WORKBENCH CONTAINER LAYOUT ----------------- #
# Explicit top-level containers scoped to .st-key-nc-center and .st-key-nc-settings
center_container = st.container(key="nc-center")
settings_container = (
    st.container(key="nc-settings") if st.session_state.get("show_settings", False) else None
)

# Sync hyperparameter defaults when quality preset changes
if st.session_state.get("prev_quality_preset") != quality_preset:
    st.session_state["prev_quality_preset"] = quality_preset
    st.session_state["cfg_steps"] = base_config.steps
    st.session_state["cfg_lr"] = base_config.learning_rate
    st.session_state["cfg_max_dim"] = base_config.max_dim
    st.session_state["cfg_param"] = base_config.parameterization

if "cfg_steps" not in st.session_state:
    st.session_state["cfg_steps"] = base_config.steps
if "cfg_lr" not in st.session_state:
    st.session_state["cfg_lr"] = base_config.learning_rate
if "cfg_max_dim" not in st.session_state:
    st.session_state["cfg_max_dim"] = base_config.max_dim
if "cfg_param" not in st.session_state:
    st.session_state["cfg_param"] = base_config.parameterization

# Right Panel Rendering
if settings_container is not None:
    with settings_container:
        st.markdown('<div class="group-mono-header">Balance</div>', unsafe_allow_html=True)
        use_raw_weights = st.checkbox("Raw loss weights", value=False)

        if use_raw_weights:
            s_weight_log = st.slider(
                "Style weight (log10)", min_value=3.0, max_value=7.0, value=5.0, step=0.2
            )
            style_weight = 10**s_weight_log

            c_weight_log = st.slider(
                "Content weight (log10)",
                min_value=-1.0,
                max_value=4.0,
                value=float(f"{math.log10(derived_cw):.1f}") if derived_cw > 0 else 2.0,
                step=0.1,
            )
            content_weight = 10**c_weight_log

            tv_weight_log = st.slider(
                "Total variation weight (log10)",
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

        st.markdown(
            f'<div class="font-mono">Style: {style_weight:.1e} | Content: {content_weight:.1f} | TV: {tv_weight:.3f}</div>',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="group-mono-header">Optimizer</div>', unsafe_allow_html=True)
        steps_val = st.slider(
            "Optimization steps",
            min_value=20,
            max_value=2000,
            value=st.session_state["cfg_steps"],
            step=20,
            key="slider_steps",
        )
        st.session_state["cfg_steps"] = steps_val

        lr_val = st.number_input(
            "Learning rate",
            min_value=0.001,
            max_value=0.1,
            value=st.session_state["cfg_lr"],
            step=0.005,
            key="input_lr",
        )
        st.session_state["cfg_lr"] = lr_val

        param_val = st.selectbox(
            "Image parameterization",
            options=["sigmoid", "clamped"],
            index=0 if st.session_state["cfg_param"] == "sigmoid" else 1,
            key="select_param",
        )
        st.session_state["cfg_param"] = param_val

        schedule_note = (
            f"{base_config.lr_schedule.capitalize()} decay to {int(base_config.lr_min_ratio * 100)}%"
            if base_config.lr_schedule == "cosine"
            else "Constant"
        )
        st.markdown(
            f'<div class="font-mono">Schedule: {schedule_note}</div>',
            unsafe_allow_html=True,
        )
        preview_interval = st.slider(
            "Preview interval (steps)",
            min_value=10,
            max_value=100,
            value=base_config.preview_every,
            step=5,
            key="slider_preview_interval",
        )

        st.markdown('<div class="group-mono-header">Image</div>', unsafe_allow_html=True)
        max_dim_val = st.slider(
            "Max resolution (px)",
            min_value=128,
            max_value=HARD_CAP_MAX_DIM,
            value=st.session_state["cfg_max_dim"],
            step=32,
            key="slider_max_dim",
        )
        st.session_state["cfg_max_dim"] = max_dim_val

        rec_scale = float(rec_settings.get("style_scale_ratio", 1.0)) if rec_settings else 1.0
        scale_ratio = st.select_slider(
            "Style pattern scale",
            options=[0.5, 0.75, 1.0, 1.5, 2.0],
            value=rec_scale if rec_scale in [0.5, 0.75, 1.0, 1.5, 2.0] else 1.0,
            key="select_style_scale",
        )
        init_mode = st.selectbox(
            "Canvas initialization", ["content", "noise"], index=0, key="select_canvas_init"
        )
        seed_val = st.number_input(
            "Random seed (0 for random)",
            min_value=0,
            max_value=999999,
            value=42,
            key="input_seed",
        )

        content_layer_choice = st.selectbox(
            "Content representation layer",
            options=[
                "conv4_2 (crisp structure)",
                "conv5_2 (abstract silhouette)",
            ],
            index=0 if (not rec_settings or rec_settings.get("content_layer") == "conv4_2") else 1,
            key="select_content_layer",
        )
        chosen_content_layer = ("conv5_2",) if "conv5_2" in content_layer_choice else ("conv4_2",)

        # Build active configuration
        overrides = {
            "style_weight": style_weight,
            "content_weight": content_weight,
            "tv_weight": tv_weight,
            "steps": steps_val,
            "max_dim": max_dim_val,
            "style_scale_ratio": scale_ratio,
            "content_layers": chosen_content_layer,
            "learning_rate": lr_val,
            "parameterization": param_val,
            "init": init_mode,
            "seed": int(seed_val) if seed_val > 0 else None,
            "preview_every": preview_interval,
            "lr_schedule": base_config.lr_schedule,
            "lr_min_ratio": base_config.lr_min_ratio,
        }
        active_config = build_config_from_ui_state(
            quality_preset=quality_preset,
            rec_settings=rec_settings,
            derived_cw=derived_cw,
            color_preserve=color_preserve,
            overrides=overrides,
        )

        # Footer diagnostics and reset
        n_diff = count_parameter_overrides(active_config, base_config, rec_settings)
        st.markdown(
            f'<div class="font-mono">{n_diff} changed | Mode: {param_val} (preset default: {base_config.parameterization})</div>',
            unsafe_allow_html=True,
        )
        if st.button("Reset to preset", key="btn_reset_preset"):
            st.session_state["cfg_steps"] = base_config.steps
            st.session_state["cfg_lr"] = base_config.learning_rate
            st.session_state["cfg_max_dim"] = base_config.max_dim
            st.session_state["cfg_param"] = base_config.parameterization
            st.rerun()
else:
    # Default active configuration when settings panel is closed
    overrides = {
        "steps": st.session_state.get("cfg_steps", base_config.steps),
        "max_dim": st.session_state.get("cfg_max_dim", base_config.max_dim),
        "learning_rate": st.session_state.get("cfg_lr", base_config.learning_rate),
        "parameterization": st.session_state.get("cfg_param", base_config.parameterization),
        "lr_schedule": base_config.lr_schedule,
        "lr_min_ratio": base_config.lr_min_ratio,
        "preview_every": base_config.preview_every,
    }
    active_config = build_config_from_ui_state(
        quality_preset=quality_preset,
        rec_settings=rec_settings,
        derived_cw=derived_cw,
        color_preserve=color_preserve,
        overrides=overrides,
    )


# ----------------- CENTER RESULT PLATE ----------------- #
with center_container:
    # Header row: Title on left, Right-aligned cluster [status readout][Settings button]
    col_hdr_left, col_hdr_right = st.columns([1, 2])

    with col_hdr_left:
        st.markdown('<div class="result-header-title">Result</div>', unsafe_allow_html=True)

    with col_hdr_right:
        col_status, col_btn = st.columns([3, 1])
        with col_status:
            status_slot = st.empty()
            status_slot.markdown(
                f'<div class="header-status-text">{st.session_state.get("run_status_msg", "Ready")}</div>',
                unsafe_allow_html=True,
            )
        with col_btn:
            if st.button("Settings", key="btn_toggle_settings", use_container_width=True):
                st.session_state["show_settings"] = not st.session_state.get("show_settings", False)
                st.rerun()

    # 3px Accent Progress Track
    progress_slot = st.empty()

    # Result Viewport Slot
    result_slot = st.empty()

    if st.session_state["latest_result_image"] is not None:
        if st.session_state.get("show_original") and content_img_pil is not None:
            c_b64 = pil_to_base64_data_uri(content_img_pil)
            result_slot.markdown(
                f'<div class="result-plate"><img src="{c_b64}" class="result-image-contain" alt="Original photo" /></div>',
                unsafe_allow_html=True,
            )
        else:
            r_b64 = pil_to_base64_data_uri(st.session_state["latest_result_image"])
            result_slot.markdown(
                f'<div class="result-plate"><img src="{r_b64}" class="result-image-contain" alt="Stylized result" /></div>',
                unsafe_allow_html=True,
            )
    else:
        result_slot.markdown(
            """
            <div class="result-plate">
                <div class="font-muted">Select a photo and style, then click Stylize to generate output.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Active settings mono caption below plate
    seed_display = active_config.seed if active_config.seed is not None else "random"
    st.markdown(
        f'<div class="font-mono" style="margin-top: 2px; margin-bottom: 2px;">Style weight {active_config.style_weight:.1e} | Content weight {active_config.content_weight:.1f} | Smoothness {active_config.tv_weight:.3f} | Seed {seed_display} | Layer {active_config.content_layers[0]}</div>',
        unsafe_allow_html=True,
    )

    # Bottom strip: Reference previews, downloads, and history
    strip_left, strip_right = st.columns([3.8, 1.2])

    with strip_left:
        ref_html_parts = ['<div class="ref-previews-container">']

        # Photo reference tile (160x120)
        if content_img_pil is not None:
            c_w, c_h = content_img_pil.size
            c_name = (
                content_choice
                if content_choice != "Upload custom photo"
                else (uploaded_content.name if uploaded_content else "Custom photo")
            )
            c_b64 = pil_to_base64_data_uri(content_img_pil)
            ref_html_parts.append(
                f'<div class="ref-tile-group">'
                f'<div class="ref-tile-label">Photo</div>'
                f'<div class="ref-tile-box"><img src="{c_b64}" alt="Photo" /></div>'
                f'<div class="ref-tile-caption" title="{html.escape(c_name)}, {c_w} x {c_h}">{html.escape(c_name)}, {c_w} x {c_h}</div>'
                f"</div>"
            )

        # Style reference tile (160x120) with Best for / Avoid note
        if style_img_pil is not None:
            s_w, s_h = style_img_pil.size
            s_b64 = pil_to_base64_data_uri(style_img_pil)
            notes_text = " ".join(guidance_notes) if guidance_notes else ""
            notes_html = (
                f'<div class="ref-tile-guidance">{html.escape(notes_text)}</div>'
                if notes_text
                else ""
            )
            ref_html_parts.append(
                f'<div class="ref-tile-group">'
                f'<div class="ref-tile-label">Style</div>'
                f'<div class="ref-tile-box"><img src="{s_b64}" alt="Style" /></div>'
                f'<div class="ref-tile-caption" title="{html.escape(style_label)}, {s_w} x {s_h}">{html.escape(style_label)}, {s_w} x {s_h}</div>'
                f"{notes_html}"
                f"</div>"
            )

        # Hairline divider & History thumbnails (64x48)
        if st.session_state.get("run_history"):
            ref_html_parts.append('<div class="ref-divider"></div>')
            ref_html_parts.append('<div class="history-strip-group">')
            ref_html_parts.append('<div class="ref-tile-label">History</div>')
            ref_html_parts.append('<div class="history-tiles-row">')
            for hist in st.session_state["run_history"]:
                h_b64 = pil_to_base64_data_uri(hist["image"])
                ref_html_parts.append(
                    f'<div class="history-thumb-box" title="{hist["style"]} ({hist["time"]})">'
                    f'<img src="{h_b64}" alt="{hist["style"]}" />'
                    f"</div>"
                )
            ref_html_parts.append("</div></div>")

        ref_html_parts.append("</div>")
        st.markdown("".join(ref_html_parts), unsafe_allow_html=True)

    with strip_right:
        if st.session_state["latest_result_image"] is not None:
            show_orig = st.checkbox("Show original", key="toggle_show_original")
            st.session_state["show_original"] = show_orig

            buf = io.BytesIO()
            st.session_state["latest_result_image"].save(buf, format="PNG")
            st.download_button(
                label="Download image",
                data=buf.getvalue(),
                file_name=f"neural_canvas_{int(time.time())}.png",
                mime="image/png",
                use_container_width=True,
            )

            if st.session_state.get("latest_config_json"):
                st.download_button(
                    label="Download parameters",
                    data=st.session_state["latest_config_json"],
                    file_name="neural_canvas_config.json",
                    mime="application/json",
                    use_container_width=True,
                )


# ----------------- MAIN EXECUTION LOOP ----------------- #
if "start_run" in locals() and start_run:
    if content_img_pil is None or style_img_pil is None:
        status_slot.markdown(
            '<div class="header-status-text">Provide both a photo and a style reference before running.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.session_state["is_running"] = True
        st.session_state["loss_history"] = []

        # Immediately update the action button in the sidebar to Cancel
        if action_btn_slot.button("Cancel", key="btn_cancel", use_container_width=True):
            st.session_state["cancel_requested"] = True

        # PREP PHASE FEEDBACK: Immediately update plate, progress line, and status
        status_slot.markdown(
            '<div class="header-status-text">Preparing feature representations...</div>',
            unsafe_allow_html=True,
        )
        progress_slot.markdown(
            '<div class="progress-track-3px"><div class="progress-bar-indeterminate"></div></div>',
            unsafe_allow_html=True,
        )
        content_b64 = pil_to_base64_data_uri(content_img_pil)
        result_slot.markdown(
            f'<div class="result-plate"><img src="{content_b64}" class="result-image-contain" style="opacity: 0.35;" alt="Preparing" /></div>',
            unsafe_allow_html=True,
        )

        try:
            engine = StyleTransferEngine(config=active_config, device=device)

            # Prepare inputs
            engine.prepare(content_img_pil, style_img_pil)

            start_time = time.time()
            total_steps = active_config.steps
            was_cancelled = False

            for step_res in engine.run():
                if st.session_state.get("cancel_requested", False):
                    was_cancelled = True
                    st.session_state["run_status_msg"] = (
                        f"Cancelled at step {step_res.step}/{total_steps}. Partial result kept."
                    )
                    status_slot.markdown(
                        f'<div class="header-status-text">{st.session_state["run_status_msg"]}</div>',
                        unsafe_allow_html=True,
                    )
                    break

                elapsed = time.time() - start_time
                steps_done = step_res.step
                rate = steps_done / elapsed if elapsed > 0 else 0
                eta = (total_steps - steps_done) / rate if rate > 0 else 0
                pct = int(100 * steps_done / total_steps)

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

                # Update live preview and determinate 3px accent line
                progress_slot.markdown(
                    f'<div class="progress-track-3px"><div class="progress-bar-determinate" style="width: {pct}%;"></div></div>',
                    unsafe_allow_html=True,
                )
                curr_b64 = pil_to_base64_data_uri(curr_pil)
                result_slot.markdown(
                    f'<div class="result-plate"><img src="{curr_b64}" class="result-image-contain" alt="Live preview" /></div>',
                    unsafe_allow_html=True,
                )

                elapsed_str = f"{int(elapsed // 60):02d}:{int(elapsed % 60):02d}"
                eta_str = f"{int(eta // 60):02d}:{int(eta % 60):02d}"
                live_status = (
                    f"step {steps_done} / {total_steps}   {elapsed_str} ETA {eta_str} | "
                    f"Style: {step_res.style_loss:.2e} | "
                    f"Content: {step_res.content_loss:.2e} | "
                    f"TV: {step_res.tv_loss:.2e}"
                )
                st.session_state["run_status_msg"] = live_status
                status_slot.markdown(
                    f'<div class="header-status-text">{live_status}</div>',
                    unsafe_allow_html=True,
                )

            total_elapsed = time.time() - start_time
            if was_cancelled:
                st.session_state["cancel_requested"] = False
                progress_slot.empty()
            else:
                if st.session_state["latest_result_image"] is not None:
                    w, h = st.session_state["latest_result_image"].size
                    final_msg = f"Done in {total_elapsed:.1f} s, {w} x {h}, {total_steps} steps"
                    st.session_state["run_status_msg"] = final_msg
                    status_slot.markdown(
                        f'<div class="header-status-text">{final_msg}</div>',
                        unsafe_allow_html=True,
                    )
                    progress_slot.empty()

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
                    st.session_state["run_history"] = st.session_state["run_history"][:5]

        except NeuralCanvasOOMError:
            st.session_state["run_status_msg"] = "Out of GPU memory. Lower the quality or max size."
            status_slot.markdown(
                f'<div class="header-status-text">{st.session_state["run_status_msg"]}</div>',
                unsafe_allow_html=True,
            )
            progress_slot.empty()
        except Exception as err:
            st.session_state["run_status_msg"] = f"Error: {err}"
            status_slot.markdown(
                f'<div class="header-status-text">{st.session_state["run_status_msg"]}</div>',
                unsafe_allow_html=True,
            )
            progress_slot.empty()
        finally:
            st.session_state["is_running"] = False
