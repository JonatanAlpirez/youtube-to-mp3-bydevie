# PLAN.md — yt-playlist-mp3

Plan de implementación por fases, pensado para entregar valor temprano y validar las decisiones de diseño antes de escalar.

---

## 🎯 Objetivo

Construir una herramienta CLI que descargue una lista de reproducción de YouTube y la convierta a archivos MP3 con metadatos limpios, portada embebida, y estructura de carpetas ordenada por artista/álbum.

---

## 🧭 Decisiones de diseño (ADR-lite)

| # | Decisión | Razón | Alternativas descartadas |
|---|----------|-------|--------------------------|
| 1 | Usar `yt-dlp` sobre `youtube-dl` | Mantenido activamente, mejor soporte de playlists, postprocesado más estable | `youtube-dl` (abandonado), `pytube` (frágil) |
| 2 | CLI en Python + `click` | Ecosistema maduro, fácil de empaquetar, tests sencillos | Node.js (overkill), Go (recompilar deps), Bash (mantenimiento) |
| 3 | Concurrencia con `ThreadPoolExecutor` | yt-dlp es I/O bound, threads son suficientes y simples | `asyncio` (overkill para subprocess), `multiprocessing` (más memoria) |
| 4 | Postprocesado con `ffmpeg` directo | Control total sobre bitrate/metadatos, sin intermediarios | `mutagen` (solo metadatos, no convierte), `pydub` (envuelve ffmpeg) |
| 5 | Config en YAML + pydantic | Validación, autocompletado, separación código/config | TOML (menos legible), JSON (sin comentarios) |
| 6 | Nombres por metadatos (no por título de video) | Un mismo video puede tener título "raro" pero artista/título correctos | Usar `--output` de yt-dlp directo (limitado) |
| 7 | Empaquetar como CLI instalable (`pip install -e .`) | Una vez instalado, se invoca como comando nativo | Script suelto (depende de PYTHONPATH) |

---

## 🏗️ Arquitectura

```
yt-playlist-mp3/
├── pyproject.toml
├── README.md
├── PLAN.md
├── config.example.yaml
├── src/
│   └── yt_playlist_mp3/
│       ├── __init__.py
│       ├── cli.py              # entrypoint click (comandos: download, info)
│       ├── config.py           # pydantic-settings
│       ├── downloader.py       # orquesta descargas concurrentes
│       ├── metadata.py         # parseo/normalización de metadatos
│       ├── postprocess.py      # ffmpeg + embebido de metadatos/portada
│       ├── paths.py            # plantillas de paths seguros (sanitización)
│       ├── progress.py         # barras rich
│       └── logging.py          # loguru config
└── tests/
    ├── test_metadata.py
    ├── test_paths.py
    └── test_postprocess.py
```

### Flujo de datos

```
URL → fetch_playlist_info (yt-dlp) → list[VideoEntry]
                                          │
                                          ▼
                              ThreadPoolExecutor
                                          │
                  ┌───────────────────────┼───────────────────────┐
                  ▼                       ▼                       ▼
           download_audio          download_audio          download_audio
                  │                       │                       │
                  └───────────────────────┼───────────────────────┘
                                          ▼
                                  postprocess_to_mp3
                                  (ffmpeg + metadatos + cover)
                                          │
                                          ▼
                                  output_dir/<Artist>/<Album>/NN - Title.mp3
```

---

## 📅 Fases

### Fase 0 — Bootstrap (1h)
- [x] Crear repo con `README.md` y `PLAN.md`
- [x] `git init`, branch `main`, `.gitignore` para Python
- [ ] `pyproject.toml` con deps: `yt-dlp`, `click`, `pydantic`, `pyyaml`, `loguru`, `rich`
- [ ] Estructura de carpetas `src/` y `tests/`
- [ ] `config.example.yaml`

