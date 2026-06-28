# PLAN.md — yt-links-mp3

Plan de implementación por fases, pensado para entregar valor temprano y validar las decisiones de diseño antes de escalar.

---

## 🎯 Objetivo

Construir una herramienta CLI que lea un archivo de texto con URLs de videos individuales (uno por línea) y descargue cada uno como MP3 con metadatos limpios y portada embebida. Soporta YouTube y otros sitios compatibles con `yt-dlp` (SoundCloud, Bandcamp, Vimeo, etc.). Los archivos se guardan en una carpeta plana (sin subcarpetas por artista/álbum) con naming consistente `{NN} - {artist} - {title}.mp3`.

---

## 🧭 Decisiones de diseño (ADR-lite)

| # | Decisión | Razón | Alternativas descartadas |
|---|----------|-------|--------------------------|
| 1 | Usar `yt-dlp` sobre `youtube-dl` | Mantenido activamente, mejor soporte de URLs individuales, postprocesado más estable | `youtube-dl` (abandonado), `pytube` (frágil) |
| 2 | CLI en Python + `click` | Ecosistema maduro, fácil de empaquetar, tests sencillos | Node.js (overkill), Go (recompilar deps), Bash (mantenimiento) |
| 3 | Concurrencia con `ThreadPoolExecutor` | yt-dlp es I/O bound, threads son suficientes y simples | `asyncio` (overkill para subprocess), `multiprocessing` (más memoria) |
| 4 | Postprocesado con `ffmpeg` directo | Control total sobre bitrate/metadatos, sin intermediarios | `mutagen` (solo metadatos, no convierte), `pydub` (envuelve ffmpeg) |
| 5 | Config en YAML + pydantic BaseModel | Validación, autocompletado, separación código/config | TOML (menos legible), JSON (sin comentarios) |
| 6 | Nombres por metadatos (no por título de video) | Un mismo video puede tener título "raro" pero artista/título correctos | Usar `--output` de yt-dlp directo (limitado) |
| 7 | **Parser del archivo de links tolerante** | Aceptar líneas vacías, comentarios `#`, espacios, URLs con/sin `https://`, IDs solos (`dQw4w9WgXcQ`) | Parser estricto (frágil ante edición manual) |
| 8 | Empaquetar como CLI instalable (`pip install -e .`) | Una vez instalado, se invoca como comando nativo | Script suelto (depende de PYTHONPATH) |

---

## 🏗️ Arquitectura

```
yt-links-mp3/
├── pyproject.toml
├── README.md
├── PLAN.md
├── config.example.yaml
├── links.example.txt
├── .pre-commit-config.yaml        # ruff lint + format hooks
├── .github/workflows/tests.yml   # CI: lint + tests matrix 3.10/3.11/3.12
├── Makefile                      # install, test, lint, format, run, clean
├── src/yt_links_mp3/
│   ├── cli.py              # entrypoint click: download, info, validate
│   ├── config.py           # pydantic BaseModel (carga YAML)
│   ├── linklist.py         # parser tolerante (YouTube + URLs genéricas)
│   ├── downloader.py       # ThreadPoolExecutor + retry + fetch_metadata_cached
│   ├── metadata.py         # TrackMetadata + cleanup_title + build_metadata
│   ├── paths.py            # sanitize + build_filename + ensure_unique_path
│   ├── cache.py            # MetadataCache persistente (JSON local)
│   ├── progress.py         # barras rich
│   └── logging.py          # loguru config
└── tests/
    ├── test_linklist.py    # parser (YouTube + sitios múltiples)
    ├── test_metadata.py    # limpieza regex + extracción
    ├── test_paths.py       # sanitización + naming
    ├── test_config.py      # carga YAML + defaults
    ├── test_downloader.py  # retry + concurrencia
    ├── test_cli.py         # comando info + helpers
    └── test_cache.py       # MetadataCache + extract_video_id
```

### Flujo de datos

