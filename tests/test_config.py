"""Tests para config.py — carga y defaults.

Regression test para SPEC-001: el config.example.yaml debe cargar
correctamente con yaml.safe_load y Config.load().
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from yt_links_mp3.config import Config


def _example_config_path() -> Path:
    return Path(__file__).parent.parent / "config.example.yaml"


def test_example_config_loads_without_error() -> None:
    """El config.example.yaml del repo debe cargar sin errores."""
    example_path = _example_config_path()
    assert example_path.exists(), "config.example.yaml debe existir en la raíz"
    config = Config.load(example_path)
    assert isinstance(config, Config)


def test_example_config_cleanup_patterns_are_valid_regex() -> None:
    """Los cleanup_patterns deben ser regex compilables."""
    example_path = _example_config_path()
    config = Config.load(example_path)
    for pattern in config.cleanup_patterns:
        # No debe lanzar re.error
        re.compile(pattern)


def test_example_config_cleanup_patterns_match_expected() -> None:
    """Los cleanup_patterns deben contener exactamente las regex esperadas."""
    example_path = _example_config_path()
    config = Config.load(example_path)
    expected = [
        r"\(official video\)",
        r"\(official music video\)",
        r"\[official video\]",
        r"\(official\)",
        r"\[official\]",
        r"\(lyric(?:s)? video\)",
        r"\(lyric(?:s)?\)",
        r"\(lyrics?\)",
        r"\(hd\)",
        r"\[hd\]",
        r"\bhd\b",
        "official video",
        "official music video",
        "music video",
        r"\blyric(?:s)? video\b",
        r"\blyrics?\b",
    ]
    assert config.cleanup_patterns == expected


def test_example_config_cleanup_patterns_actually_clean_title() -> None:
    """Smoke test: aplicar los patterns debe limpiar un título real."""
    from yt_links_mp3.metadata import cleanup_title

    example_path = _example_config_path()
    config = Config.load(example_path)
    result = cleanup_title(
        "Never Gonna Give You Up (Official Video)",
        patterns=config.cleanup_patterns,
    )
    assert result == "Never Gonna Give You Up"


def test_readme_yaml_block_is_valid() -> None:
    """El bloque YAML de ejemplo en README.md debe ser parseable."""
    readme = Path(__file__).parent.parent / "README.md"
    content = readme.read_text(encoding="utf-8")

    # Buscar el bloque YAML dentro de triple-backticks con tag yaml
    matches = re.findall(r"```yaml\n(.*?)\n```", content, re.DOTALL)
    assert matches, "README debe contener al menos un bloque YAML"

    for i, block in enumerate(matches):
        try:
            yaml.safe_load(block)
        except yaml.YAMLError as e:
            pytest.fail(f"Bloque YAML #{i} del README no es válido: {e}")
