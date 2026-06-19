"""Configuración de logging con loguru."""
from __future__ import annotations

import sys

from loguru import logger


def setup_logging(verbose: bool = False) -> None:
    """Configura loguru para consola.

    verbose=True -> DEBUG, si no -> INFO.
    """
    logger.remove()
    level = "DEBUG" if verbose else "INFO"
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        colorize=True,
    )