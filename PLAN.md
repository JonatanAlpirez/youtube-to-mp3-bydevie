# PLAN.md — yt-links-mp3

Plan de implementación por fases, pensado para entregar valor temprano y validar las decisiones de diseño antes de escalar.

---

## 🎯 Objetivo

Construir una herramienta CLI que lea un archivo de texto con URLs de videos individuales de YouTube (uno por línea) y descargue cada uno como MP3 con metadatos limpios, portada embebida y una estructura de carpetas ordenada por artista/álbum.

---

## 🧭 Decisiones de diseño (ADR-lite)

| # | Decisión | Razón | Alternativas descartadas |
|---|----------|-------|--------------------------|
| 1 | Usar `yt-dlp` sobre `youtube-dl` | Mantenido activamente, mejor soporte de URLs individuales, postprocesado más estable | `youtube-dl` (abandonado), `pytube` (frágil) |
| 2 | CLI en Python + `click` | Ecosistema maduro, fácil de empaquetar, tests sencillos | Node.js (overkill), Go (recompilar deps), Bash (mantenimiento) |
| 3 | Concurrencia con `ThreadPoolExecutor` | yt-dlp es I/O bound, threads son suficientes y simples | `asyncio` (overkill para subprocess), `multiprocessing` (más memoria) |
| 4 | Postprocesado con `ffmpeg` directo | Control total sobre bitrate/metadatos, sin intermediarios | `mutagen` (solo metadatos, no convierte), `pydub` (envuelve ffmpeg) |
| 5 | Config en YAML + pydantic | Validación, autocompletado, separación código/config | TOML (menos legible), JSON (sin comentarios) |
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
├── links.example.txt          # archivo de ejemplo con URLs
├── src/
│   └── yt_links_mp3/
│       ├── __init__.py
│       ├── cli.py              # entrypoint click (comandos: download, info, validate)
│       ├── config.py           # pydantic-settings
│       ├── linklist.py         # parser del archivo de URLs
│       ├── downloader.py       # orquesta descargas (ThreadPoolExecutor)
│       ├── paths.py            # plantillas de paths seguros (sanitización)
│       ├── progress.py         # barras rich
│       └── logging.py          # loguru config
└── tests/
    └── test_linklist.py        # parser de links
```

> Los módulos `metadata.py` y `postprocess.py` se agregarán en Fase 2.

### Flujo de datos

```
links.txt
   │
   ▼
parse_link_file()          → list[LinkEntry(url, line_number, raw)]
   │
   ▼ (filter vacíos, comentarios, dedupe preservando orden)
list[LinkEntry]
   │
   ▼
ThreadPoolExecutor
   │  ┌───────────────────────┐
   │  ▼                       ▼                       ▼
download_audio        download_audio          download_audio
(yt-dlp bestaudio)    (yt-dlp bestaudio)      (yt-dlp bestaudio)
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
| URL completa `https://...` | Aceptada |
| URL corta `youtu.be/<id>` | Aceptada, normalizada |
| Solo el ID de video (11 chars alfanuméricos + `-_`) | Aceptada, expandida a `https://youtu.be/<id>` |
| Texto después de la URL (separado por espacios o tab) | Se guarda como `description` opcional (puede usarse como hint para metadatos) |
| URL duplicada | Se deduplica preservando la primera aparición |
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

- 101 tests unitarios pasando: `linklist.py` (9), `metadata.py` (36), `paths.py` (18), `config.py` (5), `downloader.py` (18), `cli.py` (15)
- `pre-commit` con `ruff` lint + format (`.pre-commit-config.yaml`)
- CI con GitHub Actions: lint + tests en matrix Python 3.11/3.12
- `Makefile` con targets: `install`, `test`, `lint`, `lint-fix`, `format`, `run`, `clean`
- `ruff check .` y `ruff format --check .` pasan limpios

### Fase 5 — Pulido (en progreso)

- [ ] Cache de metadatos para evitar refetch
- [ ] Soporte para SoundCloud, Bandcamp (vía yt-dlp)
- [ ] Empaquetado para `pipx`

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

# 3. Dry-run
yt-links-mp3 download /tmp/links.txt --dry-run

# 4. Descargar de verdad
yt-links-mp3 download /tmp/links.txt -o /tmp/test

# 5. Verificar
ls -la /tmp/test/
ffprobe "/tmp/test/<archivo>.mp3"
```

Verificar:
- El ID duplicado (`dQw4w9WgXcQ`) aparece solo una vez
- Comentarios y líneas vacías no generan downloads
- Archivos con nombres consistentes
- `ffprobe archivo.mp3` muestra metadatos
- Portada visible en Finder/VLC
- No quedan archivos `.part` o `.tmp`

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
| Rate limiting de YouTube | Concurrencia baja por defecto (3), respeto a `--limit-rate` de yt-dlp |
| El usuario pone la misma URL dos veces sin darse cuenta | Dedupe preservando orden + warning "URL duplicada en línea N" |

---

## 📊 Estimación restante

~6–10 horas para llegar a Fase 3 funcional (metadatos + robustez). Fase 4 y 5 son nice-to-have.

---

## 🚦 Estado actual

**Fase actual:** 5 — Pulido ✅ (cache + sitios múltiples + pipx)
**Próximo paso:** Fase 6 (MusicBrainz, estructura por artista/álbum)

### Notas operativas

- Python 3.10+ requerido (`pyproject.toml` declara `>=3.10`). Probado en 3.11 y 3.12.
- ffmpeg requerido por yt-dlp para el postprocess a MP3.

---
