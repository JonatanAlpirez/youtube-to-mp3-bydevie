"""Descargador: orquesta yt-dlp + ffmpeg para cada link."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from loguru import logger
from yt_dlp import YoutubeDL

from .config import Config
from .linklist import LinkEntry


@dataclass
class DownloadResult:
    entry: LinkEntry
    success: bool
    output_path: str | None
    error: str | None


def _ydl_opts(config: Config) -> dict:
    """Opciones comunes para yt-dlp."""
    return {
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": config.audio_format,
                "preferredquality": str(config.audio_quality),
            }
        ],
        "outtmpl": str(config.output_dir / "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        # Metadatos embebidos: yt-dlp escribe info.json y ffmpeg los embebe
        "writeinfojson": False,
        "writethumbnail": config.embed_thumbnail,
    }


def download_one(entry: LinkEntry, config: Config) -> DownloadResult:
    """Descarga un solo entry. Devuelve DownloadResult."""
    config.output_dir.mkdir(parents=True, exist_ok=True)

    try:
        with YoutubeDL(_ydl_opts(config)) as ydl:
            logger.debug(f"Descargando {entry.url} (línea {entry.line_number})")
            info = ydl.extract_info(entry.url, download=True)
            # yt-dlp devuelve el path final del archivo extraído
            output_path = ydl.prepare_filename(info)
            # prepare_filename devuelve pre-conversión; el real está con la extensión final
            final_ext = config.audio_format
            output_path = output_path.rsplit(".", 1)[0] + f".{final_ext}"
            return DownloadResult(
                entry=entry,
                success=True,
                output_path=output_path,
                error=None,
            )
    except Exception as e:  # noqa: BLE001 - queremos capturar todo yt-dlp
        logger.error(f"Falló {entry.url}: {e}")
        return DownloadResult(
            entry=entry,
            success=False,
            output_path=None,
            error=str(e),
        )


def download_all(entries: list[LinkEntry], config: Config) -> list[DownloadResult]:
    """Descarga todos los entries con concurrencia del config."""
    if config.dry_run:
        logger.info(f"[dry-run] {len(entries)} links NO se descargarán")
        for e in entries:
            logger.info(f"  - {e.url}  ({e.description or 'sin descripción'})")
        return [
            DownloadResult(entry=e, success=True, output_path=None, error="dry-run")
            for e in entries
        ]

    results: list[DownloadResult] = []
    with ThreadPoolExecutor(max_workers=config.concurrency) as executor:
        future_to_entry = {
            executor.submit(download_one, entry, config): entry for entry in entries
        }
        for future in as_completed(future_to_entry):
            result = future.result()
            results.append(result)

    return results


def write_failed_links(results: list[DownloadResult], output_path: str) -> int:
    """Escribe los links fallidos a un archivo para reintentar. Devuelve cuántos escribió."""
    failed = [r for r in results if not r.success]
    if not failed:
        return 0
    lines = ["# Links fallidos - reintentá con: yt-links-mp3 download <este archivo>\n"]
    for r in failed:
        lines.append(f"{r.entry.url}    {r.entry.description or ''}\n")
    from pathlib import Path

    Path(output_path).write_text("".join(lines), encoding="utf-8")
    return len(failed)