```
links.txt
   │
   ▼
parse_link_file()          → list[LinkEntry(video_id, url, description, line_number)]
   │
   ▼ (filter vacíos, comentarios, dedupe preservando orden)
list[LinkEntry]
   │
   ▼
build_metadata() para cada entry     (usa cache si está disponible)
   │
   ▼
ThreadPoolExecutor (concurrency=N)
   │  ┌───────────────────────┐
   │  ▼                       ▼                       ▼
download_one          download_one            download_one
(yt-dlp bestaudio     (yt-dlp bestaudio        (yt-dlp bestaudio
 + retry x3 +         + retry x3 +             + retry x3 +
 build MP3)           build MP3)               build MP3)
   │                       │                       │
   └───────────────────────┼───────────────────────┘
                           ▼
                  output_dir/<NN> - <artist> - <title>.mp3   (flat)
                           +
                  links.txt.failed  (solo si hay fallos)
```

---

## 📄 Formato del archivo de links (`links.txt`)

```text
# Comentarios con # son ignorados
# Líneas vacías también se ignoran
# Las URLs pueden estar solas o tener descripción opcional después de un espacio

# --- Canciones sueltas ---
https://www.youtube.com/watch?v=dQw4w9WgXcQ
https://youtu.be/jNQXAC9IVRw          Rick Astley clásico
dQw4w9WgXcQ                            # También acepta solo el ID

# --- Mezclando canales ---
https://www.youtube.com/watch?v=9bZkp7q19f0   Gangnam Style
https://www.youtube.com/watch?v=kJQP7kiw5Fk   Despacito

# --- Live sets largos ---
https://www.youtube.com/watch?v=4xDzrJKXOOY   Boiler Room (mezcla 1h)
```

### Reglas del parser

| Caso | Comportamiento |
|---|---|
| Línea vacía | Ignorada |
| Línea que empieza con `#` | Ignorada (comentario) |
| Línea que empieza con `//` | Ignorada (comentario estilo code) |
| URL completa de YouTube (`youtube.com/watch?v=ID`, `youtu.be/ID`, `youtube.com/shorts/ID`) | Aceptada, normalizada a `https://youtu.be/<id>` |
| Solo el ID de video de YouTube (11 chars alfanuméricos + `-_`) | Aceptado, expandido a `https://youtu.be/<id>` |
| Cualquier URL `http(s)://` (SoundCloud, Bandcamp, Vimeo, etc.) | Aceptada tal cual. `yt-dlp` elige el extractor por la URL. |
| Texto después de la URL (separado por espacios o tab) | Se guarda como `description` opcional (puede usarse como hint para metadatos) |
| Duplicado por video_id (YouTube) o URL completa (otros sitios) | Se deduplica preservando la primera aparición |
| Línea que no matchea nada | Warning + skip (no aborta) |
| Encoding | UTF-8 estricto, BOM tolerado |

---

## 📅 Fases

### Fase 0 — Bootstrap ✅

- Repo con `README.md`, `PLAN.md`, `.gitignore` para Python
- Branch `main`, repo remoto en GitHub
- Proyecto renombrado a `yt-links-mp3` (paquete y CLI)
- `pyproject.toml` con deps: `yt-dlp`, `click`, `pydantic`, `pyyaml`, `loguru`, `rich`
- Estructura `src/` + `tests/`
- `config.example.yaml` y `links.example.txt`
- Virtualenv con Python 3.11 (vía Homebrew)
- Paquete instalable: `pip install -e .` deja `yt-links-mp3` en PATH

### Fase 1 — MVP funcional ✅

- `linklist.py`: parser del archivo de links (comentarios, vacíos, IDs solos, dedupe)
- `cli.py` con comando `download <archivo.txt>`
- `cli.py` con comando `validate <archivo.txt>` (preflight sin descargar)
- `downloader.py`: usa `yt-dlp` para `bestaudio` + convierte a MP3 con `ffmpeg`
- `paths.py`: sanitización de nombres
- `progress.py`: barra de progreso global con `rich`
- Logging a consola con `loguru`

