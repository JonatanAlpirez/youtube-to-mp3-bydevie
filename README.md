# 🎵 yt-playlist-mp3

Descargador de música desde listas de reproducción de YouTube. Convierte cada video de una playlist a MP3 con metadatos limpios y una estructura de carpetas ordenada.

---

## ✨ Características

- Descarga una playlist completa de YouTube como archivos MP3.
- Extrae metadatos: título, artista, álbum, número de pista, año, portada.
- Nombra los archivos con un patrón consistente (basado en metadatos, no en el título del video).
- Maneja duplicados y re-descargas (skip si ya existe con la misma calidad).
- Concurrencia configurable para acelerar la descarga.
- Progreso por video y progreso global de la playlist.
- Modo dry-run para previsualizar qué se descargaría sin tocar disco.
- Configuración vía archivo `config.yaml` o flags CLI.

---

## 🧰 Stack

| Componente            | Tecnología                                | Por qué                                                                 |
| --------------------- | ----------------------------------------- | ----------------------------------------------------------------------- |
| Descarga de video     | [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) | Mantenido, soporte de playlists, selectores de formato, postprocesado.  |
| Extracción de audio   | `ffmpeg`                                  | Estándar de facto para muxing/conversión.                               |
| Lenguaje              | Python 3.11+                              | Ecosistema, scripts, CLI limpio.                                        |
| CLI                   | [`click`](https://palletsprojects.com/p/click/) | Argumentos tipados, subcomandos, experiencia pro.                     |
| Config                | `pydantic-settings` + YAML               | Validación + archivo de config legible.                                |
| Logging               | `loguru`                                  | Salida colorida en consola + archivo rotado.                            |
| Progreso              | `rich`                                    | Barras de progreso y tablas bonitas.                                    |
| Tests                 | `pytest`                                  | Estándar del ecosistema.                                                |
| Empaquetado           | `uv` o `pip` + `pyproject.toml`           | Dependencias declarativas, instalable como CLI.                         |

---

## 📦 Instalación

```bash
# 1. Dependencias de sistema
brew install ffmpeg        # macOS
# sudo apt install ffmpeg # Debian/Ubuntu

# 2. Clonar e instalar
git clone <repo-url> yt-playlist-mp3
cd yt-playlist-mp3
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

> El comando `yt-playlist-mp3` quedará disponible en tu shell.

---

## 🚀 Uso

```bash
# Descargar una playlist
yt-playlist-mp3 download "https://www.youtube.com/playlist?list=PLxxxxxx"

# Con carpeta de salida personalizada
yt-playlist-mp3 download "URL" -o ~/Music/Playlists

# Previsualizar (dry-run)
yt-playlist-mp3 download "URL" --dry-run

# Forzar re-descarga
yt-playlist-mp3 download "URL" --force

# Concurrencia (default: 3)
yt-playlist-mp3 download "URL" --concurrency 5
```

### Configuración (`config.yaml`)

```yaml
output_dir: ~/Music/Playlists
audio_format: mp3
audio_quality: 192  # kbps
concurrency: 3
filename_template: "{artist}/{album}/{track_number:02d} - {title}.{ext}"
embed_metadata: true
embed_thumbnail: true
skip_existing: true
```

---

## 📁 Estructura resultante

```
~/Music/Playlists/
└── Mi Playlist Favorita/
    ├── cover.jpg
    ├── 01 - Track Name.mp3
    ├── 02 - Another Track.mp3
    └── ...
```

---

## ⚖️ Aviso legal

Este proyecto es solo para uso personal. Respeta los derechos de autor y los Términos de Servicio de YouTube. No distribuyas el contenido descargado.

---

## 📄 Licencia

MIT
