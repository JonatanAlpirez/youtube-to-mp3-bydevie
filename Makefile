.PHONY: help install test lint lint-fix format run clean

help:
	@echo "yt-links-mp3 — Makefile"
	@echo ""
	@echo "Targets:"
	@echo "  install    Instala el paquete y dependencias de dev en un venv"
	@echo "  test       Corre la suite de tests con pytest"
	@echo "  lint       Revisa el código con ruff (sin modificar)"
	@echo "  lint-fix   Revisa y arregla issues con ruff"
	@echo "  format     Formatea el código con ruff format"
	@echo "  run        Corre 'yt-links-mp3' con los args que pases (ej: make run ARGS='download links.txt')"
	@echo "  clean      Borra caches de Python y pytest"

install:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -e ".[dev]"
	@echo ""
	@echo "✅ Listo. Activá el venv con: source .venv/bin/activate"

test:
	pytest -v

lint:
	ruff check .

lint-fix:
	ruff check --fix .

format:
	ruff format .

run:
	.venv/bin/yt-links-mp3 $(ARGS)

clean:
	rm -rf .pytest_cache .ruff_cache __pycache__ */__pycache__ */*/__pycache__
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true