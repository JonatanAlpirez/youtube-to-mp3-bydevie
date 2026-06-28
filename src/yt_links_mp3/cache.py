"""Cache persistente para metadata de videos.

Almacena el resultado de yt-dlp.extract_info por video_id en un JSON local.
Evita llamadas repetidas a YouTube cuando el mismo video aparece en varios
archivos de links o en varias corridas.

Storage:
- Path por defecto: $XDG_CACHE_HOME/yt-links-mp3/metadata.json
- Fallback: ~/.cache/yt-links-mp3/metadata.json
- Configurable vía Config.cache_path / Config.cache_ttl_seconds

Formato JSON:
{
  "dQw4w9WgXcQ": {
    "_cached_at": 1719840000.123,
    "info": { "id": "dQw4w9WgXcQ", "title": "...", ... }
  }
}
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

# YouTube video IDs son 11 chars: letras, dígitos, - y _
_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_YOUTUBE_ID_FROM_URL_RE = re.compile(r"(?:v=|youtu\.be/|/shorts/)([A-Za-z0-9_-]{11})")


def extract_video_id(url_or_id: str) -> str:
    """Extrae el video_id de 11 chars de una URL o devuelve el ID si ya lo es.

    Para URLs no-YouTube (SoundCloud, Bandcamp, etc.) devuelve el input tal cual.
    """
    if _VIDEO_ID_RE.match(url_or_id):
        return url_or_id
    m = _YOUTUBE_ID_FROM_URL_RE.search(url_or_id)
    if m:
        return m.group(1)
    return url_or_id


class MetadataCache:
    """Cache persistente (load-on-demand, write-on-modify) en JSON."""

    def __init__(self, path: Path, ttl_seconds: float | None = None) -> None:
        self.path = path
        self.ttl_seconds = ttl_seconds
        self._data: dict[str, dict] = {}
        self._loaded = False

    def _load(self) -> None:
        """Carga el cache desde disco si existe."""
        if self._loaded:
            return
        self._loaded = True
        if not self.path.exists():
            return
        try:
            content = self.path.read_text(encoding="utf-8")
            self._data = json.loads(content)
            if not isinstance(self._data, dict):
                self._data = {}
        except (json.JSONDecodeError, OSError):
            # Cache corrupto o no legible: empezamos vacíos
            self._data = {}

    def _persist(self) -> None:
        """Guarda el cache a disco."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def get(self, video_id: str) -> dict | None:
        """Obtiene metadata cacheada por video_id, o None si no existe o expiró."""
        self._load()
        entry = self._data.get(video_id)
        if entry is None:
            return None
        if self.ttl_seconds is not None:
            cached_at = entry.get("_cached_at", 0)
            if (time.time() - cached_at) > self.ttl_seconds:
                return None
        return entry.get("info")

    def set(self, video_id: str, info: dict) -> None:
        """Guarda metadata para video_id."""
        self._load()
        self._data[video_id] = {
            "_cached_at": time.time(),
            "info": info,
        }
        self._persist()

    def clear(self) -> None:
        """Borra el cache (memoria y disco)."""
        self._data = {}
        self._loaded = True
        if self.path.exists():
            self.path.unlink()

    def size(self) -> int:
        """Cantidad de entradas en cache."""
        self._load()
        return len(self._data)


def default_cache_path() -> Path:
    """Devuelve el path por defecto del cache."""
    xdg = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg) if xdg else Path.home() / ".cache"
    return base / "yt-links-mp3" / "metadata.json"
