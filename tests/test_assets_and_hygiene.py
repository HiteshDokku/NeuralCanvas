"""Asset integrity and repository hygiene tests."""

from __future__ import annotations

import os
import re
from pathlib import Path

from PIL import Image


def test_assets_and_styles_integrity() -> None:
    """Verify that every sample and style image opens cleanly with PIL and meets minimum sizes."""
    project_root = Path(__file__).resolve().parent.parent
    samples_dir = project_root / "assets" / "samples"
    styles_dir = project_root / "styles"

    image_extensions = {".jpg", ".jpeg", ".png", ".webp"}
    failing_files: list[str] = []

    # Check assets/samples
    assert samples_dir.exists(), f"Samples directory missing: {samples_dir}"
    for img_path in samples_dir.iterdir():
        if img_path.suffix.lower() not in image_extensions:
            continue
        try:
            file_size_kb = img_path.stat().st_size / 1024
            if file_size_kb < 5.0:
                failing_files.append(
                    f"{img_path.name}: file size too small ({file_size_kb:.1f} KB)"
                )
                continue
            with Image.open(img_path) as im:
                w, h = im.size
                if w < 64 or h < 64:
                    failing_files.append(f"{img_path.name}: dimensions too small ({w}x{h})")
        except Exception as err:
            failing_files.append(f"{img_path.name}: failed to open with PIL ({err})")

    # Check styles/ (excluding _old, .cache, thumbs)
    assert styles_dir.exists(), f"Styles directory missing: {styles_dir}"
    for img_path in styles_dir.iterdir():
        if not img_path.is_file() or img_path.suffix.lower() not in image_extensions:
            continue
        try:
            file_size_kb = img_path.stat().st_size / 1024
            if file_size_kb < 10.0:
                failing_files.append(
                    f"{img_path.name}: file size too small ({file_size_kb:.1f} KB)"
                )
                continue
            with Image.open(img_path) as im:
                w, h = im.size
                if w < 256 or h < 256:
                    failing_files.append(f"{img_path.name}: dimensions too small ({w}x{h})")
        except Exception as err:
            failing_files.append(f"{img_path.name}: failed to open with PIL ({err})")

    assert not failing_files, "Asset integrity check failed for files:\n" + "\n".join(failing_files)


def test_repo_hygiene_cleanliness() -> None:
    """Ensure no dummy strings, fake domains, local paths, or forbidden URLs exist."""
    project_root = Path(__file__).resolve().parent.parent
    forbidden_tokens = [
        "place" + "holder",
        "example" + ".org",
        "file" + ":///",
        "c:" + chr(92) + "users",
        "c:/" + "users",
        "one" + "drive",
        "." + "gemini",
    ]
    hites_regex = re.compile(r"\b" + "hites" + r"\b", re.IGNORECASE)
    email_regex = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")

    ignore_dirs = {
        ".git",
        ".venv",
        "venv",
        "env",
        ".env",
        "test_venv",
        ".pytest_cache",
        ".ruff_cache",
        "__pycache__",
        "outputs",
        ".streamlit",
        "site-packages",
        "dist-info",
        "build",
        "dist",
    }
    checked_extensions = {
        ".py",
        ".md",
        ".toml",
        ".json",
        ".txt",
        ".yml",
        ".yaml",
        ".ipynb",
        ".cfg",
        ".html",
        ".sh",
        ".ps1",
    }

    violations: list[str] = []

    for root, dirs, files in os.walk(project_root):
        dirs[:] = [
            d
            for d in dirs
            if d not in ignore_dirs
            and not d.startswith(".")
            and not d.endswith("venv")
            and not d.endswith("env")
        ]
        for fname in files:
            path = Path(root) / fname
            if path.suffix.lower() not in checked_extensions:
                continue
            # Skip this test file itself and scanner for literal string definitions
            if path.name in ("test_assets_and_hygiene.py", "scan_hygiene.py"):
                continue

            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
                for line_idx, line in enumerate(content.splitlines(), start=1):
                    line_lower = line.lower()
                    for token in forbidden_tokens:
                        if token in line_lower:
                            violations.append(
                                f"{path.relative_to(project_root)}:{line_idx} - Contains '{token}': {line.strip()[:80]}"
                            )
                    if hites_regex.search(line):
                        violations.append(
                            f"{path.relative_to(project_root)}:{line_idx} - Contains author identity: {line.strip()[:80]}"
                        )
                    for match in email_regex.finditer(line):
                        email = match.group(0)
                        violations.append(
                            f"{path.relative_to(project_root)}:{line_idx} - Contains email '{email}': {line.strip()[:80]}"
                        )
            except Exception as err:
                violations.append(f"{path.relative_to(project_root)}: error reading file ({err})")

    assert not violations, "Repository hygiene check failed:\n" + "\n".join(violations)


def test_markdown_relative_links_and_images() -> None:
    """Verify that every relative link and image in README.md and CREDITS.md exists."""
    repo_root = Path(__file__).resolve().parent.parent

    for doc_name in ["README.md", "CREDITS.md"]:
        doc_path = repo_root / doc_name
        assert doc_path.exists(), f"Missing documentation file: {doc_name}"

        content = doc_path.read_text(encoding="utf-8")

        # Strip HTML comments (e.g. <!-- commented snippet -->)
        clean_content = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)

        # Match markdown links: [label](path) and ![alt](path)
        pattern = r"!?\[([^\]]*)\]\(([^)]+)\)"
        matches = re.findall(pattern, clean_content)

        for label, url in matches:
            url_clean = url.strip()
            # Ignore absolute URLs, protocol schemes, and anchors
            if (
                url_clean.startswith("http://")
                or url_clean.startswith("https://")
                or url_clean.startswith("#")
                or url_clean.startswith("mailto:")
            ):
                continue

            # Strip any in-page anchors
            target_path = url_clean.split("#")[0]
            if not target_path:
                continue

            resolved_file = repo_root / target_path
            assert resolved_file.exists(), (
                f"Broken relative link in {doc_name}: '{target_path}' (label: '{label}') "
                f"does not exist on disk at {resolved_file}"
            )
