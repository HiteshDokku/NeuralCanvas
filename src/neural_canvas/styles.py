"""Style preset registry, thumbnail generation, and Gram target caching."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import torch
from PIL import Image

from .image_io import ImageSource, load_image
from .losses import gram_matrix
from .model import get_extractor, resolve_layer_indices

logger = logging.getLogger(__name__)

# Known masterworks metadata lookup for auto-population
KNOWN_STYLES_METADATA: dict[str, dict[str, str]] = {
    "a sunday afternoon on the island of la grande jatte": {
        "name": "A Sunday Afternoon on the Island of La Grande Jatte",
        "artist": "Georges Seurat",
        "year": "1884-1886",
        "credit": "Public Domain / Art Institute of Chicago",
    },
    "composition vii (1913)": {
        "name": "Composition VII",
        "artist": "Wassily Kandinsky",
        "year": "1913",
        "credit": "Public Domain / Tretyakov Gallery",
    },
    "impression, sunrise": {
        "name": "Impression, Sunrise",
        "artist": "Claude Monet",
        "year": "1872",
        "credit": "Public Domain / Musée Marmottan Monet",
    },
    "sudden shower over shin-ōhashi bridge and atake": {
        "name": "Sudden Shower over Shin-Ōhashi Bridge and Atake",
        "artist": "Utagawa Hiroshige",
        "year": "1857",
        "credit": "Public Domain / Brooklyn Museum",
    },
    "the fighting temeraire": {
        "name": "The Fighting Temeraire",
        "artist": "J. M. W. Turner",
        "year": "1838",
        "credit": "Public Domain / National Gallery, London",
    },
    "the great wave off kanagawa": {
        "name": "The Great Wave off Kanagawa",
        "artist": "Katsushika Hokusai",
        "year": "1831",
        "credit": "Public Domain / Tokyo National Museum",
    },
    "the kiss": {
        "name": "The Kiss",
        "artist": "Gustav Klimt",
        "year": "1907-1908",
        "credit": "Public Domain / Österreichische Galerie Belvedere",
    },
    "the scream": {
        "name": "The Scream",
        "artist": "Edvard Munch",
        "year": "1893",
        "credit": "Public Domain / National Gallery, Oslo",
    },
    "the starry night": {
        "name": "The Starry Night",
        "artist": "Vincent van Gogh",
        "year": "1889",
        "credit": "Public Domain / Museum of Modern Art",
    },
    "wheatfield with cypresses": {
        "name": "Wheatfield with Cypresses",
        "artist": "Vincent van Gogh",
        "year": "1889",
        "credit": "Public Domain / Metropolitan Museum of Art",
    },
}


def sanitize_id(filename: str) -> str:
    """Derive clean lowercase identifier from filename stem."""
    stem = Path(filename).stem.lower()
    clean = "".join(c if c.isalnum() else "_" for c in stem)
    while "__" in clean:
        clean = clean.replace("__", "_")
    return clean.strip("_")


@dataclass
class StylePreset:
    """Representation of a preset style artwork."""

    id: str
    name: str
    artist: str
    year: str
    credit: str
    image_path: str
    thumbnail_path: str
    recommended_weights: dict[str, Any] | None = None
    source_url: str | None = None
    license: str | None = None
    download_date: str | None = None
    best_for: str | None = None
    avoid_for: str | None = None
    style_group: str | None = None


class StyleRegistry:
    """Manages preset styles, thumbnails, and Gram target caching."""

    def __init__(self, styles_dir: str | Path | None = None) -> None:
        if styles_dir is None:
            p = Path("styles").resolve()
            if not p.exists():
                repo_root = Path(__file__).resolve().parent.parent.parent
                if (repo_root / "styles").exists():
                    p = (repo_root / "styles").resolve()
            self.styles_dir = p
        else:
            self.styles_dir = Path(styles_dir).resolve()

        self.json_path = self.styles_dir / "styles.json"
        self.thumbs_dir = self.styles_dir / "thumbs"
        self.cache_dir = self.styles_dir / ".cache"
        self._presets: dict[str, StylePreset] = {}

    def ensure_registry(self) -> dict[str, StylePreset]:
        """Scan styles directory, generate thumbnails, build or refresh styles.json."""
        if not self.styles_dir.exists():
            return {}

        self.thumbs_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        existing_data: dict[str, dict[str, Any]] = {}
        if self.json_path.exists():
            try:
                with open(self.json_path, encoding="utf-8") as f:
                    for item in json.load(f):
                        existing_data[item["id"]] = item
            except Exception as e:
                logger.warning("Could not read existing styles.json: %s", e)

        presets: dict[str, StylePreset] = {}
        valid_extensions = {".jpg", ".jpeg", ".png", ".webp"}

        for file_path in sorted(self.styles_dir.iterdir()):
            if not file_path.is_file() or file_path.suffix.lower() not in valid_extensions:
                continue
            if file_path.name.startswith("."):
                continue

            preset_id = sanitize_id(file_path.name)
            stem_lower = file_path.stem.lower()

            # Thumbnail generation
            thumb_path = self.thumbs_dir / f"{preset_id}_thumb.jpg"
            if not thumb_path.exists():
                try:
                    with Image.open(file_path) as img:
                        img_rgb = img.convert("RGB")
                        img_rgb.thumbnail((256, 256), Image.Resampling.LANCZOS)
                        img_rgb.save(thumb_path, "JPEG", quality=85)
                except Exception as err:
                    logger.warning("Failed to generate thumbnail for %s: %s", file_path, err)
                    continue

            # Populate metadata
            if preset_id in existing_data:
                meta = existing_data[preset_id]
                name = meta.get("name", file_path.stem.title())
                artist = meta.get("artist", "TODO")
                year = meta.get("year", "TODO")
                credit = meta.get("credit", "TODO")
                rec_weights = meta.get("recommended_weights")
                source_url = meta.get("source_url")
                license_info = meta.get("license")
                download_date = meta.get("download_date")
                best_for = meta.get("best_for")
                avoid_for = meta.get("avoid_for")
                style_group = meta.get("style_group")
            elif stem_lower in KNOWN_STYLES_METADATA:
                known = KNOWN_STYLES_METADATA[stem_lower]
                name = known["name"]
                artist = known["artist"]
                year = known["year"]
                credit = known["credit"]
                rec_weights = None
                source_url = None
                license_info = "Public Domain"
                download_date = None
                best_for = None
                avoid_for = None
                style_group = None
            else:
                name = file_path.stem.replace("_", " ").title()
                artist = "TODO"
                year = "TODO"
                credit = "TODO"
                rec_weights = None
                source_url = None
                license_info = None
                download_date = None
                best_for = None
                avoid_for = None
                style_group = None

            try:
                rel_img = str(file_path.relative_to(Path.cwd()))
            except ValueError:
                rel_img = str(file_path)

            try:
                rel_thumb = str(thumb_path.relative_to(Path.cwd()))
            except ValueError:
                rel_thumb = str(thumb_path)

            preset = StylePreset(
                id=preset_id,
                name=name,
                artist=artist,
                year=year,
                credit=credit,
                image_path=rel_img,
                thumbnail_path=rel_thumb,
                recommended_weights=rec_weights,
                source_url=source_url,
                license=license_info,
                download_date=download_date,
                best_for=best_for,
                avoid_for=avoid_for,
                style_group=style_group,
            )
            presets[preset_id] = preset

        # Save back to styles.json
        try:
            with open(self.json_path, "w", encoding="utf-8") as f:
                json.dump([asdict(p) for p in presets.values()], f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning("Could not write styles.json: %s", e)

        self._presets = presets
        return presets

    def list_presets(self) -> list[StylePreset]:
        """Return list of all registered style presets."""
        if not self._presets:
            self.ensure_registry()
        return list(self._presets.values())

    def get_preset(self, preset_id: str) -> StylePreset:
        """Retrieve a style preset by its ID."""
        if not self._presets:
            self.ensure_registry()
        if preset_id not in self._presets:
            raise KeyError(
                f"Preset '{preset_id}' not found. Available presets: {list(self._presets.keys())}"
            )
        return self._presets[preset_id]

    def get_cached_grams(
        self,
        preset_id: str,
        style_max_dim: int,
        style_layers: tuple[str, ...],
        weights_tag: str = "VGG19_Weights.IMAGENET1K_V1",
        device: torch.device | None = None,
    ) -> dict[str, torch.Tensor]:
        """Retrieve precomputed style Gram matrices from cache or compute and cache them."""
        preset = self.get_preset(preset_id)
        img_path = Path(preset.image_path)
        mtime = img_path.stat().st_mtime if img_path.exists() else 0.0

        key_data = (
            f"{preset_id}|{style_max_dim}|{sorted(style_layers)}|{weights_tag}|{mtime}"
        ).encode()
        cache_hash = hashlib.sha256(key_data).hexdigest()[:16]
        cache_file = self.cache_dir / f"{preset_id}_{cache_hash}.pt"

        if cache_file.exists():
            try:
                grams: dict[str, torch.Tensor] = torch.load(cache_file, weights_only=True)
                if device is not None:
                    grams = {k: v.to(device) for k, v in grams.items()}
                return grams
            except Exception as e:
                logger.warning("Failed loading cached Gram targets from %s: %s", cache_file, e)

        # Compute on CPU / device
        dev = device if device is not None else torch.device("cpu")
        style_tensor = load_image(img_path, max_dim=style_max_dim, device=dev)
        extractor = get_extractor(dev, weights=True)
        layer_indices = resolve_layer_indices(style_layers)

        with torch.no_grad():
            features = extractor(style_tensor, layer_indices)
            grams = {name: gram_matrix(feat) for name, feat in features.items()}

        # Cache on disk (CPU tensors)
        try:
            cpu_grams = {k: v.cpu() for k, v in grams.items()}
            torch.save(cpu_grams, cache_file)
        except Exception as e:
            logger.warning("Failed saving cached Gram targets to %s: %s", cache_file, e)

        return grams

    def resolve_style(
        self,
        source: str | Path | bytes | Image.Image,
        max_dim: int | None = None,
        device: torch.device | None = None,
    ) -> torch.Tensor:
        """Resolve a style source (preset id, path, bytes, or PIL Image) to a normalized Tensor."""
        if not self._presets:
            self.ensure_registry()

        if isinstance(source, str) and source in self._presets:
            path = self._presets[source].image_path
            return load_image(path, max_dim=max_dim, device=device)

        return load_image(source, max_dim=max_dim, device=device)


_DEFAULT_REGISTRY: StyleRegistry | None = None


def get_default_registry() -> StyleRegistry:
    """Get or create singleton style registry."""
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        _DEFAULT_REGISTRY = StyleRegistry()
        _DEFAULT_REGISTRY.ensure_registry()
    return _DEFAULT_REGISTRY


def list_presets() -> list[StylePreset]:
    """List all available style presets."""
    return get_default_registry().list_presets()


def get_preset(preset_id: str) -> StylePreset:
    """Get a style preset by its id."""
    return get_default_registry().get_preset(preset_id)


def resolve_style(
    source: ImageSource,
    max_dim: int | None = None,
    device: torch.device | None = None,
) -> torch.Tensor:
    """Resolve a style preset ID or arbitrary image source to a Tensor."""
    return get_default_registry().resolve_style(source, max_dim=max_dim, device=device)