### Fase 2 — Metadatos y naming ✅

**Objetivo:** MP3s con metadatos limpios, portada embebida, nombre consistente `{NN} - {artist} - {title}.mp3`.

**Decisiones de diseño cerradas:**

| # | Decisión | Detalle |
|---|----------|---------|
| 1 | **Estructura de carpetas** | Flat. Todos los MP3s en `output_dir` (sin subcarpetas). |
| 2 | **Template de nombre** | `{track_number:02d} - {artist} - {title}.mp3`. Configurable vía `filename_template`. |
| 3 | **Track number** | Incremental 01, 02, 03… según orden en `links.txt`. |
| 4 | **Limpieza de metadatos** | Regex case-insensitive: borrar `Official Video`, `HD`, `(Lyric)`. Configurable. |
| 5 | **Portada** | Embedida en el MP3 (ID3v2.4 cover art). `maxresdefault` con fallback a `hqdefault`. |
| 6 | **Metadatos faltantes** | Artista ausente → `"Unknown Artist"`. Título ausente → título original o `video_id`. |
| 7 | **Hint manual** | Descripción en `links.txt` puede sobreescribir artista/título (`Artist - Title` o `Artist/Title`). |
| 8 | **Skip existing** | Si `{template}.mp3` ya existe, skip. `--force` ignora. |

**Implementación:**

- Módulo `metadata.py`: extracción desde yt-dlp + limpieza regex + sanitización
- `paths.py`: `build_filename(template, metadata)` compone el nombre final
- `downloader.py`: usa metadata para nombrar output + skip existing + cover embed
- `tests/test_metadata.py`: cubre regex y casos de fallback

### Fase 3 — Robustez ✅

- Reintentos: 3 intentos con backoff exponencial (1s, 5s, 15s) en errores transitorios. Errores permanentes (404, privado, eliminado, age-restricted) NO se reintentan.
- Concurrencia real: `download_all()` usa `ThreadPoolExecutor` con `config.concurrency` workers
- `--concurrency N` funciona end-to-end (default: 3)
- Resumen final: N exitosos, M skip, K fallidos, R requirieron retry. Escribe `links.txt.failed` si hay fallos
- Comando `info <link|archivo>` para ver metadata sin descargar

### Fase 4 — Calidad y DX ✅

- 125 tests unitarios pasando (ver Fase 5 para la distribución completa actualizada)
- `pre-commit` con `ruff` lint + format (`.pre-commit-config.yaml`)
- CI con GitHub Actions: lint + tests en matrix Python 3.10/3.11/3.12
- `Makefile` con targets: `install`, `test`, `lint`, `lint-fix`, `format`, `run`, `clean`
- `ruff check .` y `ruff format --check .` pasan limpios

### Fase 5 — Pulido ✅

- Cache persistente de metadata (`~/.cache/yt-links-mp3/metadata.json`) con TTL configurable (default 7 días). Acelera `info` y `download` cuando un video aparece varias veces.
- Soporte para sitios múltiples vía yt-dlp: SoundCloud, Bandcamp, Vimeo y cualquier URL `http(s)://`. El parser acepta URLs genéricas además de las de YouTube.
- Empaquetable con `pipx` para uso como comando global sin venv manual.
- Tests: **125/125 pasando** — `linklist.py` (17: 9 YouTube + 8 multi-sitio), `metadata.py` (36), `paths.py` (18), `config.py` (5), `downloader.py` (18), `cli.py` (15), `cache.py` (16).

### Fase 6 — Futuras ideas

- [ ] Integración con MusicBrainz para mejorar la calidad de metadatos (artista, álbum, año, carátula de release oficial)
- [ ] Auto-organizar en estructura `{artist}/{year - album}/` si hay año disponible

---

## 🧪 Cómo testear manualmente

