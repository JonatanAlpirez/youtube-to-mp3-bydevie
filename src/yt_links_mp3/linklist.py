"""Parser del archivo de links.

Tolera comentarios (# y //), líneas vacías, IDs solos, dedupe preservando orden
y descripción opcional después de la URL.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# Acepta IDs de YouTube de 11 chars: A-Z, a-z, 0-9, -, _
_YT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")

# URL completa de YouTube
_FULL_URL_RE = re.compile(r"https?://(?:www\.|m\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([A-Za-z0-9_-]{11})")


@dataclass(frozen=True)
class LinkEntry:
    """Una entrada parseada del archivo de links."""

    video_id: str
    url: str
    description: str | None
    line_number: int
    raw: str


@dataclass(frozen=True)
class ParseResult:
    """Resultado del parseo del archivo."""

    entries: list[LinkEntry]
    skipped: list[tuple[int, str, str]]  # (line_number, raw_line, reason)

    @property
    def total(self) -> int:
        return len(self.entries)

    @property
    def unique_ids(self) -> set[str]:
        return {e.video_id for e in self.entries}


def _extract_video_id(token: str) -> str | None:
    """Extrae el video_id de un token. Acepta URL completa, youtu.be, o ID solo."""
    m = _FULL_URL_RE.search(token)
    if m:
        return m.group(1)
    if _YT_ID_RE.match(token):
        return token
    return None


def parse_link_line(line: str) -> tuple[str | None, str | None]:
    """Parsea una línea no vacía y devuelve (video_id, description) o (None, None).

    Acepta que después del ID/URL haya texto separado por espacios o tab,
    que se devuelve como descripción opcional (sin # inicial si la línea
    empieza con eso, se maneja en parse_link_file).
    """
    # Tomamos el primer token como candidato a URL/ID
    parts = line.split(maxsplit=1)
    if not parts:
        return None, None

    first = parts[0]
    video_id = _extract_video_id(first)
    if not video_id:
        return None, None

    description = parts[1].strip() if len(parts) > 1 else None
    return video_id, description


def parse_link_file(path: str | Path) -> ParseResult:
    """Parsea un archivo de links tolerante.

    Reglas:
      - Línea vacía o solo whitespace: ignorada
      - Línea que empieza con # o //: ignorada (comentario)
      - URLs completas o youtu.be/<id>: aceptadas
      - IDs solos de 11 chars: aceptados, normalizados a https://youtu.be/<id>
      - Texto después de la URL/ID: se guarda como descripción
      - Duplicados: deduplicados preservando primera aparición
      - Encoding: UTF-8 estricto, BOM tolerado
      - Líneas que no matchean: warning + skip (no aborta)
    """
    file_path = Path(path)
    raw_text = file_path.read_text(encoding="utf-8-sig")

    entries: list[LinkEntry] = []
    skipped: list[tuple[int, str, str]] = []
    seen_ids: dict[str, int] = {}  # video_id -> primera line_number donde apareció

    for line_number, raw_line in enumerate(raw_text.splitlines(), start=1):
        stripped = raw_line.strip()

        # Vacía o comentario
        if not stripped or stripped.startswith(("#", "//")):
            continue

        video_id, description = parse_link_line(stripped)

        if video_id is None:
            skipped.append((line_number, raw_line, "no parece ser un link o ID válido"))
            continue

        # Dedupe preservando primera aparición
        if video_id in seen_ids:
            first_line = seen_ids[video_id]
            skipped.append((line_number, raw_line, f"duplicado de línea {first_line}"))
            continue

        seen_ids[video_id] = line_number
        url = f"https://youtu.be/{video_id}"
        entries.append(
            LinkEntry(
                video_id=video_id,
                url=url,
                description=description,
                line_number=line_number,
                raw=raw_line,
            )
        )

    return ParseResult(entries=entries, skipped=skipped)