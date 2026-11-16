"""Tests for UI hygiene, forbidden characters, font assets, and AppTest workflows."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import tomllib
from streamlit.testing.v1 import AppTest

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

EMOJI_PATTERN = re.compile(
    "["
    "\U0001f600-\U0001f64f"  # emoticons
    "\U0001f300-\U0001f5ff"  # symbols & pictographs
    "\U0001f680-\U0001f6ff"  # transport & map
    "\U0001f700-\U0001f77f"  # alchemical
    "\U0001f780-\U0001f7ff"  # geometric
    "\U0001f800-\U0001f8ff"  # supplemental arrows
    "\U0001f900-\U0001f9ff"  # supplemental symbols
    "\U0001fa00-\U0001fa6f"  # chess
    "\U0001fa70-\U0001faff"  # symbols & pictographs ext-a
    "\u2600-\u26ff"  # misc symbols
    "\u2700-\u27bf"  # dingbats
    "]+",
    flags=re.UNICODE,
)


def test_ui_forbidden_characters() -> None:
    """Scan app/*.py, app/static/theme.css and .streamlit/config.toml for forbidden characters."""
    repo_root = Path(__file__).resolve().parent.parent
    app_dir = repo_root / "app"
    css_file = app_dir / "static" / "theme.css"
    toml_file = repo_root / ".streamlit" / "config.toml"

    files_to_check = list(app_dir.glob("*.py"))
    if css_file.exists():
        files_to_check.append(css_file)
    if toml_file.exists():
        files_to_check.append(toml_file)

    violations: list[str] = []

    for file_path in files_to_check:
        content = file_path.read_text(encoding="utf-8")
        rel_path = file_path.relative_to(repo_root)

        # Check line by line for em dash and emoji
        for line_num, line in enumerate(content.splitlines(), start=1):
            if "\u2014" in line:
                violations.append(f"{rel_path}:{line_num} - Contains forbidden em dash (U+2014)")
            if EMOJI_PATTERN.search(line):
                violations.append(f"{rel_path}:{line_num} - Contains forbidden emoji characters")

        # In Python files, scan string literals for exclamation marks
        if file_path.suffix == ".py":
            tree = ast.parse(content, filename=str(file_path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    val = node.value
                    if "!" in val:
                        # Exclude markdown image syntax, css !important, or != operators
                        cleaned = re.sub(r"!\[.*?\]\(.*?\)", "", val)
                        cleaned = cleaned.replace("!important", "")
                        if "!" in cleaned:
                            violations.append(
                                f"{rel_path}:{node.lineno} - Contains exclamation mark in string literal: {val[:40]!r}"
                            )

    assert not violations, "Forbidden characters detected:\n" + "\n".join(violations)


def test_font_files_and_licenses() -> None:
    """Verify that every font file referenced in config.toml exists with its license file."""
    repo_root = Path(__file__).resolve().parent.parent
    config_path = repo_root / ".streamlit" / "config.toml"
    assert config_path.exists(), "config.toml not found"

    with open(config_path, "rb") as f:
        cfg = tomllib.load(f)

    theme_cfg = cfg.get("theme", {})
    font_faces = theme_cfg.get("fontFaces", [])
    assert font_faces, "No fontFaces defined in .streamlit/config.toml"

    checked_families: set[str] = set()

    for face in font_faces:
        url = face.get("url")
        family = face.get("family")
        assert url, f"fontFace missing url: {face}"
        assert family, f"fontFace missing family: {face}"

        font_path = repo_root / url
        assert font_path.exists(), f"Font file does not exist: {font_path}"
        assert font_path.stat().st_size > 0, f"Font file is empty: {font_path}"

        if family not in checked_families:
            checked_families.add(family)
            # Verify license file exists for this family
            font_dir = font_path.parent
            license_files = (
                list(font_dir.glob(f"*{family.replace(' ', '')}*OFL*.txt"))
                + list(font_dir.glob(f"*{family.replace(' ', '')}*license*.txt"))
                + list(font_dir.glob("*OFL*.txt"))
            )
            assert license_files, f"No license file found for font family {family} in {font_dir}"


def test_apptest_first_render() -> None:
    """Verify Streamlit app renders initially without unhandled exceptions."""
    repo_root = Path(__file__).resolve().parent.parent
    app_script = str(repo_root / "app" / "streamlit_app.py")
    at = AppTest.from_file(app_script, default_timeout=60)
    at.run(timeout=60)

    exceptions = [e.value for e in at.exception]
    assert not exceptions, f"App threw exceptions on initial render: {exceptions}"
    assert at.sidebar, "Sidebar failed to render"


def test_apptest_settings_toggle() -> None:
    """Verify opening and closing the right Settings panel via toggle button."""
    repo_root = Path(__file__).resolve().parent.parent
    app_script = str(repo_root / "app" / "streamlit_app.py")
    at = AppTest.from_file(app_script, default_timeout=60)
    at.run(timeout=60)

    assert not at.session_state.get("show_settings", False)

    # Click Settings button to open panel
    at.button(key="btn_toggle_settings").click().run(timeout=60)
    assert at.session_state.get("show_settings") is True

    # Click Settings button to close panel
    at.button(key="btn_toggle_settings").click().run(timeout=60)
    assert at.session_state.get("show_settings") is False


def test_apptest_error_lines() -> None:
    """Verify missing input validation line appears when clicking Stylize with no photo."""
    repo_root = Path(__file__).resolve().parent.parent
    app_script = str(repo_root / "app" / "streamlit_app.py")
    at = AppTest.from_file(app_script, default_timeout=60)
    at.run(timeout=60)

    # By default, content source is Upload custom photo and no photo is uploaded
    at.sidebar.button(key="btn_stylize").click().run(timeout=60)
    assert not at.exception


def test_apptest_draft_run() -> None:
    """Verify running a minimal Draft stylization via AppTest."""
    repo_root = Path(__file__).resolve().parent.parent
    app_script = str(repo_root / "app" / "streamlit_app.py")
    at = AppTest.from_file(app_script, default_timeout=60)
    at.run(timeout=60)

    at.sidebar.selectbox[0].set_value("dog.jpg").run(timeout=60)
    at.sidebar.segmented_control[0].set_value("Draft").run(timeout=60)
    at.session_state["cfg_steps"] = 2
    at.sidebar.button(key="btn_stylize").click().run(timeout=60)

    assert not at.exception
    assert at.session_state.get("latest_result_image") is not None
    assert "Done in" in at.session_state.get("run_status_msg", "")


def test_apptest_cancelled_state() -> None:
    """Verify cancellation preserves partial output and displays cancelled status."""
    repo_root = Path(__file__).resolve().parent.parent
    app_script = str(repo_root / "app" / "streamlit_app.py")
    at = AppTest.from_file(app_script, default_timeout=60)
    at.run(timeout=60)

    at.sidebar.selectbox[0].set_value("dog.jpg").run(timeout=60)
    at.sidebar.segmented_control[0].set_value("Draft").run(timeout=60)
    at.session_state["cfg_steps"] = 10
    at.session_state["cancel_requested"] = True
    at.sidebar.button(key="btn_stylize").click().run(timeout=60)

    assert not at.exception
    status_msg = at.session_state.get("run_status_msg", "")
    assert "Cancelled at step" in status_msg or "Partial result kept" in status_msg


def test_ui_config_matches_preset() -> None:
    """Verify that build_config_from_ui_state matches presets field-by-field."""
    from app.ui_helpers import build_config_from_ui_state
    from neural_canvas.config import PRESETS
    from neural_canvas.styles import get_default_registry

    # 1. Check Draft, Balanced, and High match base presets field-by-field on clean run
    for preset_name, base_preset in PRESETS.items():
        cfg = build_config_from_ui_state(preset_name)
        assert cfg.lr_schedule == base_preset.lr_schedule
        assert cfg.lr_min_ratio == base_preset.lr_min_ratio
        assert cfg.learning_rate == base_preset.learning_rate
        assert cfg.parameterization == base_preset.parameterization
        assert cfg.tv_weight == base_preset.tv_weight
        assert cfg.content_weight == base_preset.content_weight
        assert cfg.style_weight == base_preset.style_weight
        assert cfg.steps == base_preset.steps
        assert cfg.max_dim == base_preset.max_dim
        assert cfg.init == base_preset.init
        assert cfg.content_layers == base_preset.content_layers
        assert cfg.preview_every == base_preset.preview_every

    # 2. Check per-style overrides (impression_sunrise)
    reg = get_default_registry()
    presets_dict = reg.ensure_registry()
    imp = presets_dict.get("impression_sunrise")
    assert imp is not None
    assert imp.recommended_weights is not None

    imp_cfg = build_config_from_ui_state("balanced", rec_settings=imp.recommended_weights)
    assert imp_cfg.content_weight == 120.0
    assert imp_cfg.multi_crop_style is True
    assert imp_cfg.num_style_crops == 8
    assert imp_cfg.style_crop_exclude == [0.5, 0.0, 0.88, 0.8]
    assert imp_cfg.style_layer_weights == {
        "conv1_1": 0.28,
        "conv2_1": 0.25,
        "conv3_1": 0.25,
        "conv4_1": 0.17,
        "conv5_1": 0.05,
    }
    # Base balanced parameters are preserved
    assert imp_cfg.steps == PRESETS["balanced"].steps
    assert imp_cfg.max_dim == PRESETS["balanced"].max_dim
    assert imp_cfg.learning_rate == PRESETS["balanced"].learning_rate
    assert imp_cfg.parameterization == PRESETS["balanced"].parameterization
    assert imp_cfg.preview_every == PRESETS["balanced"].preview_every
