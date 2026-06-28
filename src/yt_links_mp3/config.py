"""Config con pydantic + YAML."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from .cache import default_cache_path
from .metadata import DEFAULT_CLEANUP_PATTERNS


class Config(BaseModel):
    """Config principal del CLI."""

    output_dir: Path = Field(default=Path.home() / "Music" / "Downloads")
    audio_format: str = "mp3"
    audio_quality: int = 320  # kbps — máximo para MP3 (CBR)
    concurrency: int = 3
    # Reintentos en errores transitorios (network, 5xx, timeout).
    # Errores permanentes (404, privado, eliminado, age-restricted) no se reintentan.
    max_retries: int = 3
    # Base del backoff exponencial (segundos). Backoffs: base * 5^(attempt-1)
    # Default 1.0 → 1s, 5s, 15s.
    retry_backoff_base: float = 1.0
    skip_existing: bool = True
    force: bool = False
    dry_run: bool = False
    embed_thumbnail: bool = True
    # Template para el nombre del archivo. Placeholders:
    # {track_number}, {artist}, {title}, {video_id}, {ext}
    filename_template: str = "{track_number:02d} - {artist} - {title}.{ext}"
    # Patrones regex (case-insensitive) a borrar del título al limpiar
    cleanup_patterns: list[str] = Field(default_factory=lambda: list(DEFAULT_CLEANUP_PATTERNS))
    failed_filename: str = "links.txt.failed"
    # Cache persistente de metadata. None = sin cache (cada llamada a yt-dlp).
    # Path por defecto: ~/.cache/yt-links-mp3/metadata.json
    cache_path: Path | None = None
    # TTL del cache en segundos. None = sin expiración.
    # Default: 7 días (604800s) — razonable porque la metadata no cambia seguido.
    cache_ttl_seconds: float | None = 7 * 24 * 3600

    @classmethod
    def load(cls, path: str | Path | None = None) -> Config:
        """Carga config desde YAML. Si no hay path o no existe, devuelve defaults."""
        if path is None:
            return cls(cache_path=default_cache_path())
        file_path = Path(path)
        if not file_path.exists():
            return cls(cache_path=default_cache_path())
        data = yaml.safe_load(file_path.read_text(encoding="utf-8")) or {}
        # Expandir ~ en output_dir si viene como string
        if "output_dir" in data and isinstance(data["output_dir"], str):
            data["output_dir"] = Path(data["output_dir"]).expanduser()
        # Cache path: si el YAML no lo define, usar el default del sistema
        if "cache_path" not in data or data["cache_path"] is None:
            data["cache_path"] = default_cache_path()
        elif isinstance(data["cache_path"], str):
            data["cache_path"] = Path(data["cache_path"]).expanduser()
        return cls(**data)
