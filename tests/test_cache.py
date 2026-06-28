"""Tests para cache.py — MetadataCache + extract_video_id."""

from __future__ import annotations

import time
from pathlib import Path

from yt_links_mp3.cache import MetadataCache, default_cache_path, extract_video_id

# ------------------- extract_video_id -------------------


def test_extract_id_from_bare_id() -> None:
    assert extract_video_id("dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_video_id("abc-DEF_123") == "abc-DEF_123"


def test_extract_id_from_full_url() -> None:
    assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_video_id("https://youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_extract_id_returns_input_if_not_youtube() -> None:
    """URLs de SoundCloud/Bandcamp se devuelven tal cual."""
    assert (
        extract_video_id("https://soundcloud.com/artist/track")
        == "https://soundcloud.com/artist/track"
    )
    assert extract_video_id("https://bandcamp.com/track/123") == "https://bandcamp.com/track/123"


# ------------------- MetadataCache básico -------------------


def test_cache_miss_returns_none(tmp_path: Path) -> None:
    cache = MetadataCache(path=tmp_path / "meta.json")
    assert cache.get("dQw4w9WgXcQ") is None


def test_cache_set_and_get(tmp_path: Path) -> None:
    cache = MetadataCache(path=tmp_path / "meta.json")
    info = {"id": "abc12345678", "title": "Test Song"}
    cache.set("abc12345678", info)
    assert cache.get("abc12345678") == info


def test_cache_persists_across_instances(tmp_path: Path) -> None:
    """Una instancia escribe, otra lee desde el mismo path."""
    path = tmp_path / "meta.json"
    c1 = MetadataCache(path=path)
    c1.set("vid1", {"id": "vid1", "title": "First"})

    c2 = MetadataCache(path=path)
    assert c2.get("vid1") == {"id": "vid1", "title": "First"}


def test_cache_size(tmp_path: Path) -> None:
    cache = MetadataCache(path=tmp_path / "meta.json")
    assert cache.size() == 0
    cache.set("a", {"id": "a"})
    cache.set("b", {"id": "b"})
    assert cache.size() == 2


def test_cache_clear_in_memory(tmp_path: Path) -> None:
    cache = MetadataCache(path=tmp_path / "meta.json")
    cache.set("a", {"id": "a"})
    cache.clear()
    assert cache.size() == 0
    assert cache.get("a") is None


def test_cache_clear_removes_file(tmp_path: Path) -> None:
    path = tmp_path / "meta.json"
    cache = MetadataCache(path=path)
    cache.set("a", {"id": "a"})
    assert path.exists()
    cache.clear()
    assert not path.exists()


# ------------------- TTL -------------------


def test_cache_no_ttl_never_expires(tmp_path: Path) -> None:
    """Con ttl_seconds=None, las entradas nunca expiran."""
    cache = MetadataCache(path=tmp_path / "meta.json", ttl_seconds=None)
    cache.set("vid", {"id": "vid", "title": "T"})
    # Forzamos un get inmediato: debe estar
    assert cache.get("vid") is not None


def test_cache_ttl_expires(tmp_path: Path) -> None:
    """Con TTL corto, una entrada vieja devuelve None."""
    cache = MetadataCache(path=tmp_path / "meta.json", ttl_seconds=0.05)
    cache.set("vid", {"id": "vid"})
    time.sleep(0.1)
    assert cache.get("vid") is None


# ------------------- Robustez -------------------


def test_cache_corrupt_file_starts_empty(tmp_path: Path) -> None:
    """Si el JSON está corrupto, el cache arranca vacío en lugar de explotar."""
    path = tmp_path / "meta.json"
    path.write_text("esto no es JSON válido {]", encoding="utf-8")
    cache = MetadataCache(path=path)
    assert cache.size() == 0


def test_cache_creates_parent_dir(tmp_path: Path) -> None:
    """El cache crea el directorio padre si no existe."""
    nested = tmp_path / "deep" / "nested" / "meta.json"
    cache = MetadataCache(path=nested)
    cache.set("vid", {"id": "vid"})
    assert nested.exists()
    assert nested.parent.is_dir()


def test_cache_overwrites_existing_entry(tmp_path: Path) -> None:
    """set() sobre una key existente reemplaza el valor."""
    cache = MetadataCache(path=tmp_path / "meta.json")
    cache.set("vid", {"id": "vid", "title": "v1"})
    cache.set("vid", {"id": "vid", "title": "v2"})
    assert cache.get("vid") == {"id": "vid", "title": "v2"}


def test_cache_persists_unicode_correctly(tmp_path: Path) -> None:
    """Los caracteres unicode (tildes, ñ, emojis) se preservan al persistir."""
    cache = MetadataCache(path=tmp_path / "meta.json")
    cache.set("vid", {"title": "Canción con tildes y ñ — 🎵"})
    c2 = MetadataCache(path=tmp_path / "meta.json")
    assert c2.get("vid")["title"] == "Canción con tildes y ñ — 🎵"


# ------------------- default_cache_path -------------------


def test_default_cache_path_returns_path() -> None:
    """default_cache_path() devuelve un Path que termina en metadata.json."""
    p = default_cache_path()
    assert isinstance(p, Path)
    assert p.name == "metadata.json"
    assert "yt-links-mp3" in str(p)
