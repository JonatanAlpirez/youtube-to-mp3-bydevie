"""Barra de progreso con rich."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from rich.progress import (
    BarColumn,
    Progress,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)


@contextmanager
def progress_bar(total: int, description: str = "Descargando") -> Iterator[Progress]:
    """Context manager que devuelve un Progress listo para usar."""
    with Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TextColumn("({task.completed}/{task.total})"),
        TimeElapsedColumn(),
        TextColumn("·"),
        TimeRemainingColumn(),
        refresh_per_second=2,
    ) as progress:
        progress.add_task(description, total=total)
        yield progress