### Fase 1 — MVP funcional (4–6h)
- [ ] `cli.py` con comando `download` que recibe una URL de playlist
- [ ] `downloader.py`: usa `yt-dlp` para obtener metadata de la playlist
- [ ] `downloader.py`: descarga audio (formato `bestaudio`) y convierte a MP3 con `ffmpeg` postprocess
- [ ] `paths.py`: sanitiza nombres de archivo (caracteres prohibidos, longitud máxima)
- [ ] `progress.py`: barra de progreso global con `rich`
- [ ] Logging a consola con `loguru`
- [ ] Salida por defecto: `~/Music/Playlists/<Nombre de Playlist>/NN - Title.mp3`

**Criterio de aceptación:** dado el URL de una playlist de 10 videos, produce 10 MP3s válidos en menos de 5 minutos.

### Fase 2 — Metadatos ricos (3–4h)
- [ ] `metadata.py`: extraer artista/título/álbum de la descripción/título del video con heurísticas
- [ ] `postprocess.py`: embeber metadatos (ID3v2.4) y portada con `ffmpeg`
- [ ] Nombres por plantilla: `{artist}/{album}/{track_number:02d} - {title}.{ext}`
- [ ] Descargar `cover.jpg` de maxresdefault si está disponible

**Criterio de aceptación:** los MP3s se ven correctamente en iTunes/VLC/Files.app con carátula y metadatos.

### Fase 3 — Robustez (2–3h)
- [ ] `config.yaml` con todas las opciones (output_dir, concurrency, quality, dry-run, etc.)
- [ ] Flag `--dry-run` que muestra qué se descargaría sin escribir
- [ ] Flag `--force` para re-descargar
- [ ] Skip automático de videos ya descargados (hash por ID + duración)
- [ ] Manejo de errores: reintentos (3x con backoff), continuar si un video falla
- [ ] Resumen final: N exitosos, M fallidos, con lista de fallos

**Criterio de aceptación:** una playlist con 50 videos, 2 privados y 1 roto, termina con 48 archivos y un reporte claro.

### Fase 4 — Calidad y DX (2–3h)
- [ ] Tests unitarios para `paths.py`, `metadata.py`, `config.py`
- [ ] `pre-commit` con `ruff` + `black`
- [ ] CI con GitHub Actions (lint + tests en matrix Python 3.11/3.12)
- [ ] `Makefile` con targets: `install`, `test`, `lint`, `run`
- [ ] Comando `info <url>` que muestra metadata de la playlist sin descargar

### Fase 5 — Pulido (opcional)
- [ ] Soporte de canales completos (`/videos` page)
- [ ] Soporte de un solo video (no playlist)
- [ ] Cache de metadatos para evitar refetch
- [ ] Integración con `beets` o `MusicBrainz` para arreglar metadatos
- [ ] Empaquetado para `brew tap` o `pipx`

---

## 🧪 Cómo testear manualmente

```bash
# Crear una playlist de prueba pública (3–5 videos)
yt-playlist-mp3 download "https://www.youtube.com/playlist?list=PLxxxxxx" --dry-run
yt-playlist-mp3 download "https://www.youtube.com/playlist?list=PLxxxxxx" -o /tmp/test
ls -la /tmp/test/
```

Verificar:
- Archivos con nombres consistentes
- `ffprobe archivo.mp3` muestra metadatos
- Portada visible en Finder/VLC
- No quedan archivos `.part` o `.tmp`

---

## ⚠️ Riesgos y mitigaciones

| Riesgo | Mitigación |
|--------|-----------|
| YouTube cambia la firma de las URLs y `yt-dlp` se rompe | Pin a versión estable de `yt-dlp`; documentar cómo actualizar |
| `ffmpeg` no instalado en el sistema | Verificar en `cli.py` y abortar con mensaje claro |
| Metadatos sucios (track con "Official Video" en el título) | Heurísticas de limpieza en `metadata.py`; permitir override manual |
| Copyright / DMCA | Disclaimer prominente en README; el proyecto es personal |
| Rate limiting de YouTube | Concurrencia baja por defecto (3), respeto a `--limit-rate` de yt-dlp |

---

## 📊 Estimación total

~12–17 horas de desarrollo para llegar a Fase 3 funcional. Fase 4 y 5 son nice-to-have.

---

## 🚦 Estado actual

**Fase:** 0 — Bootstrap ✅
**Próximo paso:** Fase 1 — MVP funcional (pyproject + descarga básica)