```bash
# 1. Crear un archivo de prueba
cat > /tmp/links.txt <<EOF
# Canciones de prueba
https://www.youtube.com/watch?v=dQw4w9WgXcQ
https://www.youtube.com/watch?v=9bZkp7q19f0
dQw4w9WgXcQ  # ID solo (debe ser dedupe'd)
EOF

# 2. Validar (sin descargar)
yt-links-mp3 validate /tmp/links.txt

# 3. Ver metadata sin descargar
yt-links-mp3 info /tmp/links.txt

# 4. Dry-run
yt-links-mp3 download /tmp/links.txt --dry-run

# 5. Descargar de verdad
yt-links-mp3 download /tmp/links.txt -o /tmp/test

# 6. Verificar
ls -la /tmp/test/
ffprobe "/tmp/test/<archivo>.mp3"
```

Verificar:
- El ID duplicado (`dQw4w9WgXcQ`) aparece solo una vez
- Comentarios y líneas vacías no generan downloads
- Archivos con nombres consistentes (`NN - Artist - Title.mp3`)
- `ffprobe archivo.mp3` muestra metadatos (artista, título, álbum si está)
- Portada visible en Finder/VLC
- No quedan archivos `.part` o `.tmp`
- Una segunda corrida del mismo archivo: todos como `skip`
- `info` muestra tabla con N, Artista, Título, Duración, Descargado
- `info` con cache deshabilitado igual funciona; con cache activado la 2da corrida es instantánea

---

## 🔧 Ejemplo de uso real (workflow típico)

```bash
# Día 1: armás tu archivo de links curado
vim ~/Music/links.txt
# Pegás URLs a mano, con descripciones opcionales

# Día 1: descargás todo
yt-links-mp3 download ~/Music/links.txt

# Días siguientes: agregás más links y volvés a correr
vim ~/Music/links.txt
yt-links-mp3 download ~/Music/links.txt
# → skip automático de los que ya están descargados

# Si algo falló (video privado, geo-block, etc.):
cat ~/Music/links.txt.failed     # solo los que fallaron
yt-links-mp3 download ~/Music/links.txt.failed  # reintenta esos
```

---

## ⚠️ Riesgos y mitigaciones

| Riesgo | Mitigación |
|--------|-----------|
| YouTube cambia la firma de las URLs y `yt-dlp` se rompe | Pin a versión estable de `yt-dlp`; documentar cómo actualizar |
| `ffmpeg` no instalado en el sistema | Verificar en `cli.py` y abortar con mensaje claro |
| Archivo de links mal formateado (URLs inválidas, encoding raro) | Parser tolerante: warn + skip líneas malas, no abortar |
| Metadatos sucios (track con "Official Video" en el título) | Heurísticas de limpieza en `metadata.py`; permitir override manual |
| Copyright / DMCA | Disclaimer prominente en README; el proyecto es personal |
| Rate limiting de YouTube | Concurrencia baja por defecto (3) + cache persistente de metadata |
| El usuario pone la misma URL dos veces sin darse cuenta | Dedupe preservando orden + warning "URL duplicada en línea N" |
| Sitios no-YouTube con rate limits agresivos (SoundCloud) | Cache de metadata reduce llamadas; retry con backoff ya implementado |
| Python 3.9 deprecado por yt-dlp y pydantic 2 | `pyproject.toml` declara `>=3.10`; CI matrix 3.10/3.11/3.12 |

---

## 📊 Estimación restante

Fase 6 (MusicBrainz + estructura por artista/álbum) estimada en ~6–10 horas. No hay bloqueantes conocidos.

---

## 🚦 Estado actual

**Fase actual:** 5 — Pulido ✅ (cache + sitios múltiples + pipx)
**Próximo paso:** Fase 6 (MusicBrainz, estructura por artista/álbum)

### Notas operativas

- Python 3.10+ requerido (`pyproject.toml` declara `>=3.10`). Probado en 3.11 y 3.12.
- ffmpeg requerido por yt-dlp para el postprocess a MP3.

---
